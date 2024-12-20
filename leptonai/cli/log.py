import re
import sys

from .util import click_group, console

from ..api.v1.client import APIClient

import json
import click

from datetime import datetime, timedelta, timezone

str_time_format = "%Y-%m-%d %H:%M:%S.%f"
str_date_format = "%Y-%m-%d"
def preprocess_time(input_time):
    """
    Preprocesses custom time formats like YD (yesterday) or TD (today).
    """
    now = datetime.now().astimezone()
    input_time = input_time.lower().replace("today", now.strftime(str_date_format), 1)
    input_time = input_time.lower().replace("td", now.strftime(str_date_format), 1)
    input_time = input_time.lower().replace(
        "yesterday", (now - timedelta(days=1)).strftime(str_date_format), 1
    )
    input_time = input_time.lower().replace(
        "yd", (now - timedelta(days=1)).strftime(str_date_format), 1
    )
    if input_time.lower() == "now":
        input_time = now.strftime(str_time_format)
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

    return local_time


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
    # callback=preprocess_time,
)
@click.option(
    "--end",
    type=str,
    default=None,
    help="The end time in ISO format.",
    # callback=preprocess_time,
)
@click.option(
    "--limit",
    type=int,
    default=5000,
    show_default=True,
    help="The maximum number of result lines to return, up to 5000.",
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
    if not deployment and not job and not replica and not job_history_name:
        console.print("[red]No deployment name, job name or replica id provided.[/red]")
        sys.exit(1)

    if not end:
        console.print("[red]Warning[/red] No end time provided. will be set to Now")
        end = "now"
    if not start:
        console.print("[red]Warning[/red] No start time provided. will be set to today (today 00:00:00)")

    client = APIClient()

    def fetch_and_print_logs(start, end, limit):
        unix_start = preprocess_time(start)
        unix_end = preprocess_time(end)
        if unix_end <= unix_start:
            console.print("[red]Warning[/red] End time must be greater than start time.")
            sys.exit(1)
        log_dict = client.log.get_log(
            name_or_deployment=deployment,
            name_or_job=job,
            replica=replica,
            job_history_name=job_history_name,
            start=unix_start,
            end=unix_end,
            limit=limit
        )
        lines = log_dict["data"]["result"]
        first_local_time = None
        last_local_time = None
        count = 0

        log_list = []
        for line in lines:
            values = line["values"]
            for value in values:
                log_list.append((int(value[0]), value[1]))

        log_list.sort(key=lambda x: x[0])

        for log in log_list:
            local_time = convert_to_local_time(log[0]).strftime(str_time_format)
            if first_local_time is None:
                first_local_time = local_time
            last_local_time = local_time
            cur_line = safe_load_json(log[1])
            count += 1
            console.print(f"[green]{local_time}|[/]{json.dumps(cur_line)}")

        cur_timezone = datetime.now().astimezone().tzname()
        first_local_time = first_local_time or start
        last_local_time = last_local_time or end
        console.print(
            f"\n👆Time range: [blue]{cur_timezone}|{first_local_time}[/] → "
            f"[blue]{cur_timezone}|{last_local_time}[/] total [green]{count}[/] lines \n"
        )
        return first_local_time, last_local_time

    first_local_time, last_local_time = fetch_and_print_logs(start, end, limit)
    while True:
        console.print("Enter a command [yellow](e.g., `next 10`, `last 20`, `time+ 30.5s`, `time- 2.1s`, `quit`)[/]:")
        user_input = input().strip()
        if user_input.lower() in ["q", "quit", "exit"]:
            console.print("[lightblue]Exiting log viewer.[/]")
            break

        cmd_parts = user_input.split()
        if cmd_parts is None or len(cmd_parts) != 2 or cmd_parts[0] not in ["next", "last", "time+", "time-"]:
            console.print("[red]Invalid command[/] we only accept next, last, time+ and time-")
            continue
        cmd, param = cmd_parts

        if cmd == "next":
            try:
                line_count = int(param)
            except (IndexError, ValueError):
                console.print("[red]Please specify a valid number of lines.[/red]")
                continue
            first_local_time, last_local_time = fetch_and_print_logs(last_local_time, 'now', line_count)

        elif cmd == "last":
            try:
                line_count = int(param)
            except (IndexError, ValueError):
                console.print("[red]Please specify a valid number of lines.[/red]")
                continue
            first_local_time, last_local_time = fetch_and_print_logs('yesterday', first_local_time, line_count)
        elif cmd == "time+" or cmd == "time-":
            pattern = r'^\d+(\.\d+)?s$'
            if not re.match(pattern, param):
                console.print("[red]Invalid offset format. Expected something like '2.567s'.[/]")
                continue

            seconds_str = param[:-1]  # remove the trailing 's'
            try:
                float_seconds = float(seconds_str)
            except ValueError:
                console.print(f"[red]Failed to parse the numeric value {seconds_str} in the offset.[/red]")
                continue

            int_seconds = int(float_seconds)
            microseconds = int((float_seconds - int_seconds)*1_000_000)

            if cmd == "time+":
                last_local_time_obj = datetime.strptime(last_local_time, str_time_format)
                adjusted_last_local_time = last_local_time_obj + timedelta(seconds=int_seconds,
                                                                                microseconds=microseconds)
                adjusted_last_local_time = adjusted_last_local_time.strftime(str_time_format)
                console.print("<<<<<<<<<")
                console.print(last_local_time)
                console.print(adjusted_last_local_time)
                console.print("<<<<<<<<<")
                first_local_time, last_local_time = fetch_and_print_logs(last_local_time, adjusted_last_local_time, 5000)

            if cmd == "time-":
                first_local_time_obj = datetime.strptime(first_local_time, str_time_format)
                adjusted_first_local_time = first_local_time_obj - timedelta(seconds=int_seconds,
                                                                                microseconds=microseconds)
                adjusted_first_local_time = adjusted_first_local_time.strftime(str_time_format)
                console.print("<<<<<<<<<")
                console.print(adjusted_first_local_time)
                console.print(first_local_time)
                console.print("<<<<<<<<<")
                first_local_time, last_local_time = fetch_and_print_logs(adjusted_first_local_time, first_local_time,
                                                                         5000)



def add_command(cli_group):
    cli_group.add_command(log)
