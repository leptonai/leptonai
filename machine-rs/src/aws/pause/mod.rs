use std::io::{self, stdout, Error, ErrorKind};

use aws_manager::{self, autoscaling, sts};
use clap::{Arg, Command};
use crossterm::{
    execute,
    style::{Color, Print, ResetColor, SetForegroundColor},
};
use dialoguer::{theme::ColorfulTheme, Select};
use tokio::time::Duration;

pub const NAME: &str = "pause";

pub fn command() -> Command {
    Command::new(NAME)
        .about("Pauses the dev-machine with ASG")
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

pub async fn execute(log_level: &str, spec_file_path: &str, skip_prompt: bool) -> io::Result<()> {
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
            "No, I am not ready to pause the dev-machine!",
            "Yes, let's pause the dev-machine!",
        ];
        let selected = Select::with_theme(&ColorfulTheme::default())
            .with_prompt("Select your 'pause' option")
            .items(&options[..])
            .default(0)
            .interact()
            .unwrap();
        if selected == 0 {
            return Ok(());
        }
    }

    log::info!("pausing dev-machine with ASG...");
    let autoscaling_manager = autoscaling::Manager::new(&shared_config);
    let asg_logical_id = aws_resources.cloudformation_asg_logical_id.clone().unwrap();

    log::info!("setting ASG logical id '{asg_logical_id}' desired capacity to 0");
    autoscaling_manager
        .cli
        .set_desired_capacity()
        .auto_scaling_group_name(&asg_logical_id)
        .desired_capacity(0)
        .send()
        .await
        .unwrap();

    println!();
    log::info!("pause all success!");
    Ok(())
}
