use std::{
    collections::HashMap,
    fs,
    io::{self, stdout, Error, ErrorKind},
    path::Path,
};

use aws_manager::{self, cloudformation, ec2, kms, s3, sts};
use aws_sdk_cloudformation::types::StackStatus;
use aws_sdk_ec2::types::Filter;
use clap::{Arg, Command};
use crossterm::{
    execute,
    style::{Color, Print, ResetColor, SetForegroundColor},
};
use dialoguer::{theme::ColorfulTheme, Select};
use tokio::time::{sleep, Duration};

pub const NAME: &str = "delete";

pub fn command() -> Command {
    Command::new(NAME)
        .about("Deletes resources based on configuration")
        .arg(
            Arg::new("LOG_LEVEL")
                .long("log-level")
                .short('l')
                .help("Sets the log level")
                .required(false)
                .num_args(1)
                .value_parser(["debug", "info"])
                .default_value("info"),
        )
        .arg(
            Arg::new("SPEC_FILE_PATH")
                .long("spec-file-path")
                .short('s')
                .help("The spec file to load and update")
                .required(true)
                .num_args(1),
        )
        .arg(
            Arg::new("SKIP_PROMPT")
                .long("skip-prompt")
                .short('s')
                .help("Skips prompt mode")
                .required(false)
                .num_args(0),
        )
        .arg(
            Arg::new("DELETE_ALL")
                .long("delete-all")
                .short('a')
                .help("Enables delete all mode (e.g., delete S3 bucket)")
                .required(false)
                .num_args(0),
        )
}

// 50-minute
const MAX_WAIT_SECONDS: u64 = 50 * 60;

pub async fn execute(
    log_level: &str,
    spec_file_path: &str,
    delete_all: bool,
    skip_prompt: bool,
) -> io::Result<()> {
    // ref. https://github.com/env-logger-rs/env_logger/issues/47
    env_logger::init_from_env(
        env_logger::Env::default().filter_or(env_logger::DEFAULT_FILTER_ENV, log_level),
    );

    let spec = crate::aws::Spec::load(spec_file_path).unwrap();
    let aws_resources = spec.aws_resources.clone();

    let shared_config = aws_manager::load_config(
        Some(aws_resources.region.clone()),
        aws_resources.profile_name.clone(),
        Some(Duration::from_secs(30)),
    )
    .await;

    let sts_manager = sts::Manager::new(&shared_config);
    let current_identity = sts_manager.get_identity().await.unwrap();

    // validate identity
    if !aws_resources.identity.user_id.is_empty() {
        // AWS calls must be made from the same caller
        if aws_resources.identity != current_identity {
            log::warn!(
                "config identity {:?} != currently loaded identity {:?}",
                aws_resources.identity,
                current_identity
            );
        }
    } else {
        return Err(Error::new(ErrorKind::Other, "unknown identity"));
    };

    execute!(
        stdout(),
        SetForegroundColor(Color::Blue),
        Print(format!("\nLoaded configuration: '{}'\n", spec_file_path)),
        ResetColor
    )?;
    let spec_contents = spec.encode_yaml().unwrap();
    println!("{}\n", spec_contents);

    if !skip_prompt {
        let options = &[
            "No, I am not ready to delete resources!",
            "Yes, let's delete resources!",
        ];
        let selected = Select::with_theme(&ColorfulTheme::default())
            .with_prompt("Select your 'delete' option")
            .items(&options[..])
            .default(0)
            .interact()
            .unwrap();
        if selected == 0 {
            return Ok(());
        }
    }

    log::info!("deleting resources...");
    let s3_manager = s3::Manager::new(&shared_config);
    let kms_manager = kms::Manager::new(&shared_config);
    let ec2_manager = ec2::Manager::new(&shared_config);
    let cloudformation_manager = cloudformation::Manager::new(&shared_config);

    // delete this first since EC2 key delete does not depend on ASG/VPC
    // (mainly to speed up delete operation)
    sleep(Duration::from_secs(2)).await;
    execute!(
        stdout(),
        SetForegroundColor(Color::Red),
        Print("\n\n\nSTEP: deleting EC2 key pair\n"),
        ResetColor
    )?;

    if Path::new(&aws_resources.ssh_private_key_path).exists() {
        fs::remove_file(&aws_resources.ssh_private_key_path).unwrap();
    }
    let ec2_key_path_compressed = format!("{}.zstd", aws_resources.ssh_private_key_path);
    if Path::new(ec2_key_path_compressed.as_str()).exists() {
        fs::remove_file(ec2_key_path_compressed.as_str()).unwrap();
    }
    let ec2_key_path_compressed_encrypted = format!("{}.encrypted", ec2_key_path_compressed);
    if Path::new(ec2_key_path_compressed_encrypted.as_str()).exists() {
        fs::remove_file(ec2_key_path_compressed_encrypted.as_str()).unwrap();
    }
    ec2_manager
        .delete_key_pair(&aws_resources.ec2_key_name)
        .await
        .unwrap();

    // delete this first since KMS key delete does not depend on ASG/VPC
    // (mainly to speed up delete operation)
    if aws_resources.kms_key_id.is_some() && aws_resources.kms_key_arn.is_some() {
        sleep(Duration::from_secs(2)).await;
        execute!(
            stdout(),
            SetForegroundColor(Color::Red),
            Print("\n\n\nSTEP: deleting KMS key\n"),
            ResetColor
        )?;

        let cmk_id = aws_resources.kms_key_id.unwrap();
        kms_manager
            .schedule_to_delete(cmk_id.as_str(), 7)
            .await
            .unwrap();
    }

    // IAM roles can be deleted without being blocked on ASG/VPC
    if aws_resources
        .cloudformation_ec2_instance_profile_arn
        .is_some()
    {
        sleep(Duration::from_secs(2)).await;
        execute!(
            stdout(),
            SetForegroundColor(Color::Red),
            Print("\n\n\nSTEP: trigger delete EC2 instance role\n"),
            ResetColor
        )?;

        let ec2_instance_role_stack_name = aws_resources
            .cloudformation_ec2_instance_role
            .clone()
            .unwrap();
        cloudformation_manager
            .delete_stack(ec2_instance_role_stack_name.as_str())
            .await
            .unwrap();
    }

    if spec.machine.machines > 0 && aws_resources.cloudformation_asg_logical_id.is_some() {
        sleep(Duration::from_secs(2)).await;
        execute!(
            stdout(),
            SetForegroundColor(Color::Red),
            Print("\n\n\nSTEP: triggering delete ASG\n"),
            ResetColor
        )?;

        let asg_stack_name = aws_resources.cloudformation_asg.clone().unwrap();
        cloudformation_manager
            .delete_stack(asg_stack_name.as_str())
            .await
            .unwrap();
    }

    if spec.machine.machines > 0 && aws_resources.cloudformation_asg_logical_id.is_some() {
        sleep(Duration::from_secs(2)).await;
        execute!(
            stdout(),
            SetForegroundColor(Color::Red),
            Print("\n\n\nSTEP: confirming delete ASG\n"),
            ResetColor
        )?;

        let asg_stack_name = aws_resources.cloudformation_asg.unwrap();

        let desired_capacity = spec.machine.machines;
        let mut wait_secs = 500 + 60 * desired_capacity as u64; // some instances take longer to terminate
        if wait_secs > MAX_WAIT_SECONDS {
            wait_secs = MAX_WAIT_SECONDS;
        }
        cloudformation_manager
            .poll_stack(
                asg_stack_name.as_str(),
                StackStatus::DeleteComplete,
                Duration::from_secs(wait_secs),
                Duration::from_secs(30),
            )
            .await
            .unwrap();
    }

    // VPC delete must run after associated EC2 instances are terminated due to dependencies
    if aws_resources.existing_vpc_security_group_ids.is_none()
        && aws_resources.existing_vpc_subnet_ids_for_asg.is_none()
        && aws_resources.cloudformation_vpc_id.is_some()
        && aws_resources.cloudformation_vpc_security_group_id.is_some()
        && aws_resources.cloudformation_vpc_public_subnet_ids.is_some()
    {
        sleep(Duration::from_secs(2)).await;
        execute!(
            stdout(),
            SetForegroundColor(Color::Red),
            Print("\n\n\nSTEP: deleting VPC\n"),
            ResetColor
        )?;

        let vpc_stack_name = aws_resources.cloudformation_vpc.unwrap();
        cloudformation_manager
            .delete_stack(vpc_stack_name.as_str())
            .await
            .unwrap();
        sleep(Duration::from_secs(10)).await;
        cloudformation_manager
            .poll_stack(
                vpc_stack_name.as_str(),
                StackStatus::DeleteComplete,
                Duration::from_secs(500),
                Duration::from_secs(30),
            )
            .await
            .unwrap();
    }

    if aws_resources
        .cloudformation_ec2_instance_profile_arn
        .is_some()
    {
        sleep(Duration::from_secs(2)).await;
        execute!(
            stdout(),
            SetForegroundColor(Color::Red),
            Print("\n\n\nSTEP: confirming delete EC2 instance role\n"),
            ResetColor
        )?;

        let ec2_instance_role_stack_name = aws_resources.cloudformation_ec2_instance_role.unwrap();
        cloudformation_manager
            .poll_stack(
                ec2_instance_role_stack_name.as_str(),
                StackStatus::DeleteComplete,
                Duration::from_secs(500),
                Duration::from_secs(30),
            )
            .await
            .unwrap();
    }

    if delete_all {
        sleep(Duration::from_secs(2)).await;
        execute!(
            stdout(),
            SetForegroundColor(Color::Red),
            Print("\n\n\nSTEP: deleting S3 bucket\n"),
            ResetColor
        )?;

        s3_manager
            .delete_objects(&aws_resources.s3_bucket, None)
            .await
            .unwrap();
        s3_manager
            .delete_bucket(&aws_resources.s3_bucket)
            .await
            .unwrap();
    }

    execute!(
        stdout(),
        SetForegroundColor(Color::Red),
        Print("\n\n\nSTEP: deleting orphaned EBS volumes\n"),
        ResetColor
    )?;
    // ref. https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_DescribeVolumes.html
    let filters: Vec<Filter> = vec![
        Filter::builder()
            .set_name(Some(String::from("tag:Kind")))
            .set_values(Some(vec![String::from("aws-volume-provisioner")]))
            .build(),
        Filter::builder()
            .set_name(Some(String::from("tag:Id")))
            .set_values(Some(vec![spec.id.clone()]))
            .build(),
    ];
    let volumes = ec2_manager.describe_volumes(Some(filters)).await.unwrap();
    log::info!("found {} volumes", volumes.len());
    if !volumes.is_empty() {
        log::info!("deleting {} volumes", volumes.len());
        for v in volumes {
            let volume_id = v.volume_id().unwrap().to_string();
            log::info!("deleting EBS volume '{}'", volume_id);
            ec2_manager
                .cli
                .delete_volume()
                .volume_id(volume_id)
                .send()
                .await
                .unwrap();
            sleep(Duration::from_secs(2)).await;
        }
    }

    execute!(
        stdout(),
        SetForegroundColor(Color::Red),
        Print("\n\n\nSTEP: deleting orphaned EIPs\n"),
        ResetColor
    )?;
    let eips = ec2_manager
        .describe_eips_by_tags(HashMap::from([(String::from("Id"), spec.id.clone())]))
        .await
        .unwrap();
    log::info!("found {} EIP addresses", eips.len());
    for eip_addr in eips.iter() {
        let allocation_id = eip_addr.allocation_id.to_owned().unwrap();

        log::info!("releasing EIP '{}'", allocation_id);
        ec2_manager
            .cli
            .release_address()
            .allocation_id(allocation_id)
            .send()
            .await
            .unwrap();
        sleep(Duration::from_secs(2)).await;
    }

    println!();
    log::info!("delete all success!");
    Ok(())
}
