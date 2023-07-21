use std::io::{self, stdout};

use clap::{value_parser, Arg, Command};
use crossterm::{
    execute,
    style::{Color, Print, ResetColor, SetForegroundColor},
};

pub const NAME: &str = "default-spec";

pub fn command() -> Command {
    Command::new(NAME)
        .about("Writes a default configuration")
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
            Arg::new("REGION")
                .long("region")
                .short('r')
                .help("Sets the AWS region for API calls/endpoints")
                .required(true)
                .num_args(1)
                .default_value("us-east-1"),
        )
        .arg(
            Arg::new("PROFILE_NAME")
                .long("profile-name")
                .help("Sets the AWS credential profile name for API calls/endpoints")
                .required(false)
                .num_args(1)
                .default_value("default"),
        )
        .arg(
            Arg::new("SSH_KEY_EMAIL")
                .long("ssh-key-email")
                .help("Sets the email address for an SSH key")
                .required(false)
                .num_args(1),
        )
        .arg(
            Arg::new("UNSAFE_TEMPORARY_AWS_SECRET_KEY_ID")
                .long("unsafe-temporary-aws-secret-key-id")
                .help("This is unsafe... only use temp credentials...")
                .required(false)
                .num_args(1),
        )
        .arg(
            Arg::new("UNSAFE_TEMPORARY_AWS_SECRET_ACCESS_KEY")
                .long("unsafe-temporary-aws-secret-access-key")
                .help("This is unsafe... only use temp credentials...")
                .required(false)
                .num_args(1),
        )
        .arg(
            Arg::new("SSH_INGRESS_IPV4_CIDR")
                .long("ssh-ingress-ipv4-cidr")
                .help("Sets the IPv4 CIDR range for ingress SSH traffic (leave empty to default to public IP on the local)")
                .required(false)
                .num_args(1),
        )
        .arg(
            Arg::new("USER_DEFINED_TCP_INGRESS_PORTS_IPV4_CIDR")
                .long("user-defined-tcp-ingress-ports-ipv4-cidr")
                .help("Sets the IPv4 CIDR range for ingress SSH traffic (leave empty to default to public IP on the local)")
                .required(false)
                .num_args(1),
        )
        .arg(
            Arg::new("USER_DEFINED_TCP_INGRESS_PORTS")
                .long("user-defined-tcp-ingress-ports")
                .help("Sets the comma-separated TCP ingress ports (up to 10)")
                .required(false)
                .num_args(1),
        )
        .arg(
            Arg::new("ARCH_TYPE")
                .long("arch-type")
                .help("Sets the machine architecture")
                .required(true)
                .num_args(1)
                .value_parser([
                    aws_manager::ec2::ArchType::Amd64.as_str(),
                    aws_manager::ec2::ArchType::Arm64.as_str(),
                    aws_manager::ec2::ArchType::Amd64GpuP4NvidiaTeslaA100.as_str(),
                    aws_manager::ec2::ArchType::Amd64GpuG3NvidiaTeslaM60.as_str(),
                    aws_manager::ec2::ArchType::Amd64GpuG4dnNvidiaT4.as_str(),
                    aws_manager::ec2::ArchType::Amd64GpuG5NvidiaA10G.as_str(),
                    aws_manager::ec2::ArchType::Amd64GpuInf1.as_str(),
                    aws_manager::ec2::ArchType::Amd64GpuTrn1.as_str(),
                ])
                .default_value(aws_manager::ec2::ArchType::Amd64GpuG5NvidiaA10G.as_str()),
        )
        .arg(
            // TODO: support aws_manager::ec2::OsType::Al2023
            Arg::new("OS_TYPE")
                .long("os-type")
                .help("Sets the OS type")
                .required(true)
                .num_args(1)
                .value_parser([aws_manager::ec2::OsType::Ubuntu2004.as_str(), aws_manager::ec2::OsType::Ubuntu2204.as_str()])
                .default_value(aws_manager::ec2::OsType::Ubuntu2004.as_str()),
        )
        .arg(
            Arg::new("INSTANCE_MODE")
                .long("instance-mode")
                .help("Sets the EC2 instance mode")
                .required(false)
                .num_args(1)
                .value_parser(["spot", "on-demand"])
                .default_value("on-demand"),
        )
        .arg(
            Arg::new("INSTANCE_SIZE")
                .long("instance-size")
                .help("Sets the EC2 instance size")
                .required(false)
                .num_args(1)
                .value_parser(["large", "xlarge", "2xlarge", "4xlarge", "6xlarge", "8xlarge", "12xlarge", "16xlarge", "24xlarge", "32xlarge"])
                .default_value("2xlarge"),
        )
        .arg(
            Arg::new("INSTANCE_TYPES")
                .long("instance-types")
                .help("Sets the comma-separated EC2 instance types (overwrites --instance-size)")
                .required(false)
                .num_args(1)
        )
        .arg(
            Arg::new("IP_MODE")
                .long("ip-mode")
                .help("Sets IP mode to provision EC2 elastic IPs for all nodes")
                .required(false)
                .num_args(1)
                .value_parser(["elastic", "ephemeral"])
                .default_value("ephemeral"),
        )
        .arg(
            Arg::new("EC2_KEY_IMPORT")
                .long("ec2-key-import")
                .help("Set to locally create an EC2 SSH key pair and import to EC2")
                .required(false)
                .num_args(0),
        )
        .arg(
            Arg::new("IMAGE_ID")
                .long("image-id")
                .help("Sets the image id")
                .required(false)
                .num_args(1),
        )
        .arg(
            Arg::new("IMAGE_ID_SSM_PARAMETER")
                .long("image-id-ssm-parameter")
                .help("Sets the image id ssm parameter to resolve")
                .required(false)
                .num_args(1),
        )
        .arg(
            Arg::new("IMAGE_VOLUME_TYPE")
                .long("image-volume-type")
                .help("Sets the image volume type")
                .required(false)
                .num_args(1)
                .value_parser(["gp2", "gp3", "io1", "io2"])
                .default_value("gp3"),
        )
        .arg(
            Arg::new("IMAGE_VOLUME_SIZE_IN_GB")
                .long("image-volume-size-in-gb")
                .help("Sets the image volume size in GB")
                .required(false)
                .num_args(1)
                .value_parser(value_parser!(u32))
                .default_value("20"),
        )
        .arg(
            Arg::new("IMAGE_VOLUME_IOPS")
                .long("image-volume-iops")
                .help("Sets the image volume IOPS (note that max iops to volume size ratio for io volume type is 50)")
                .required(false)
                .num_args(1)
                .value_parser(value_parser!(u32))
                .default_value("3000"),
        )
        .arg(
            Arg::new("AAD_TAG")
                .long("aad-tag")
                .short('a')
                .help("Sets the AAD tag for envelope encryption with KMS")
                .required(false)
                .num_args(1)
                .default_value("my-aad-tag"),
        )
        .arg(
            Arg::new("EXISTING_VPC_SECURITY_GROUP_ID")
                .long("existing-vpc-security-group-id")
                .help("Sets the AWS EC2 security group Id (if not empty, apply command skips VPC creation, delete is skipped)")
                .required(false)
                .num_args(1),
        )
        .arg(
            Arg::new("EXISTING_VPC_SUBNET_IDS_FOR_ASG")
                .long("existing-vpc-subnet-ids-for-asg")
                .help("Sets the comma-separated subnet Ids to use the existing AWS VPC subnets for ASG (if not empty, apply command skips VPC creation, cannot integrate with NLB, delete is skipped)")
                .required(false)
                .num_args(1),
        )
        .arg(
            Arg::new("PLUGINS")
                .long("plugins")
                .help(format!("Sets the comma-separated plugins [possible values: {:?}]", aws_manager::ec2::plugins::Plugin::all()))
                .required(false)
                .num_args(1)
                .default_value("imds,provider-id,vercmp,setup-local-disks,mount-bpf-fs,time-sync,system-limit-bump,ssm-agent,cloudwatch-agent"),
        )
        .arg(
            Arg::new("POST_INIT_SCRIPT")
                .long("post-init-script")
                .help("Commands to run post init script at the end")
                .required(false)
                .num_args(1)
                .default_value("echo DONE"),
        )
        .arg(
            Arg::new("ID_PREFIX")
                .long("id-prefix")
                .help("Prefix to generate Id with")
                .required(false)
                .num_args(1)
                .default_value(crate::aws::ID_PREFIX),
        )
        .arg(
            Arg::new("VOLUME_TYPE")
                .long("volume-type")
                .help("Sets the volume type")
                .required(false)
                .num_args(1)
                .value_parser(["gp2", "gp3", "io1", "io2"])
                .default_value("gp3"),
        )
        .arg(
            Arg::new("VOLUME_SIZE_IN_GB")
                .long("volume-size-in-gb")
                .help("Sets the initial volume size in GB")
                .required(false)
                .num_args(1)
                .value_parser(value_parser!(u32))
                .default_value("300"),
        )
        .arg(
            Arg::new("VOLUME_IOPS")
                .long("volume-iops")
                .help("Sets the IOPS")
                .required(false)
                .num_args(1)
                .value_parser(value_parser!(u32))
                .default_value("3000"),
        )
        .arg(
            Arg::new("VOLUME_THROUGHPUT")
                .long("volume-throughput")
                .help("Sets the volume throughput")
                .required(false)
                .num_args(1)
                .value_parser(value_parser!(u32))
                .default_value("500"),
        )
        .arg(
            Arg::new("WAIT_FOR_INIT_SCRIPT_COMPLETION")
                .long("wait-for-init-script-completion")
                .help("Blocks until the init script is complete by polling the /var/log/cloud-init-output.log")
                .required(false)
                .num_args(0),
        )
        .arg(
            Arg::new("IMAGE_NAME_TO_CREATE")
                .long("image-name-to-create")
                .help("Set a non-empty name to create an AMI after creation or init script is complete")
                .required(false)
                .num_args(1),
        )
        .arg(
            Arg::new("WAIT_FOR_IMAGE_CREATE_COMPLETION")
                .long("wait-for-image-create-completion")
                .help("Blocks until the image creation is complete")
                .required(false)
                .num_args(0),
        )
        .arg(
            Arg::new("AUTO_DELETE_AFTER_APPLY")
                .long("auto-delete-after-apply")
                .help("Deletes after success apply")
                .required(false)
                .num_args(0),
        )
        .arg(
            Arg::new("AUTO_DELETE_AFTER_APPLY_DELETE_ALL")
                .long("auto-delete-after-apply-delete-all")
                .help("Enables delete all mode (e.g., delete S3 bucket)")
                .required(false)
                .num_args(0),
        )
        .arg(
            Arg::new("SPEC_FILE_PATH")
                .long("spec-file-path")
                .short('s')
                .help("The spec file to load and update")
                .required(true)
                .num_args(1),
        )
}

pub async fn execute(opts: crate::aws::DefaultSpecOption) -> io::Result<()> {
    // ref. https://github.com/env-logger-rs/env_logger/issues/47
    env_logger::init_from_env(
        env_logger::Env::default()
            .filter_or(env_logger::DEFAULT_FILTER_ENV, opts.log_level.clone()),
    );

    let spec = crate::aws::Spec::default(opts.clone()).await.unwrap();
    spec.validate()?;
    spec.sync(None)?;

    execute!(
        stdout(),
        SetForegroundColor(Color::Blue),
        Print(format!("\nSaved spec: '{}'\n", opts.spec_file_path)),
        ResetColor
    )?;
    let spec_contents = spec.encode_yaml().unwrap();
    println!("{}\n", spec_contents);

    execute!(
        stdout(),
        SetForegroundColor(Color::Magenta),
        Print(format!("\nvi {}\n", opts.spec_file_path)),
        ResetColor
    )?;
    println!();
    println!("# run the following to create resources");
    execute!(
        stdout(),
        SetForegroundColor(Color::Green),
        Print(format!(
            "{} aws apply \\\n--spec-file-path {}\n",
            std::env::current_exe()
                .expect("unexpected None current_exe")
                .display(),
            opts.spec_file_path
        )),
        ResetColor
    )?;

    println!();
    println!("# run the following to delete all resources including the S3 bucket WITHOUT PROMPT");
    execute!(
        stdout(),
        SetForegroundColor(Color::Red),
        Print(format!(
            "{} aws delete \\\n--delete-all \\\n--skip-prompt \\\n--spec-file-path {}\n",
            std::env::current_exe()
                .expect("unexpected None current_exe")
                .display(),
            opts.spec_file_path
        )),
        ResetColor
    )?;

    println!();
    println!("# run the following to pause/resume the dev machine");
    execute!(
        stdout(),
        SetForegroundColor(Color::Red),
        Print(format!(
            "{} aws pause \\\n--spec-file-path {}\n",
            std::env::current_exe()
                .expect("unexpected None current_exe")
                .display(),
            opts.spec_file_path
        )),
        ResetColor
    )?;
    execute!(
        stdout(),
        SetForegroundColor(Color::Red),
        Print(format!(
            "{} aws resume \\\n--spec-file-path {}\n",
            std::env::current_exe()
                .expect("unexpected None current_exe")
                .display(),
            opts.spec_file_path
        )),
        ResetColor
    )?;

    Ok(())
}
