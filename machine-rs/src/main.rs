pub mod aws;

use clap::{crate_version, Command};

const APP_NAME: &str = "machine-rs";

#[tokio::main]
async fn main() {
    let matches = Command::new(APP_NAME)
        .version(crate_version!())
        .about("Dev machine")
        .subcommands(vec![
            aws::command::new(), // for dev machines in AWS
        ])
        .get_matches();

    match matches.subcommand() {
        Some((crate::aws::command::NAME, sub_matches)) => {
            crate::aws::command::execute(sub_matches).await;
        }
        _ => unreachable!("unknown subcommand"),
    }
}
