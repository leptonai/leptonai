import sys

from .util import click_group, console

from ..api.v1.client import APIClient

import json
import click

from datetime import datetime, timedelta, timezone


def preprocess_time(ctx, param, input_time):
    """
    Preprocesses custom time formats like YD (yesterday) or TD (today).
    """
    now = datetime.now().astimezone()
    input_time = input_time.lower().replace("today", now.strftime("%Y-%m-%d"), 1)
    input_time = input_time.lower().replace("td", now.strftime("%Y-%m-%d"), 1)
    input_time = input_time.lower().replace(
        "yesterday", (now - timedelta(days=1)).strftime("%Y-%m-%d"), 1
    )
    input_time = input_time.lower().replace(
        "yd", (now - timedelta(days=1)).strftime("%Y-%m-%d"), 1
    )
    if input_time.lower() == "now":
        input_time = now.strftime("%Y-%m-%d %H:%M:%S.%f")
    if input_time.lower() == "today":
        input_time = now.to_date_string()
    if input_time.lower() == "yesterday":
        input_time = now.to_date_string()

    # Parse the time and ensure it uses the local timezone
    parsed_time = datetime.fromisoformat(input_time)
    parsed_time = parsed_time.astimezone(now.tzinfo)
    return int(
        parsed_time.timestamp() * 1_000_000_000 + parsed_time.microsecond * 1_000
    )


def convert_to_local_time(nanoseconds):
    """
    Convert a timestamp in nanoseconds to the local time, including the current timezone.

    Args:
        nanoseconds (int or str): The timestamp in nanoseconds.

    Returns:
        str: The local time with timezone as a formatted string.
    """
    if isinstance(nanoseconds, str):
        nanoseconds = int(nanoseconds)

    # Convert nanoseconds to seconds
    seconds = nanoseconds / 1e9
    # Create an aware UTC datetime object
    utc_time = datetime.fromtimestamp(seconds, tz=timezone.utc)
    # Convert UTC time to the local time
    local_time = utc_time.astimezone()

    return local_time.strftime("%Y-%m-%d %H:%M:%S.%f")


def safe_load_json(string):
    try:
        return json.loads(string)
    except json.JSONDecodeError:
        return string


@click_group()
def log():
    pass


# @log.command(name="get_log")
@log.command(name="get")
@click.option(
    "--deployment",
    "-d",
    type=str,
    default=None,
    help="The name of the deployment or a LeptonDeployment object.",
)
@click.option(
    "--job", type=str, default=None, help="The name of the job or a LeptonJob object."
)
@click.option(
    "--replica",
    type=str,
    default=None,
    help="The name of the replica or a Replica object.",
)
@click.option(
    "--job-history-name", type=str, default=None, help="The name of the job history."
)
@click.option(
    "--start",
    type=str,
    default=None,
    help="The start time in ISO format.",
    callback=preprocess_time,
)
@click.option(
    "--end",
    type=str,
    default=None,
    help="The end time in ISO format.",
    callback=preprocess_time,
)
@click.option(
    "--limit",
    type=int,
    default=5000,
    show_default=True,
    help="The maximum line of results to return.",
)
def log_command(
    deployment,
    job,
    replica,
    job_history_name,
    start,
    end,
    limit,
):
    # console.print(start)
    # console.print(end)
    # sys.exit(0)
    if not deployment and not job and not replica and not job_history_name:
        console.print("[red]No deployment name, job name or replica id provided.[/red]")
        sys.exit(1)

    if not end:
        console.print("[red]No end time provided.[/red]")
        sys.exit(1)

    client = APIClient()

    log_dict = client.log.get_log(
        name_or_deployment=deployment,
        name_or_job=job,
        replica=replica,
        job_history_name=job_history_name,
        start=start,
        end=end,
        limit=limit,
    )
    lines = log_dict["data"]["result"]

    first_local_time = None
    last_local_time = None
    count = 0
    for line in lines:
        values = line["values"]
        for value in values:
            local_time = convert_to_local_time(value[0])
            first_local_time = first_local_time if first_local_time else local_time
            last_local_time = local_time
            cur_line = safe_load_json(value[1])
            count += 1
            console.print(f"[green]{local_time}|[/]{json.dumps(cur_line)}")

    cur_timezone = datetime.now().astimezone().tzname()
    console.print(
        f"\n[blue]👆Time lapse:[/] [green]{cur_timezone}|{first_local_time}[/] → "
        f"[green]{cur_timezone}|{last_local_time}[/] total [green]{count}[/] lines \n"
    )


def add_command(cli_group):
    cli_group.add_command(log)
