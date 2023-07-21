pub mod apply;
pub mod artifacts;
pub mod command;
pub mod default_spec;
pub mod delete;
pub mod pause;
pub mod resume;

use std::{
    fs::{self, File},
    io::{self, Error, ErrorKind, Write},
    path::Path,
    str::FromStr,
    string::String,
};

use aws_manager::{ec2, ssm, sts};
use serde::{Deserialize, Serialize};
use tokio::time::Duration;

pub const MIN_MACHINES: u32 = 1;
pub const MAX_MACHINES: u32 = 2;

#[derive(Debug, Serialize, Deserialize, Eq, PartialEq, Clone)]
#[serde(rename_all = "snake_case")]
pub struct Spec {
    #[serde(default)]
    pub id: String,

    #[serde(default)]
    pub aad_tag: String,

    /// If not none, creates an SSH key in remote machine with this email.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub ssh_key_email: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub unsafe_temporary_aws_secret_key_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub unsafe_temporary_aws_secret_access_key: Option<String>,

    pub aws_resources: Resources,
    pub machine: Machine,

    /// Upload artifacts from the local machine to share with remote machines.
    pub upload_artifacts: UploadArtifacts,

    /// A list of plugins to install via an init script.
    pub plugins: Vec<aws_manager::ec2::plugins::Plugin>,
    pub post_init_script: String,

    #[serde(default)]
    pub wait_for_init_script_completion: bool,
    #[serde(default)]
    pub image_name_to_create: String,
    #[serde(default)]
    pub wait_for_image_create_completion: bool,

    #[serde(default)]
    pub auto_delete_after_apply: bool,
    #[serde(default)]
    pub auto_delete_after_apply_delete_all: bool,

    #[serde(default)]
    pub spec_file_path: String,
}

#[derive(Debug, Serialize, Deserialize, Eq, PartialEq, Clone)]
#[serde(rename_all = "snake_case")]
pub struct Machine {
    #[serde(default)]
    pub machines: u32,
    pub arch_type: ec2::ArchType,
    pub os_type: ec2::OsType,
    #[serde(default)]
    pub instance_types: Vec<String>,
    #[serde(default)]
    pub instance_mode: String,
    #[serde(default)]
    pub ip_mode: String,

    /// If empty and "image_id_ssm_parameter" is non-empty,
    /// "image_id_ssm_parameter" overwrites "image_id" during "apply".
    #[serde(default)]
    pub image_id: String,
    #[serde(default)]
    pub image_id_ssm_parameter: String,

    #[serde(default)]
    pub image_volume_type: String,
    #[serde(default)]
    pub image_volume_size_in_gb: u32,
    #[serde(default)]
    pub image_volume_iops: u32,

    #[serde(default)]
    pub volume_type: String,
    #[serde(default)]
    pub volume_size_in_gb: u32,
    #[serde(default)]
    pub volume_iops: u32,
    #[serde(default)]
    pub volume_throughput: u32,
}

#[derive(Debug, Serialize, Deserialize, Eq, PartialEq, Clone)]
#[serde(rename_all = "snake_case")]
pub struct Resources {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub profile_name: Option<String>,
    #[serde(default)]
    pub identity: sts::Identity,

    #[serde(default)]
    pub region: String,

    #[serde(default)]
    pub ssh_ingress_ipv4_cidr: String,
    #[serde(default)]
    pub user_defined_tcp_ingress_ports_ipv4_cidr: String,
    #[serde(default)]
    pub user_defined_tcp_ingress_ports: Vec<u32>,

    #[serde(default)]
    pub s3_bucket: String,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub kms_key_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub kms_key_arn: Option<String>,

    #[serde(default)]
    pub ec2_key_import: bool,
    #[serde(default)]
    pub ec2_key_name: String,
    #[serde(default)]
    pub ssh_private_key_path: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub ssh_public_key_path: Option<String>,
    #[serde(default)]
    pub ssh_commands_path: String,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub existing_vpc_security_group_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub existing_vpc_subnet_ids_for_asg: Option<Vec<String>>,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub cloudformation_ec2_instance_role: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cloudformation_ec2_instance_profile_arn: Option<String>,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub cloudformation_vpc: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cloudformation_vpc_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cloudformation_vpc_security_group_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cloudformation_vpc_public_subnet_ids: Option<Vec<String>>,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub cloudformation_asg: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cloudformation_asg_logical_id: Option<String>,

    #[serde(default)]
    pub release_info_file_path: String,
}

impl Default for Resources {
    fn default() -> Self {
        Self::default()
    }
}

impl Resources {
    pub fn default() -> Self {
        Self {
            profile_name: None,

            identity: sts::Identity::default(),

            region: String::from("us-east-1"),

            ssh_ingress_ipv4_cidr: String::from("0.0.0.0/0"),
            user_defined_tcp_ingress_ports_ipv4_cidr: String::from("0.0.0.0/0"),
            user_defined_tcp_ingress_ports: Vec::new(),

            s3_bucket: String::from(""),

            kms_key_id: None,
            kms_key_arn: None,

            ec2_key_import: false,
            ec2_key_name: String::new(),
            ssh_private_key_path: String::new(),
            ssh_public_key_path: None,
            ssh_commands_path: String::new(),

            existing_vpc_security_group_id: None,
            existing_vpc_subnet_ids_for_asg: None,

            cloudformation_ec2_instance_role: None,
            cloudformation_ec2_instance_profile_arn: None,

            cloudformation_vpc: None,
            cloudformation_vpc_id: None,
            cloudformation_vpc_security_group_id: None,
            cloudformation_vpc_public_subnet_ids: None,

            cloudformation_asg: None,
            cloudformation_asg_logical_id: None,

            release_info_file_path: String::new(),
        }
    }
}

/// Represents artifacts for installation, to be shared with
/// remote machines. All paths are local to the caller's environment.
#[derive(Debug, Serialize, Deserialize, Eq, PartialEq, Clone)]
#[serde(rename_all = "snake_case")]
pub struct UploadArtifacts {
    #[serde(default)]
    pub init_bash_local_file_path: String,
}

/// Represents the CloudFormation stack name.
pub enum StackName {
    Ec2InstanceRole(String),
    Vpc(String),
    Asg(String),
}

impl StackName {
    pub fn encode(&self) -> String {
        match self {
            StackName::Ec2InstanceRole(id) => format!("{}-ec2-instance-role", id),
            StackName::Vpc(id) => format!("{}-vpc", id),
            StackName::Asg(id) => format!("{}-asg", id),
        }
    }
}

/// Defines "default-spec" option.
#[derive(Debug, Serialize, Deserialize, Eq, PartialEq, Clone)]
pub struct DefaultSpecOption {
    pub log_level: String,

    pub ssh_key_email: String,
    pub unsafe_temporary_aws_secret_key_id: String,
    pub unsafe_temporary_aws_secret_access_key: String,

    pub ssh_ingress_ipv4_cidr: String,
    pub user_defined_tcp_ingress_ports_ipv4_cidr: String,
    pub user_defined_tcp_ingress_ports: Vec<u32>,

    pub arch_type: String,
    pub os_type: String,
    pub aad_tag: String,

    pub profile_name: String,
    pub region: String,
    pub instance_mode: String,
    pub instance_size: String,
    pub instance_types: Vec<String>,
    pub ip_mode: String,

    pub ec2_key_import: bool,

    pub image_id: String,
    pub image_id_ssm_parameter: String,
    pub image_volume_type: String,
    pub image_volume_size_in_gb: u32,
    pub image_volume_iops: u32,

    pub existing_vpc_security_group_id: String,
    pub existing_vpc_subnet_ids_for_asg: Vec<String>,

    pub plugins: Vec<String>,
    pub post_init_script: String,

    pub id_prefix: String,

    pub volume_type: String,
    pub volume_size_in_gb: u32,
    pub volume_iops: u32,
    pub volume_throughput: u32,

    pub wait_for_init_script_completion: bool,
    pub image_name_to_create: String,
    pub wait_for_image_create_completion: bool,

    pub auto_delete_after_apply: bool,
    pub auto_delete_after_apply_delete_all: bool,

    pub spec_file_path: String,
}

pub const ID_PREFIX: &str = "dev";

impl Spec {
    pub async fn default(opts: DefaultSpecOption) -> io::Result<Self> {
        if opts.image_volume_size_in_gb > 0 && opts.image_volume_size_in_gb < 20 {
            return Err(Error::new(
                ErrorKind::InvalidInput,
                format!(
                    "image_volume_size_in_gb '{}' must be >= 20 GiB",
                    opts.image_volume_size_in_gb
                ),
            ));
        }
        if opts.image_volume_type.starts_with("io") && opts.image_volume_size_in_gb > 0 {
            if opts.image_volume_iops > opts.image_volume_size_in_gb * 50 {
                return Err(Error::new(
                    ErrorKind::InvalidInput,
                    format!(
                        "max iops to volume size ratio for io volume is 50, got '{}'",
                        opts.image_volume_iops / opts.image_volume_size_in_gb
                    ),
                ));
            }
        }

        let ssh_ingress_ipv4_cidr = if !opts.ssh_ingress_ipv4_cidr.is_empty() {
            opts.ssh_ingress_ipv4_cidr.clone()
        } else {
            log::info!("empty ssh_ingress_ipv4_cidr, so default to public IP on the local host");
            if let Some(ip) = public_ip::addr().await {
                log::info!("found public ip address {:?}", ip);
                format!("{}/32", ip.to_string())
            } else {
                log::warn!("failed to get a public IP address -- default to 0.0.0.0/0");
                "0.0.0.0/0".to_string()
            }
        };

        let user_defined_tcp_ingress_ports_ipv4_cidr = if !opts
            .user_defined_tcp_ingress_ports_ipv4_cidr
            .is_empty()
        {
            opts.user_defined_tcp_ingress_ports_ipv4_cidr.clone()
        } else {
            log::info!("empty user_defined_tcp_ingress_ports_ipv4_cidr, so default to public IP on the local host");
            if let Some(ip) = public_ip::addr().await {
                log::info!("found public ip address {:?}", ip);
                format!("{}/32", ip.to_string())
            } else {
                log::warn!("failed to get a public IP address -- default to 0.0.0.0/0");
                "0.0.0.0/0".to_string()
            }
        };

        let ssh_key_email = if opts.ssh_key_email.is_empty() {
            None
        } else {
            Some(opts.ssh_key_email.clone())
        };
        let unsafe_temporary_aws_secret_key_id =
            if opts.unsafe_temporary_aws_secret_key_id.is_empty() {
                None
            } else {
                Some(opts.unsafe_temporary_aws_secret_key_id.clone())
            };
        let unsafe_temporary_aws_secret_access_key =
            if opts.unsafe_temporary_aws_secret_access_key.is_empty() {
                None
            } else {
                Some(opts.unsafe_temporary_aws_secret_access_key.clone())
            };

        let id_prefix = if opts.id_prefix.is_empty() {
            ID_PREFIX.to_string()
        } else {
            opts.id_prefix.clone()
        };
        // don't use id to minimize the number of s3 buckets
        // in case one user creates multiple dev machines
        // [year][month][date]-[system host-based id]
        let s3_bucket = format!(
            "{id_prefix}-{}-{}-{}",
            id_manager::time::timestamp(6),
            id_manager::system::string(7),
            opts.region
        );
        let id = id_manager::time::with_prefix(&id_prefix);

        let init_bash_local_file_path = get_init_script_path(&opts.spec_file_path);

        let os_type = ec2::OsType::from_str(&opts.os_type).map_err(|e| {
            Error::new(
                ErrorKind::InvalidInput,
                format!("failed OsType::from_str '{}' with {}", opts.os_type, e),
            )
        })?;
        let arch_type = ec2::ArchType::from_str(&opts.arch_type).map_err(|e| {
            Error::new(
                ErrorKind::InvalidInput,
                format!("failed ArchType::from_str '{}' with {}", opts.arch_type, e),
            )
        })?;
        let valid_instance_types = ec2::valid_instance_types(arch_type.clone());

        let instance_types = if opts.instance_types.is_empty() {
            ec2::default_instance_types(&opts.region, &opts.arch_type, &opts.instance_size)?
        } else {
            opts.instance_types.clone()
        };
        if !valid_instance_types.is_empty() {
            for instance_type in instance_types.iter() {
                if !valid_instance_types.contains(instance_type) {
                    return Err(Error::new(
                        ErrorKind::InvalidInput,
                        format!(
                            "arch '{}' does not support instance type '{}'",
                            arch_type.as_str(),
                            instance_type
                        ),
                    ));
                }
            }
        }

        let (plugins, bash_script) = aws_manager::ec2::plugins::create(
            arch_type.clone(),
            os_type.clone(),
            opts.plugins,
            opts.ip_mode == "elastic",
            &s3_bucket,
            &id,
            &opts.region,
            &opts.volume_type,
            opts.volume_size_in_gb,
            opts.volume_iops,
            opts.volume_throughput,
            ssh_key_email.clone(),
            if opts.unsafe_temporary_aws_secret_key_id.is_empty() {
                None
            } else {
                Some(opts.unsafe_temporary_aws_secret_key_id.clone())
            },
            if opts.unsafe_temporary_aws_secret_access_key.is_empty() {
                None
            } else {
                Some(opts.unsafe_temporary_aws_secret_access_key.clone())
            },
            Some(opts.post_init_script.clone()),
        )?;

        let path = Path::new(&init_bash_local_file_path);
        let parent_dir = path.parent().unwrap();
        fs::create_dir_all(parent_dir)?;
        let mut f = File::create(path)?;
        f.write_all(bash_script.as_bytes())?;

        let ssh_private_key_path = get_ssh_private_key_path(&opts.spec_file_path);
        let ssh_public_key_path = if opts.ec2_key_import {
            let pubk_path = get_ssh_public_key_path(&opts.spec_file_path);
            let (pk, pubk) = ssh_scp_manager::rsa::new_key(None)?;

            let path = Path::new(&ssh_private_key_path);
            let parent_dir = path.parent().unwrap();
            fs::create_dir_all(parent_dir)?;
            let mut f = File::create(path)?;
            f.write_all(pk.as_bytes())?;
            log::info!("wrote SSH private key to '{ssh_private_key_path}'");

            let path = Path::new(&pubk_path);
            let parent_dir = path.parent().unwrap();
            fs::create_dir_all(parent_dir)?;
            let mut f = File::create(path)?;
            f.write_all(pubk.as_bytes())?;
            log::info!("wrote SSH public key to '{pubk_path}'");

            Some(pubk_path)
        } else {
            None
        };

        let shared_config = aws_manager::load_config(
            Some(opts.region.clone()),
            if opts.profile_name.is_empty() {
                None
            } else {
                Some(opts.profile_name.clone())
            },
            Some(Duration::from_secs(30)),
        )
        .await;
        let ssm_manager = ssm::Manager::new(&shared_config);

        let image_id = if !opts.image_id.is_empty() {
            log::info!("using ami {} from the flag", opts.image_id);
            opts.image_id.clone()
        } else if !opts.image_id_ssm_parameter.is_empty() {
            log::info!(
                "image_id empty, so checking if ssm parameter {} exists",
                opts.image_id_ssm_parameter
            );
            match ssm_manager.fetch_ami(&opts.image_id_ssm_parameter).await {
                Ok(ami) => {
                    let image_id = ami.image_id.clone();
                    log::info!(
                        "fetched ami {:?} and image id {image_id} from the SSM parameter {}",
                        ami,
                        opts.image_id_ssm_parameter
                    );

                    image_id
                }
                Err(e) => {
                    log::warn!("failed to fetch ami {} -- skipping fetching ami for now, retrying in apply",e);
                    String::new()
                }
            }
        } else {
            String::new()
        };

        Ok(Self {
            id: id.clone(),

            aad_tag: opts.aad_tag.clone(),
            ssh_key_email,
            unsafe_temporary_aws_secret_key_id,
            unsafe_temporary_aws_secret_access_key,

            aws_resources: Resources {
                profile_name: if opts.profile_name.is_empty() {
                    None
                } else {
                    Some(opts.profile_name.clone())
                },
                region: opts.region.clone(),
                ssh_ingress_ipv4_cidr,
                user_defined_tcp_ingress_ports_ipv4_cidr,
                user_defined_tcp_ingress_ports: opts.user_defined_tcp_ingress_ports.clone(),

                s3_bucket,

                ec2_key_import: opts.ec2_key_import,
                ec2_key_name: format!("{}-ec2-key", id),
                ssh_private_key_path,
                ssh_public_key_path,
                ssh_commands_path: get_ssh_commands_path(&opts.spec_file_path),

                existing_vpc_security_group_id: if opts.existing_vpc_security_group_id.is_empty() {
                    None
                } else {
                    Some(opts.existing_vpc_security_group_id.clone())
                },
                existing_vpc_subnet_ids_for_asg: if opts.existing_vpc_subnet_ids_for_asg.is_empty()
                {
                    None
                } else {
                    Some(opts.existing_vpc_subnet_ids_for_asg.clone())
                },

                release_info_file_path: get_release_info_file_path(&opts.spec_file_path),

                ..Resources::default()
            },

            machine: Machine {
                machines: 1,
                arch_type,
                os_type,
                instance_types,
                instance_mode: opts.instance_mode.clone(),
                ip_mode: opts.ip_mode.clone(),

                image_id,
                image_id_ssm_parameter: opts.image_id_ssm_parameter.clone(),

                image_volume_type: opts.image_volume_type.clone(),
                image_volume_size_in_gb: opts.image_volume_size_in_gb,
                image_volume_iops: opts.image_volume_iops,

                volume_type: opts.volume_type.clone(),
                volume_size_in_gb: opts.volume_size_in_gb,
                volume_iops: opts.volume_iops,
                volume_throughput: opts.volume_throughput,
            },

            upload_artifacts: UploadArtifacts {
                init_bash_local_file_path,
            },

            plugins: plugins.clone(),
            post_init_script: opts.post_init_script.clone(),

            wait_for_init_script_completion: opts.wait_for_init_script_completion,
            image_name_to_create: opts.image_name_to_create.clone(),
            wait_for_image_create_completion: opts.wait_for_image_create_completion,

            auto_delete_after_apply: opts.auto_delete_after_apply,
            auto_delete_after_apply_delete_all: opts.auto_delete_after_apply_delete_all,

            spec_file_path: opts.spec_file_path.clone(),
        })
    }

    /// Converts to string in YAML format.
    pub fn encode_yaml(&self) -> io::Result<String> {
        match serde_yaml::to_string(&self) {
            Ok(s) => Ok(s),
            Err(e) => Err(Error::new(
                ErrorKind::Other,
                format!("failed to serialize Spec to YAML {}", e),
            )),
        }
    }

    /// Saves the current spec to disk
    /// and overwrites the file.
    pub fn sync(&self, file_path: Option<String>) -> io::Result<()> {
        let path = if let Some(f) = &file_path {
            Path::new(f)
        } else {
            Path::new(&self.spec_file_path)
        };
        log::info!("syncing Spec to '{:?}'", path.display());

        let parent_dir = path.parent().unwrap();
        fs::create_dir_all(parent_dir)?;

        let ret = serde_yaml::to_string(self);
        let d = match ret {
            Ok(d) => d,
            Err(e) => {
                return Err(Error::new(
                    ErrorKind::Other,
                    format!("failed to serialize Spec to YAML {}", e),
                ));
            }
        };
        let mut f = File::create(path)?;
        f.write_all(d.as_bytes())?;

        Ok(())
    }

    pub fn load(file_path: &str) -> io::Result<Self> {
        log::info!("loading Spec from {}", file_path);

        if !Path::new(file_path).exists() {
            return Err(Error::new(
                ErrorKind::NotFound,
                format!("file {} does not exists", file_path),
            ));
        }

        let f = File::open(file_path).map_err(|e| {
            Error::new(
                ErrorKind::Other,
                format!("failed to open {} ({})", file_path, e),
            )
        })?;
        serde_yaml::from_reader(f)
            .map_err(|e| Error::new(ErrorKind::InvalidInput, format!("invalid YAML: {}", e)))
    }

    /// Validates the spec.
    pub fn validate(&self) -> io::Result<()> {
        log::info!("validating Spec");

        if self.id.is_empty() {
            return Err(Error::new(ErrorKind::InvalidInput, "'id' cannot be empty"));
        }

        // some AWS resources have tag limit of 32-character
        if self.id.len() > 28 {
            return Err(Error::new(
                ErrorKind::InvalidInput,
                format!("'id' length cannot be >28 (got {})", self.id.len()),
            ));
        }

        if self.aws_resources.region.is_empty() {
            return Err(Error::new(
                ErrorKind::InvalidInput,
                "'aws_resources.region' cannot be empty",
            ));
        }
        if self.aws_resources.user_defined_tcp_ingress_ports.len() > 10 {
            return Err(Error::new(
                ErrorKind::InvalidInput,
                "'aws_resources.user_defined_tcp_ingress_ports' cannot be >10",
            ));
        }

        if self.machine.machines < MIN_MACHINES {
            return Err(Error::new(
                ErrorKind::InvalidInput,
                format!(
                    "'machine.machines' {} <minimum {}",
                    self.machine.machines, MIN_MACHINES
                ),
            ));
        }
        if self.machine.machines > MAX_MACHINES {
            return Err(Error::new(
                ErrorKind::InvalidInput,
                format!(
                    "'machine.machines' {} >maximum {}",
                    self.machine.machines, MAX_MACHINES
                ),
            ));
        }

        for p in self.plugins.iter() {
            if matches!(p, aws_manager::ec2::plugins::Plugin::StaticIpProvisioner) {
                if self.machine.ip_mode != "elastic" {
                    return Err(Error::new(
                        ErrorKind::InvalidInput,
                        format!(
                            "aws_manager::ec2::plugins::Plugin::StaticIpProvisioner requires 'machine.ip_mode' elastic (got {})",
                            self.machine.ip_mode
                        ),
                    ));
                }
            }
        }

        if self.auto_delete_after_apply_delete_all && !self.auto_delete_after_apply {
            return Err(Error::new(
                ErrorKind::InvalidInput,
                "'auto_delete_after_apply_delete_all' requires 'auto_delete_after_apply' true",
            ));
        }
        if self.wait_for_image_create_completion && !self.wait_for_init_script_completion {
            return Err(Error::new(
                ErrorKind::InvalidInput,
                "'wait_for_image_create_completion' requires 'wait_for_init_script_completion' true",
            ));
        }

        Ok(())
    }
}

/// RUST_LOG=debug cargo test --package machine-rs --lib -- aws::test_spec --exact --show-output
#[test]
fn test_spec() {
    let _ = env_logger::builder().is_test(true).try_init();

    let id = random_manager::secure_string(10);
    let bucket = format!("test-{}", id_manager::time::timestamp(8));

    let contents = format!(
        r#"

id: {}

aad_tag: hi
ssh_key_email: abc@abc.com
unsafe_temporary_aws_secret_key_id: a
unsafe_temporary_aws_secret_access_key: b

aws_resources:
  profile_name: default
  region: us-east-1
  s3_bucket: {}
  ssh_ingress_ipv4_cidr: 1.2.3.4/0
  user_defined_tcp_ingress_ports_ipv4_cidr: 0.0.0.0/0

machine:
  machines: 1
  arch_type: arm64
  os_type: al2023
  instance_types:
  - c6g.large
  instance_mode: spot
  ip_mode: elastic
  image_id: abc
  image_id_ssm_parameter: aaa

  image_volume_type: io1
  image_volume_size_in_gb: 20
  image_volume_iops: 200
  volume_type: gp3
  volume_size_in_gb: 222
  volume_iops: 3000
  volume_throughput: 500

upload_artifacts:
  init_bash_local_file_path: /tmp/aaa.bash

plugins:
- cloudwatch-agent
post_init_script: echo 123

wait_for_init_script_completion: true
image_name_to_create: aaa
wait_for_image_create_completion: true

auto_delete_after_apply: true
auto_delete_after_apply_delete_all: true

spec_file_path: /tmp/spec.yaml
"#,
        id, bucket,
    );
    let mut f = tempfile::NamedTempFile::new().unwrap();
    let ret = f.write_all(contents.as_bytes());
    assert!(ret.is_ok());
    let config_path = f.path().to_str().unwrap();

    let ret = Spec::load(config_path);
    assert!(ret.is_ok());
    let cfg = ret.unwrap();

    let ret = cfg.sync(Some(config_path.to_string()));
    assert!(ret.is_ok());

    let orig = Spec {
        id: id.clone(),
        aad_tag: String::from("hi"),
        ssh_key_email: Some(String::from("abc@abc.com")),
        unsafe_temporary_aws_secret_key_id: Some(String::from("a")),
        unsafe_temporary_aws_secret_access_key: Some(String::from("b")),

        aws_resources: Resources {
            profile_name: Some(String::from("default")),
            region: String::from("us-east-1"),
            s3_bucket: bucket.clone(),
            ssh_ingress_ipv4_cidr: String::from("1.2.3.4/0"),
            user_defined_tcp_ingress_ports_ipv4_cidr: String::from("0.0.0.0/0"),
            ..Resources::default()
        },

        machine: Machine {
            arch_type: ec2::ArchType::Arm64,
            os_type: ec2::OsType::Al2023,
            machines: 1,
            instance_types: vec![String::from("c6g.large")],
            instance_mode: String::from("spot"),
            ip_mode: String::from("elastic"),
            image_id: String::from("abc"),
            image_id_ssm_parameter: String::from("aaa"),
            image_volume_type: String::from("io1"),
            image_volume_size_in_gb: 20,
            image_volume_iops: 200,
            volume_type: String::from("gp3"),
            volume_size_in_gb: 222,
            volume_iops: 3000,
            volume_throughput: 500,
        },

        upload_artifacts: UploadArtifacts {
            init_bash_local_file_path: String::from("/tmp/aaa.bash"),
        },

        plugins: vec![aws_manager::ec2::plugins::Plugin::CloudwatchAgent],
        post_init_script: String::from("echo 123"),

        wait_for_init_script_completion: true,
        image_name_to_create: String::from("aaa"),
        wait_for_image_create_completion: true,

        auto_delete_after_apply: true,
        auto_delete_after_apply_delete_all: true,

        spec_file_path: String::from("/tmp/spec.yaml"),
    };

    assert_eq!(cfg, orig);
    assert!(cfg.validate().is_ok());
    assert!(orig.validate().is_ok());

    // manually check to make sure the serde deserializer works
    assert_eq!(cfg.id, id);
    assert_eq!(cfg.aad_tag, "hi");
    assert_eq!(cfg.ssh_key_email.clone().unwrap(), "abc@abc.com");

    assert_eq!(cfg.aws_resources.region, "us-east-1");
    assert_eq!(cfg.aws_resources.s3_bucket, bucket);
    assert_eq!(cfg.aws_resources.ssh_ingress_ipv4_cidr, "1.2.3.4/0");

    assert_eq!(cfg.machine.machines, 1);
    assert_eq!(cfg.machine.arch_type, ec2::ArchType::Arm64);
    assert_eq!(cfg.machine.os_type, ec2::OsType::Al2023);
    let instance_types = cfg.machine.instance_types;
    assert_eq!(instance_types[0], "c6g.large");

    assert_eq!(
        cfg.upload_artifacts.init_bash_local_file_path,
        "/tmp/aaa.bash"
    );

    assert_eq!(
        cfg.plugins[0],
        aws_manager::ec2::plugins::Plugin::CloudwatchAgent
    );
}

/// Represents the S3/storage key path.
/// MUST be kept in sync with "cfn-templates/ec2_instance_role.yaml".
pub enum StorageNamespace {
    DevMachineConfigFile(String),
    Ec2AccessKeyCompressedEncrypted(String),
    InitScript(String),
}

impl StorageNamespace {
    pub fn encode(&self) -> String {
        match self {
            StorageNamespace::DevMachineConfigFile(id) => format!("{}/dev-machine.config.yaml", id),
            StorageNamespace::Ec2AccessKeyCompressedEncrypted(id) => {
                format!("{}/ec2-access-key.zstd.seal_aes_256.encrypted", id)
            }
            StorageNamespace::InitScript(id) => {
                format!("{}/init.bash", id)
            }
        }
    }
}

fn get_ssh_private_key_path(spec_file_path: &str) -> String {
    let path = Path::new(spec_file_path);
    let parent_dir = path.parent().unwrap();
    let name = path.file_stem().unwrap();
    let new_name = format!("{}-ec2-access.key", name.to_str().unwrap(),);
    String::from(
        parent_dir
            .join(Path::new(new_name.as_str()))
            .as_path()
            .to_str()
            .unwrap(),
    )
}

fn get_ssh_public_key_path(spec_file_path: &str) -> String {
    let path = Path::new(spec_file_path);
    let parent_dir = path.parent().unwrap();
    let name = path.file_stem().unwrap();
    let new_name = format!("{}-ec2-access.pub.pem", name.to_str().unwrap(),);
    String::from(
        parent_dir
            .join(Path::new(new_name.as_str()))
            .as_path()
            .to_str()
            .unwrap(),
    )
}

fn get_ssh_commands_path(spec_file_path: &str) -> String {
    let path: &Path = Path::new(spec_file_path);
    let parent_dir = path.parent().unwrap();
    let name = path.file_stem().unwrap();
    let new_name = format!("{}-ssh-commands.sh", name.to_str().unwrap(),);
    String::from(
        parent_dir
            .join(Path::new(new_name.as_str()))
            .as_path()
            .to_str()
            .unwrap(),
    )
}

fn get_init_script_path(spec_file_path: &str) -> String {
    let path = Path::new(spec_file_path);
    let parent_dir = path.parent().unwrap();
    let name = path.file_stem().unwrap();
    let new_name = format!("{}-init.bash", name.to_str().unwrap(),);
    String::from(
        parent_dir
            .join(Path::new(new_name.as_str()))
            .as_path()
            .to_str()
            .unwrap(),
    )
}

fn get_release_info_file_path(spec_file_path: &str) -> String {
    let path = Path::new(spec_file_path);
    let parent_dir = path.parent().unwrap();
    let name = path.file_stem().unwrap();
    let new_name = format!("{}-release-info", name.to_str().unwrap(),);
    String::from(
        parent_dir
            .join(Path::new(new_name.as_str()))
            .as_path()
            .to_str()
            .unwrap(),
    )
}
