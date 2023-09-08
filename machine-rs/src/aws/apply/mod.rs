use std::{
    collections::HashMap,
    fs::{self, File},
    io::{self, stdout, Error, ErrorKind},
    os::unix::fs::PermissionsExt,
    path::Path,
};

use aws_manager::{
    self, cloudformation, ec2,
    kms::{self, envelope},
    s3, ssm, sts,
};
use aws_sdk_cloudformation::types::{Capability, OnFailure, Parameter, StackStatus, Tag};
use aws_sdk_ec2::types::Filter;
use clap::{Arg, Command};
use crossterm::{
    execute,
    style::{Color, Print, ResetColor, SetForegroundColor},
};
use dialoguer::{theme::ColorfulTheme, Select};
use tokio::time::{sleep, Duration};

pub const NAME: &str = "apply";

pub fn command() -> Command {
    Command::new(NAME)
        .about("Applies/creates resources based on configuration")
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
}

// 50-minute
const MAX_WAIT_SECONDS: u64 = 50 * 60;

pub async fn execute(log_level: &str, spec_file_path: &str, skip_prompt: bool) -> io::Result<()> {
    // ref. https://github.com/env-logger-rs/env_logger/issues/47
    env_logger::init_from_env(
        env_logger::Env::default().filter_or(env_logger::DEFAULT_FILTER_ENV, log_level),
    );

    let mut spec = crate::aws::Spec::load(spec_file_path).unwrap();
    spec.spec_file_path = spec_file_path.to_string();
    spec.validate()?;

    let mut aws_resources = spec.aws_resources.clone();
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
        aws_resources.identity = current_identity;
    };

    let ssm_manager = ssm::Manager::new(&shared_config);
    if !spec.machine.image_id.is_empty() {
        log::info!("using ami {}", spec.machine.image_id);
    } else if !spec.machine.image_id_ssm_parameter.is_empty() {
        log::info!(
            "image_id empty, so checking if ssm parameter {} exists (this is retry of default-spec run)",
            spec.machine.image_id_ssm_parameter
        );
        let ami = ssm_manager
            .fetch_ami(&spec.machine.image_id_ssm_parameter)
            .await
            .unwrap();

        let image_id = ami.image_id.clone();
        log::info!(
            "fetched ami {:?} and image id {image_id} from the SSM parameter {}",
            ami,
            spec.machine.image_id_ssm_parameter
        );

        spec.machine.image_id = image_id;
    }

    // set defaults based on ID
    aws_resources.ec2_key_name = format!("{}-ec2-key", spec.id);
    if aws_resources.cloudformation_ec2_instance_role.is_none() {
        aws_resources.cloudformation_ec2_instance_role =
            Some(crate::aws::StackName::Ec2InstanceRole(spec.id.clone()).encode());
    }
    if aws_resources.cloudformation_vpc.is_none() {
        aws_resources.cloudformation_vpc =
            Some(crate::aws::StackName::Vpc(spec.id.clone()).encode());
    }
    if aws_resources.cloudformation_asg.is_none() {
        aws_resources.cloudformation_asg =
            Some(crate::aws::StackName::Asg(spec.id.clone()).encode());
    }
    spec.aws_resources = aws_resources.clone();
    spec.sync(None)?;

    execute!(
        stdout(),
        SetForegroundColor(Color::Blue),
        Print(format!("\nLoaded Spec: '{}'\n", spec_file_path)),
        ResetColor
    )?;
    let spec_contents = spec.encode_yaml()?;
    println!("{}\n", spec_contents);

    println!();
    println!();
    if !skip_prompt {
        let options = &[
            "No, I am not ready to create resources!",
            "Yes, let's create resources!",
        ];
        let selected = Select::with_theme(&ColorfulTheme::default())
            .with_prompt("Select your 'apply' option")
            .items(&options[..])
            .default(0)
            .interact()
            .unwrap();
        if selected == 0 {
            return Ok(());
        }
    }

    log::info!("creating resources (with spec path {})", spec_file_path);
    let ec2_manager = ec2::Manager::new(&shared_config);
    let kms_manager = kms::Manager::new(&shared_config);
    let s3_manager = s3::Manager::new(&shared_config);
    let cloudformation_manager = cloudformation::Manager::new(&shared_config);

    sleep(Duration::from_secs(2)).await;
    execute!(
        stdout(),
        SetForegroundColor(Color::Green),
        Print("\n\n\nSTEP: creating S3 bucket\n"),
        ResetColor
    )?;
    s3_manager
        .create_bucket(&aws_resources.s3_bucket)
        .await
        .unwrap();

    sleep(Duration::from_secs(2)).await;
    s3_manager
        .put_object(
            spec_file_path,
            &aws_resources.s3_bucket,
            &crate::aws::StorageNamespace::DevMachineConfigFile(spec.id.clone()).encode(),
        )
        .await
        .unwrap();
    s3_manager
        .put_object(
            &spec.upload_artifacts.init_bash_local_file_path,
            &aws_resources.s3_bucket,
            &crate::aws::StorageNamespace::InitScript(spec.id.clone()).encode(),
        )
        .await
        .unwrap();

    if aws_resources.kms_key_id.is_none() && aws_resources.kms_key_arn.is_none() {
        sleep(Duration::from_secs(2)).await;
        execute!(
            stdout(),
            SetForegroundColor(Color::Green),
            Print("\n\n\nSTEP: creating KMS key\n"),
            ResetColor
        )?;
        let key = kms_manager
            .create_symmetric_default_key(format!("{}-cmk", spec.id).as_str(), false)
            .await
            .unwrap();

        aws_resources.kms_key_id = Some(key.id);
        aws_resources.kms_key_arn = Some(key.arn);
        spec.aws_resources = aws_resources.clone();
        spec.sync(None)?;

        sleep(Duration::from_secs(1)).await;
        s3_manager
            .put_object(
                spec_file_path,
                &aws_resources.s3_bucket,
                &crate::aws::StorageNamespace::DevMachineConfigFile(spec.id.clone()).encode(),
            )
            .await
            .unwrap();
    }
    let envelope_manager = envelope::Manager::new(
        &kms_manager,
        aws_resources.kms_key_id.clone().unwrap(),
        spec.aad_tag.clone(),
    );

    sleep(Duration::from_secs(2)).await;
    if spec.aws_resources.ec2_key_import {
        execute!(
            stdout(),
            SetForegroundColor(Color::Green),
            Print("\n\n\nSTEP: importing EC2 key pair\n"),
            ResetColor
        )
        .unwrap();
        ec2_manager
            .import_key(
                &aws_resources.ec2_key_name,
                &aws_resources.ssh_public_key_path.clone().unwrap(),
            )
            .await
            .unwrap();
    } else {
        execute!(
            stdout(),
            SetForegroundColor(Color::Green),
            Print("\n\n\nSTEP: creating EC2 key pair\n"),
            ResetColor
        )
        .unwrap();
        ec2_manager
            .create_key_pair(
                &aws_resources.ec2_key_name,
                &aws_resources.ssh_private_key_path,
            )
            .await
            .unwrap();
    }

    let tmp_compressed_path = random_manager::tmp_path(15, Some(".zstd")).unwrap();
    compress_manager::pack_file(
        &aws_resources.ssh_private_key_path,
        &tmp_compressed_path,
        compress_manager::Encoder::Zstd(3),
    )
    .unwrap();

    let tmp_encrypted_path = random_manager::tmp_path(15, Some(".encrypted")).unwrap();
    envelope_manager
        .seal_aes_256_file(&tmp_compressed_path, &tmp_encrypted_path)
        .await
        .unwrap();

    s3_manager
        .put_object(
            &tmp_encrypted_path,
            &aws_resources.s3_bucket,
            &crate::aws::StorageNamespace::Ec2AccessKeyCompressedEncrypted(spec.id.clone())
                .encode(),
        )
        .await
        .unwrap();

    spec.aws_resources = aws_resources.clone();
    spec.sync(None)?;

    sleep(Duration::from_secs(1)).await;
    s3_manager
        .put_object(
            spec_file_path,
            &aws_resources.s3_bucket,
            &crate::aws::StorageNamespace::DevMachineConfigFile(spec.id.clone()).encode(),
        )
        .await
        .unwrap();

    spec.aws_resources = aws_resources.clone();
    spec.sync(None)?;

    if aws_resources
        .cloudformation_ec2_instance_profile_arn
        .is_none()
    {
        sleep(Duration::from_secs(2)).await;
        execute!(
            stdout(),
            SetForegroundColor(Color::Green),
            Print("\n\n\nSTEP: creating EC2 instance role\n"),
            ResetColor
        )?;

        let ec2_instance_role_tmpl = crate::aws::artifacts::ec2_instance_role_yaml().unwrap();
        let ec2_instance_role_stack_name = aws_resources
            .cloudformation_ec2_instance_role
            .clone()
            .unwrap();

        cloudformation_manager
            .create_stack(
                ec2_instance_role_stack_name.as_str(),
                Some(vec![Capability::CapabilityNamedIam]),
                OnFailure::Delete,
                &ec2_instance_role_tmpl,
                Some(Vec::from([
                    Tag::builder().key("KIND").value("dev-machine").build(),
                    Tag::builder()
                        .key("UserId")
                        .value(aws_resources.identity.user_id.clone())
                        .build(),
                ])),
                Some(Vec::from([
                    build_param("Id", &spec.id),
                    build_param("KmsKeyArn", &aws_resources.kms_key_arn.clone().unwrap()),
                    build_param("S3BucketName", &aws_resources.s3_bucket),
                ])),
            )
            .await
            .unwrap();

        sleep(Duration::from_secs(10)).await;
        let stack = cloudformation_manager
            .poll_stack(
                ec2_instance_role_stack_name.as_str(),
                StackStatus::CreateComplete,
                Duration::from_secs(500),
                Duration::from_secs(30),
            )
            .await
            .unwrap();

        for o in stack.outputs.unwrap() {
            let k = o.output_key.unwrap();
            let v = o.output_value.unwrap();
            log::info!("stack output key=[{}], value=[{}]", k, v,);
            if k.eq("InstanceProfileArn") {
                aws_resources.cloudformation_ec2_instance_profile_arn = Some(v)
            }
        }
        spec.aws_resources = aws_resources.clone();
        spec.sync(None)?;

        sleep(Duration::from_secs(1)).await;
        s3_manager
            .put_object(
                spec_file_path,
                &aws_resources.s3_bucket,
                &crate::aws::StorageNamespace::DevMachineConfigFile(spec.id.clone()).encode(),
            )
            .await
            .unwrap();
    }

    if aws_resources.cloudformation_vpc_id.is_none()
        && aws_resources.existing_vpc_security_group_ids.is_none()
        && aws_resources.existing_vpc_subnet_ids_for_asg.is_none()
        && aws_resources.cloudformation_vpc_security_group_id.is_none()
        && aws_resources.cloudformation_vpc_public_subnet_ids.is_none()
    {
        sleep(Duration::from_secs(2)).await;
        execute!(
            stdout(),
            SetForegroundColor(Color::Green),
            Print("\n\n\nSTEP: creating VPC\n"),
            ResetColor
        )?;

        let vpc_tmpl = crate::aws::artifacts::vpc_yaml().unwrap();
        let vpc_stack_name = aws_resources.cloudformation_vpc.clone().unwrap();

        let mut parameters = Vec::from([
            build_param("Id", &spec.id),
            build_param("UserId", &aws_resources.identity.user_id),
            build_param("VpcCidr", "10.0.0.0/16"),
            build_param("PublicSubnetCidr1", "10.0.64.0/19"),
            build_param("PublicSubnetCidr2", "10.0.128.0/19"),
            build_param("PublicSubnetCidr3", "10.0.192.0/19"),
            build_param(
                "SshPortIngressIpv4Range",
                if !spec.aws_resources.ssh_ingress_ipv4_cidr.is_empty() {
                    spec.aws_resources.ssh_ingress_ipv4_cidr.as_str()
                } else {
                    "0.0.0.0/0"
                },
            ),
            build_param(
                "UserDefinedTcpIngressPortsIngressIpv4Range",
                if !spec
                    .aws_resources
                    .user_defined_tcp_ingress_ports_ipv4_cidr
                    .is_empty()
                {
                    spec.aws_resources
                        .user_defined_tcp_ingress_ports_ipv4_cidr
                        .as_str()
                } else {
                    "0.0.0.0/0"
                },
            ),
        ]);
        if !spec.aws_resources.user_defined_tcp_ingress_ports.is_empty() {
            let mut ports_in_str: Vec<String> = Vec::new();
            for p in spec.aws_resources.user_defined_tcp_ingress_ports.iter() {
                ports_in_str.push(format!("{}", p));
            }
            parameters.push(build_param(
                "UserDefinedTcpIngressPorts",
                ports_in_str.join(",").as_str(),
            ));
            parameters.push(build_param(
                "UserDefinedTcpIngressPortsCount",
                format!("{}", ports_in_str.len()).as_str(),
            ));
        } else {
            parameters.push(build_param("UserDefinedTcpIngressPortsCount", "0"));
        }

        cloudformation_manager
            .create_stack(
                vpc_stack_name.as_str(),
                None,
                OnFailure::Delete,
                &vpc_tmpl,
                Some(Vec::from([
                    Tag::builder().key("KIND").value("dev-machine").build(),
                    Tag::builder()
                        .key("UserId")
                        .value(aws_resources.identity.user_id.clone())
                        .build(),
                ])),
                Some(parameters),
            )
            .await
            .unwrap();

        sleep(Duration::from_secs(10)).await;
        let stack = cloudformation_manager
            .poll_stack(
                vpc_stack_name.as_str(),
                StackStatus::CreateComplete,
                Duration::from_secs(300),
                Duration::from_secs(30),
            )
            .await
            .unwrap();

        for o in stack.outputs.unwrap() {
            let k = o.output_key.unwrap();
            let v = o.output_value.unwrap();
            log::info!("stack output key=[{}], value=[{}]", k, v,);
            if k.eq("VpcId") {
                aws_resources.cloudformation_vpc_id = Some(v);
                continue;
            }
            if k.eq("SecurityGroupId") {
                aws_resources.cloudformation_vpc_security_group_id = Some(v);
                continue;
            }
            if k.eq("PublicSubnetIds") {
                let splits: Vec<&str> = v.split(',').collect();
                let mut pub_subnets: Vec<String> = vec![];
                for s in splits {
                    log::info!("public subnet {}", s);
                    pub_subnets.push(String::from(s));
                }
                aws_resources.cloudformation_vpc_public_subnet_ids = Some(pub_subnets);
            }
        }
        spec.aws_resources = aws_resources.clone();
        spec.sync(None)?;

        sleep(Duration::from_secs(1)).await;
        s3_manager
            .put_object(
                spec_file_path,
                &aws_resources.s3_bucket,
                &crate::aws::StorageNamespace::DevMachineConfigFile(spec.id.clone()).encode(),
            )
            .await
            .unwrap();
    }

    let is_spot_instance = spec.machine.instance_mode == *"spot";
    let on_demand_pct = if is_spot_instance { 0 } else { 100 };

    let security_group_ids = if let Some(s) = &aws_resources.existing_vpc_security_group_ids {
        log::info!("using the existing security group Id {:?}", s);
        s.join(",")
    } else {
        aws_resources
            .cloudformation_vpc_security_group_id
            .clone()
            .unwrap()
    };

    // always use a single AZ, use join(",") for multi-AZ
    let asg_subnet_ids = if let Some(ss) = &aws_resources.existing_vpc_subnet_ids_for_asg {
        log::info!("using the existing subnets {:?} for ASG", ss);
        ss[random_manager::usize() % ss.len()].clone()
    } else {
        let ss = aws_resources
            .cloudformation_vpc_public_subnet_ids
            .clone()
            .unwrap();
        ss[random_manager::usize() % ss.len()].clone()
    };

    let mut asg_parameters = Vec::from([
        build_param("Id", &spec.id),
        build_param("UserId", &aws_resources.identity.user_id),
        build_param("KmsKeyArn", &aws_resources.kms_key_arn.clone().unwrap()),
        build_param("AadTag", &spec.aad_tag),
        build_param("S3BucketName", &aws_resources.s3_bucket),
        build_param("Ec2KeyPairName", &aws_resources.ec2_key_name.clone()),
        build_param(
            "InstanceProfileArn",
            &aws_resources
                .cloudformation_ec2_instance_profile_arn
                .clone()
                .unwrap(),
        ),
        build_param("PublicSubnetIds", &asg_subnet_ids),
        build_param("SecurityGroupIds", &security_group_ids),
        build_param(
            "InstanceMode",
            if is_spot_instance {
                "spot"
            } else {
                "on-demand"
            },
        ),
        build_param(
            "OnDemandPercentageAboveBaseCapacity",
            format!("{}", on_demand_pct).as_str(),
        ),
    ]);

    if !spec.machine.image_id.is_empty() {
        asg_parameters.push(build_param("ImageId", &spec.machine.image_id));
    } else {
        log::info!("no image_id, no image_id_ssm_parameter specified, fallback to default");
        asg_parameters.push(build_param(
            "ImageIdSsmParameter",
            &ec2::default_image_id_ssm_parameter(
                spec.machine.arch_type.as_str(),
                spec.machine.os_type.as_str(),
            )
            .unwrap(),
        ));
    }

    asg_parameters.push(build_param(
        "ImageVolumeType",
        &spec.machine.image_volume_type,
    ));
    asg_parameters.push(build_param(
        "ImageVolumeIops",
        format!("{}", spec.machine.image_volume_iops).as_str(),
    ));

    if spec.machine.image_volume_size_in_gb > 0 {
        asg_parameters.push(build_param(
            "ImageVolumeSize",
            format!("{}", spec.machine.image_volume_size_in_gb).as_str(),
        ));
    }
    if let Some(email) = &spec.ssh_key_email {
        asg_parameters.push(build_param("SshKeyEmail", email));
    }

    // TODO: remove this
    let simplified_arch: Vec<&str> = spec.machine.arch_type.as_str().split('-').collect();
    asg_parameters.push(build_param("ArchType", simplified_arch[0]));
    asg_parameters.push(build_param("OsType", spec.machine.os_type.as_str()));

    if !spec.machine.instance_types.is_empty() {
        let instance_types = spec.machine.instance_types.clone();
        asg_parameters.push(build_param("InstanceTypes", &instance_types.join(",")));
        asg_parameters.push(build_param(
            "InstanceTypesCount",
            format!("{}", instance_types.len()).as_str(),
        ));
    }

    if aws_resources.cloudformation_asg_logical_id.is_some() {
        log::warn!(
            "looks like asg is already created in {:?} -- skipping",
            aws_resources.cloudformation_asg_logical_id
        )
    }

    sleep(Duration::from_secs(2)).await;
    execute!(
        stdout(),
        SetForegroundColor(Color::Green),
        Print("\n\n\nSTEP: creating ASG\n"),
        ResetColor
    )?;

    let cloudformation_asg_tmpl = crate::aws::artifacts::asg_ubuntu_yaml().unwrap();
    let cloudformation_asg_stack_name = aws_resources.cloudformation_asg.clone().unwrap();

    let desired_capacity = spec.machine.machines;

    // must deep-copy as shared with other machine kind
    let mut parameters = asg_parameters.clone();

    parameters.push(build_param(
        "AsgName",
        format!("{}-{}", spec.id, simplified_arch[0]).as_str(),
    ));
    parameters.push(build_param(
        "AsgDesiredCapacity",
        format!("{}", desired_capacity).as_str(),
    ));

    cloudformation_manager
        .create_stack(
            cloudformation_asg_stack_name.as_str(),
            None,
            OnFailure::Delete,
            &cloudformation_asg_tmpl,
            Some(Vec::from([
                Tag::builder().key("KIND").value("dev-machine").build(),
                Tag::builder()
                    .key("UserId")
                    .value(aws_resources.identity.user_id.clone())
                    .build(),
            ])),
            Some(parameters),
        )
        .await
        .unwrap();

    // add 5-minute for ELB creation
    let mut wait_secs = 300 + 60 * desired_capacity as u64;
    if wait_secs > MAX_WAIT_SECONDS {
        wait_secs = MAX_WAIT_SECONDS;
    }
    sleep(Duration::from_secs(30)).await;
    let stack = cloudformation_manager
        .poll_stack(
            cloudformation_asg_stack_name.as_str(),
            StackStatus::CreateComplete,
            Duration::from_secs(wait_secs),
            Duration::from_secs(30),
        )
        .await
        .unwrap();

    for o in stack.outputs.unwrap() {
        let k = o.output_key.unwrap();
        let v = o.output_value.unwrap();
        log::info!("stack output key=[{}], value=[{}]", k, v,);
        if k.eq("AsgLogicalId") {
            aws_resources.cloudformation_asg_logical_id = Some(v);
            continue;
        }
    }
    if aws_resources.cloudformation_asg_logical_id.is_none() {
        return Err(Error::new(
            ErrorKind::Other,
            "aws_resources.cloudformation_asg_logical_id not found",
        ));
    }

    // so we can destroy if the following steps fail
    spec.aws_resources = aws_resources.clone();
    spec.sync(None)?;

    let asg_name = aws_resources.cloudformation_asg_logical_id.clone().unwrap();

    let mut droplets: Vec<ec2::Droplet> = Vec::new();
    let target_nodes = spec.machine.machines;
    for _ in 0..10 {
        // TODO: better retries
        log::info!(
            "fetching all droplets for dev-machine SSH access (target nodes {})",
            target_nodes
        );
        droplets = ec2_manager.list_asg(&asg_name).await.unwrap();
        if (droplets.len() as u32) >= target_nodes {
            let mut all_have_ips = true;
            for d in droplets.iter() {
                if d.public_ipv4.is_empty() {
                    log::warn!("{} does not have public IP yet", d.instance_id);
                    all_have_ips = false;
                    break;
                }
            }
            if all_have_ips {
                break;
            }
        }
        log::info!(
            "retrying fetching all droplets (only got {})",
            droplets.len()
        );
        sleep(Duration::from_secs(30)).await;
    }

    let mut eips = Vec::new();
    if spec.machine.ip_mode == *"elastic" {
        log::info!("using elastic IPs... wait more");
        loop {
            eips = ec2_manager
                .describe_eips_by_tags(HashMap::from([(String::from("Id"), spec.id.clone())]))
                .await
                .unwrap();

            log::info!("got {} EIP addresses", eips.len());

            let mut ready = true;
            for eip_addr in eips.iter() {
                ready = ready && eip_addr.instance_id.is_some();
            }
            if ready && eips.len() == target_nodes as usize {
                break;
            }

            sleep(Duration::from_secs(30)).await;
        }
    }

    let mut instance_id_to_public_ip = HashMap::new();
    for eip_addr in eips.iter() {
        let allocation_id = eip_addr.allocation_id.to_owned().unwrap();
        let instance_id = eip_addr.instance_id.to_owned().unwrap();
        let public_ip = eip_addr.public_ip.to_owned().unwrap();
        log::info!("EIP found {allocation_id} for {instance_id} and {public_ip}");
        instance_id_to_public_ip.insert(instance_id, public_ip);
    }

    let f = File::open(&aws_resources.ssh_private_key_path).unwrap();
    f.set_permissions(PermissionsExt::from_mode(0o444)).unwrap();

    let user_name = ec2::default_user_name(spec.machine.os_type.as_str()).unwrap();
    let mut ssh_commands = Vec::new();
    for d in droplets {
        let public_ip = if let Some(public_ip) = instance_id_to_public_ip.get(&d.instance_id) {
            public_ip.clone()
        } else {
            d.public_ipv4.clone()
        };
        instance_id_to_public_ip.insert(d.instance_id.clone(), public_ip.clone());

        let ssh_command = ssh_scp_manager::ssh::aws::Command {
            ssh_key_path: aws_resources.ssh_private_key_path.clone(),
            user_name: user_name.clone(),

            region: aws_resources.region.clone(),
            availability_zone: d.availability_zone,

            instance_id: d.instance_id,
            instance_state: d.instance_state_name,

            ip_mode: spec.machine.ip_mode.clone(),
            public_ip,

            profile: None,
        };
        println!("\n{}\n", ssh_command.to_string());
        ssh_commands.push(ssh_command);
    }
    println!();

    ssh_scp_manager::ssh::aws::Commands(ssh_commands.clone())
        .sync(&aws_resources.ssh_commands_path)
        .unwrap();
    spec.aws_resources = aws_resources.clone();
    spec.sync(None)?;

    sleep(Duration::from_secs(1)).await;
    s3_manager
        .put_object(
            spec_file_path,
            &aws_resources.s3_bucket,
            &crate::aws::StorageNamespace::DevMachineConfigFile(spec.id.clone()).encode(),
        )
        .await
        .unwrap();

    log::info!("waiting for bootstrap and ready (to be safe)");
    sleep(Duration::from_secs(20)).await;

    if spec.wait_for_init_script_completion {
        log::info!("waiting for init script completion");
        for ssh_command in ssh_commands.iter() {
            loop {
                let ready = match ssh_command.run("tail -30 /var/log/cloud-init-output.log") {
                    Ok(output) => {
                        println!(
                            "{} init script std output:\n{}\n",
                            ssh_command.instance_id, output.stdout
                        );
                        if !output.stderr.trim().is_empty() {
                            println!(
                                "{} init script std err:\n{}\n",
                                ssh_command.instance_id, output.stderr
                            );
                        }

                        log::info!(
                            "checking stdout for complete message string '{}'",
                            aws_manager::ec2::plugins::INIT_SCRIPT_COMPLETE_MSG
                        );
                        output
                            .stdout
                            .contains(aws_manager::ec2::plugins::INIT_SCRIPT_COMPLETE_MSG)
                    }
                    Err(e) => {
                        log::warn!("failed to run ssh command {}", e);
                        false
                    }
                };
                if ready {
                    break;
                }

                sleep(Duration::from_secs(40)).await;
            }

            if spec.wait_for_image_create_completion {
                log::info!("now that machine's ready, download the release information file");
                match ssh_command.download_file(
                    "/etc/release-full",
                    &aws_resources.release_info_file_path,
                    true,
                ) {
                    Ok(_) => {
                        log::info!(
                            "successfully downloaded release info to {}",
                            aws_resources.release_info_file_path
                        )
                    }
                    Err(e) => {
                        log::warn!("failed to download release info file {}", e);
                    }
                }

                log::warn!("now that machine's ready, fast-run SSH key cleanups...");
                match ssh_command.run("sudo cat /etc/release-full && sudo rm -rf /etc/ssh/ssh_hosts* /home/ubuntu/.ssh/authorized_keys /root/.ssh/authorized_keys || true") {
                    Ok(output) => {
                        println!(
                            "{} init script std output:\n{}\n",
                            ssh_command.instance_id, output.stdout
                        );
                        if !output.stderr.trim().is_empty() {
                            println!(
                                "{} init script std err:\n{}\n",
                                ssh_command.instance_id, output.stderr
                            );
                        }
                    }
                    Err(e) => {
                        log::warn!("failed to run ssh command {}", e);
                    }
                }
            }
        }
    }

    println!();
    log::info!("apply all success!");
    println!();
    println!("# run the following to delete resources WITHOUT PROMPT");
    execute!(
        stdout(),
        SetForegroundColor(Color::Red),
        Print(format!(
            "{} aws delete \\\n--delete-all \\\n--skip-prompt \\\n--spec-file-path {}\n",
            std::env::current_exe()
                .expect("unexpected None current_exe")
                .display(),
            spec_file_path
        )),
        ResetColor
    )?;

    if !spec.image_name_to_create.is_empty() {
        println!();
        println!();
        sleep(Duration::from_secs(5)).await;
        for ssh_command in ssh_commands.iter() {
            match ssh_command.run("sudo rm -rf /etc/ssh/ssh_hosts* /home/ubuntu/.ssh/authorized_keys /root/.ssh/authorized_keys || true") {
                Ok(output) => {
                    println!(
                        "{} init script std output:\n{}\n",
                        ssh_command.instance_id, output.stdout
                    );
                    if !output.stderr.trim().is_empty() {
                        println!(
                            "{} init script std err:\n{}\n",
                            ssh_command.instance_id, output.stderr
                        );
                    }
                }
                Err(e) => {
                    log::warn!("failed to run ssh command {}", e);

                    // in case previous try failed
                    log::warn!("sleeping another 100-second for ssh key cleanup job on remote");
                    sleep(Duration::from_secs(100)).await;
                }
            }
        }

        let mut instance_id = String::new();
        if let Some((k, _v)) = instance_id_to_public_ip.iter().next() {
            instance_id = k.clone();
        }

        log::info!(
            "creating an image {} for the instance {}",
            spec.image_name_to_create,
            instance_id
        );
        let ami = ec2_manager
            .create_image(&instance_id, &spec.image_name_to_create)
            .await
            .unwrap();
        log::info!("created an image '{ami}'");

        if spec.wait_for_image_create_completion {
            log::info!("now polling the image {ami}");
            sleep(Duration::from_secs(30)).await;

            let img = ec2_manager
                .poll_image_until_available(
                    &ami,
                    Duration::from_secs(5000), // can take up to 40-minute
                    Duration::from_secs(60),
                )
                .await
                .unwrap();

            log::info!(
                "successfully polled the image {:?} -- AMI '{ami}' is now available for use",
                img
            );
        }
    }

    if spec.auto_delete_after_apply {
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

            let ec2_instance_role_stack_name =
                aws_resources.cloudformation_ec2_instance_role.unwrap();
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

        if spec.auto_delete_after_apply_delete_all {
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
    }

    Ok(())
}

fn build_param(k: &str, v: &str) -> Parameter {
    Parameter::builder()
        .parameter_key(k)
        .parameter_value(v)
        .build()
}
