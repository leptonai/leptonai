use clap::Command;

pub const NAME: &str = "aws";

pub fn new() -> Command {
    Command::new(NAME)
        .about("AWS sub-commands")
        .subcommands(vec![
            crate::aws::default_spec::command(),
            crate::aws::apply::command(),
            crate::aws::delete::command(),
            crate::aws::pause::command(),
            crate::aws::resume::command(),
        ])
}

pub async fn execute(matches: &clap::ArgMatches) {
    match matches.subcommand() {
        Some((crate::aws::default_spec::NAME, sub_matches)) => {
            let s = sub_matches
                .get_one::<String>("EXISTING_VPC_SUBNET_IDS_FOR_ASG")
                .unwrap_or(&String::new())
                .clone();
            let existing_vpc_subnet_ids_for_asg: Vec<String> = if s.is_empty() {
                Vec::new()
            } else {
                s.split(',').map(|x| x.trim().to_string()).collect()
            };

            let s = sub_matches
                .get_one::<String>("PLUGINS")
                .unwrap_or(&String::new())
                .clone();
            let plugins: Vec<String> = if s.is_empty() {
                Vec::new()
            } else {
                s.split(',').map(|x| x.trim().to_string()).collect()
            };

            let s = sub_matches
                .get_one::<String>("USER_DEFINED_TCP_INGRESS_PORTS")
                .unwrap_or(&String::new())
                .clone();
            let user_defined_tcp_ingress_ports: Vec<u32> = if s.is_empty() {
                Vec::new()
            } else {
                s.split(',')
                    .map(|x| x.trim().to_string().parse::<u32>().unwrap())
                    .collect()
            };

            let s = sub_matches
                .get_one::<String>("INSTANCE_TYPES")
                .unwrap_or(&String::new())
                .clone();
            let instance_types: Vec<String> = if s.is_empty() {
                Vec::new()
            } else {
                s.split(',').map(|x| x.trim().to_string()).collect()
            };

            let opt = crate::aws::DefaultSpecOption {
                log_level: sub_matches
                    .get_one::<String>("LOG_LEVEL")
                    .unwrap_or(&String::from("info"))
                    .clone(),

                ssh_key_email: sub_matches
                    .get_one::<String>("SSH_KEY_EMAIL")
                    .unwrap_or(&String::new())
                    .clone(),
                unsafe_temporary_aws_secret_key_id: sub_matches
                    .get_one::<String>("UNSAFE_TEMPORARY_AWS_SECRET_KEY_ID")
                    .unwrap_or(&String::new())
                    .clone(),
                unsafe_temporary_aws_secret_access_key: sub_matches
                    .get_one::<String>("UNSAFE_TEMPORARY_AWS_SECRET_ACCESS_KEY")
                    .unwrap_or(&String::new())
                    .clone(),

                ssh_ingress_ipv4_cidr: sub_matches
                    .get_one::<String>("SSH_INGRESS_IPV4_CIDR")
                    .unwrap_or(&String::new())
                    .clone(),

                user_defined_tcp_ingress_ports_ipv4_cidr: sub_matches
                    .get_one::<String>("USER_DEFINED_TCP_INGRESS_PORTS_IPV4_CIDR")
                    .unwrap_or(&String::new())
                    .clone(),
                user_defined_tcp_ingress_ports,

                profile_name: sub_matches
                    .get_one::<String>("PROFILE_NAME")
                    .unwrap_or(&String::new())
                    .clone(),
                region: sub_matches
                    .get_one::<String>("REGION")
                    .unwrap_or(&String::new())
                    .clone(),
                instance_mode: sub_matches
                    .get_one::<String>("INSTANCE_MODE")
                    .unwrap()
                    .clone(),
                instance_size: sub_matches
                    .get_one::<String>("INSTANCE_SIZE")
                    .unwrap_or(&String::from("2xlarge"))
                    .clone(),
                instance_types,
                ip_mode: sub_matches.get_one::<String>("IP_MODE").unwrap().clone(),

                ec2_key_import: sub_matches.get_flag("EC2_KEY_IMPORT"),

                image_id: sub_matches
                    .get_one::<String>("IMAGE_ID")
                    .unwrap_or(&String::new())
                    .clone(),
                image_id_ssm_parameter: sub_matches
                    .get_one::<String>("IMAGE_ID_SSM_PARAMETER")
                    .unwrap_or(&String::new())
                    .clone(),

                image_volume_type: sub_matches
                    .get_one::<String>("IMAGE_VOLUME_TYPE")
                    .unwrap_or(&String::from("gp3"))
                    .clone(),
                image_volume_size_in_gb: *sub_matches
                    .get_one::<u32>("IMAGE_VOLUME_SIZE_IN_GB")
                    .unwrap_or(&20),
                image_volume_iops: *sub_matches
                    .get_one::<u32>("IMAGE_VOLUME_IOPS")
                    .unwrap_or(&3000),

                arch_type: sub_matches.get_one::<String>("ARCH_TYPE").unwrap().clone(),
                os_type: sub_matches.get_one::<String>("OS_TYPE").unwrap().clone(),
                aad_tag: sub_matches.get_one::<String>("AAD_TAG").unwrap().clone(),

                existing_vpc_security_group_id: sub_matches
                    .get_one::<String>("EXISTING_VPC_SECURITY_GROUP_ID")
                    .unwrap_or(&String::new())
                    .to_string(),
                existing_vpc_subnet_ids_for_asg,

                plugins,
                post_init_script: sub_matches
                    .get_one::<String>("POST_INIT_SCRIPT")
                    .unwrap_or(&String::from("echo DONE"))
                    .clone(),

                id_prefix: sub_matches
                    .get_one::<String>("ID_PREFIX")
                    .unwrap_or(&String::from(crate::aws::ID_PREFIX))
                    .clone(),

                volume_type: sub_matches
                    .get_one::<String>("VOLUME_TYPE")
                    .unwrap_or(&String::from("gp3"))
                    .clone(),
                volume_size_in_gb: *sub_matches
                    .get_one::<u32>("VOLUME_SIZE_IN_GB")
                    .unwrap_or(&300),
                volume_iops: *sub_matches.get_one::<u32>("VOLUME_IOPS").unwrap_or(&3000),
                volume_throughput: *sub_matches
                    .get_one::<u32>("VOLUME_THROUGHPUT")
                    .unwrap_or(&500),

                wait_for_init_script_completion: sub_matches
                    .get_flag("WAIT_FOR_INIT_SCRIPT_COMPLETION"),
                image_name_to_create: sub_matches
                    .get_one::<String>("IMAGE_NAME_TO_CREATE")
                    .unwrap_or(&String::new())
                    .clone(),
                wait_for_image_create_completion: sub_matches
                    .get_flag("WAIT_FOR_IMAGE_CREATE_COMPLETION"),

                auto_delete_after_apply: sub_matches.get_flag("AUTO_DELETE_AFTER_APPLY"),
                auto_delete_after_apply_delete_all: sub_matches
                    .get_flag("AUTO_DELETE_AFTER_APPLY_DELETE_ALL"),

                spec_file_path: sub_matches
                    .get_one::<String>("SPEC_FILE_PATH")
                    .unwrap()
                    .clone(),
            };
            crate::aws::default_spec::execute(opt).await.unwrap();
        }

        Some((crate::aws::apply::NAME, sub_matches)) => {
            crate::aws::apply::execute(
                &sub_matches
                    .get_one::<String>("LOG_LEVEL")
                    .unwrap_or(&String::from("info"))
                    .clone(),
                &sub_matches
                    .get_one::<String>("SPEC_FILE_PATH")
                    .unwrap_or(&String::new())
                    .clone(),
                sub_matches.get_flag("SKIP_PROMPT"),
            )
            .await
            .unwrap();
        }

        Some((crate::aws::delete::NAME, sub_matches)) => {
            crate::aws::delete::execute(
                &sub_matches
                    .get_one::<String>("LOG_LEVEL")
                    .unwrap_or(&String::from("info"))
                    .clone(),
                &sub_matches
                    .get_one::<String>("SPEC_FILE_PATH")
                    .unwrap_or(&String::new())
                    .clone(),
                sub_matches.get_flag("DELETE_ALL"),
                sub_matches.get_flag("SKIP_PROMPT"),
            )
            .await
            .unwrap();
        }

        Some((crate::aws::pause::NAME, sub_matches)) => {
            crate::aws::pause::execute(
                &sub_matches
                    .get_one::<String>("LOG_LEVEL")
                    .unwrap_or(&String::from("info"))
                    .clone(),
                &sub_matches
                    .get_one::<String>("SPEC_FILE_PATH")
                    .unwrap_or(&String::new())
                    .clone(),
                sub_matches.get_flag("SKIP_PROMPT"),
            )
            .await
            .unwrap();
        }

        Some((crate::aws::resume::NAME, sub_matches)) => {
            crate::aws::resume::execute(
                &sub_matches
                    .get_one::<String>("LOG_LEVEL")
                    .unwrap_or(&String::from("info"))
                    .clone(),
                &sub_matches
                    .get_one::<String>("SPEC_FILE_PATH")
                    .unwrap_or(&String::new())
                    .clone(),
                sub_matches.get_flag("SKIP_PROMPT"),
            )
            .await
            .unwrap();
        }

        _ => unreachable!("unknown subcommand"),
    }
}
