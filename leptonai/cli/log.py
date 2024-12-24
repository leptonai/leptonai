import re
import sys
import os
from .util import click_group, console

from ..api.v1.client import APIClient

import json
import click

from datetime import datetime, timedelta, timezone
from rich.progress import Progress

str_time_format = "%Y-%m-%d %H:%M:%S.%f"
str_date_format = "%Y-%m-%d"


def preprocess_time(input_time, unix_format=False):
    """
    Preprocesses custom time formats like YD (yesterday) or TD (today).
    """
    now = datetime.now().astimezone()
    input_time = input_time.replace("/", "-")

    input_time = re.sub(
        r"(\.\d{1,5})(?!\d)", lambda m: m.group(1).ljust(7, "0"), input_time
    )

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
    parsed_time = datetime.fromisoformat(input_time).astimezone(now.tzinfo)

    if unix_format:
        return int(
            parsed_time.timestamp() * 1_000_000_000 + parsed_time.microsecond * 1_000
        )
    return parsed_time


def unix_to_local_time_str(nanoseconds):
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

    return local_time.strftime(str_time_format)


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
    "--job",
    "-j",
    type=str,
    default=None,
    help="Specifies the job ID. To find the job ID, use the 'lep job list' command.",
)
@click.option(
    "--replica",
    type=str,
    default=None,
    help="The name of the replica or a Replica object.",
)
@click.option(
    "--job-history-name",
    type=str,
    default=None,
    help="The name of the job history.",
    hidden=True,
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
    help="The maximum number of result lines to return.(default: 5000)",
)
@click.option(
    "--path",
    type=click.Path(
        exists=False,
        file_okay=True,
        dir_okay=True,
        writable=True,
        readable=True,
        resolve_path=True,
    ),
    default=None,
    show_default=True,
    help="Local directory path to save the log TXT files.",
)
def log_command(
    deployment,
    job,
    replica,
    job_history_name,
    start,
    end,
    limit,
    path,
):
    if not deployment and not job and not replica and not job_history_name:
        console.print("[red]No deployment name, job name or replica id provided.[/red]")
        sys.exit(1)

    if sum(bool(var) for var in [deployment, job, job_history_name]) > 1:
        raise ValueError(
            "Only one of 'deployment', 'job', 'replica', or 'job_history_name' can be"
            " specified."
        )

    if not end:
        console.print("[red]Warning[/red] No end time provided. will be set to Now")
        end = "now"
    if not start:
        console.print(
            "[red]Warning[/red] No start time provided. will be set to today (today"
            " 00:00:00)"
        )
        start = "today"

    client = APIClient()

    def fetch_log(start, end, limit):
        unix_start = preprocess_time(start, unix_format=True)
        unix_end = preprocess_time(end, unix_format=True)
        if unix_end <= unix_start:
            console.print(
                "[red]Warning[/red] End time must be greater than start time."
            )
            sys.exit(1)

        log_list = []
        cur_unix_end = unix_end
        cur_limit = limit
        with Progress() as progress:
            task = progress.add_task("Fetching logs...", total=limit)
            while cur_limit > 0:
                progress.update(task, completed=limit - cur_limit)
                log_dict = client.log.get_log(
                    name_or_deployment=deployment,
                    name_or_job=job,
                    replica=replica,
                    job_history_name=job_history_name,
                    start=unix_start,
                    end=cur_unix_end,
                    limit=cur_limit if cur_limit < 10000 else 10000,
                )
                lines = log_dict["data"]["result"]

                cur_log_list = []

                for line in lines:
                    values = line["values"]
                    for value in values:
                        cur_log_list.append((int(value[0]), value[1]))

                # Break out of the loop if no logs exist in the specified time range
                if len(cur_log_list) == 0:
                    break
                # By setting reverse=True, the resulting list will be ordered from newest to oldest.
                # The subsequent while loop also produces a list from newest to oldest, allowing us
                # to easily extend them and, if desired, reverse the final combined list just once.
                cur_log_list.sort(key=lambda x: x[0], reverse=True)

                cur_limit -= len(cur_log_list)
                cur_unix_end = cur_log_list[-1][0]

                log_list.extend(cur_log_list)

        return log_list

    def fetch_and_print_logs(start, end, limit, path=None):

        log_list = fetch_log(start, end, limit)

        first_local_time = (
            unix_to_local_time_str(log_list[-1][0]) if len(log_list) > 0 else start
        )
        last_local_time = (
            unix_to_local_time_str(log_list[0][0]) if len(log_list) > 0 else end
        )
        cur_timezone = datetime.now().astimezone().tzname()

        if path:
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            if os.path.isdir(path):
                default_filename = f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                path = os.path.join(path, default_filename)

            with open(path, "w", encoding="utf-8") as f:
                f.write(
                    f"Time range: {cur_timezone}|{first_local_time} → "
                    f"{cur_timezone}|{last_local_time} | total {len(log_list)} lines \n"
                )
                for log in reversed(log_list):
                    local_time = unix_to_local_time_str(log[0])
                    cur_line = safe_load_json(log[1])
                    f.write(f"\n{local_time}｜{cur_line}\n")
                    # f.write(f"**{local_time}｜{cur_line}\n")
            console.print(
                f"\n[bold green]Successfully saved the log to:[/bold green] {path}\n"
            )
            sys.exit(0)
        else:
            for log in reversed(log_list):
                local_time = unix_to_local_time_str(log[0])
                cur_line = safe_load_json(log[1])
                console.print(f"[green]{local_time}|[/]", end="")
                console.print(json.dumps(cur_line), markup=False)

            console.print(
                f"\n👆Time range: [blue]{cur_timezone}|{first_local_time}[/] →"
                f" [blue]{cur_timezone}|{last_local_time}[/] total"
                f" [green]{len(log_list)}[/] lines \n"
            )
        return first_local_time, last_local_time

    first_local_time, last_local_time = fetch_and_print_logs(start, end, limit, path)

    while True:
        console.print(
            "Enter a command [yellow](e.g., `next 10`, `last 20`, `time+ 30.5s`, `time-"
            " 2.1s`, `quit`)[/]:"
        )
        user_input = input().strip()
        if user_input.lower() in ["q", "quit", "exit"]:
            console.print("[lightblue]Exiting log viewer.[/]")
            break

        cmd_parts = user_input.split()
        if (
            cmd_parts is None
            or len(cmd_parts) != 2
            or cmd_parts[0] not in ["next", "last", "time+", "time-"]
        ):
            console.print(
                "[red]Invalid command[/] we only accept next, last, time+ and time-"
            )
            continue
        cmd, param = cmd_parts

        if cmd == "next":
            try:
                line_count = int(param)
            except (IndexError, ValueError):
                console.print("[red]Please specify a valid number of lines.[/red]")
                continue
            first_local_time, last_local_time = fetch_and_print_logs(
                last_local_time, "now", line_count
            )

        elif cmd == "last":
            try:
                line_count = int(param)
            except (IndexError, ValueError):
                console.print("[red]Please specify a valid number of lines.[/red]")
                continue
            first_local_time, last_local_time = fetch_and_print_logs(
                "yesterday", first_local_time, line_count
            )
        elif cmd == "time+" or cmd == "time-":
            pattern = r"^\d+(\.\d+)?s$"
            if not re.match(pattern, param):
                console.print(
                    "[red]Invalid offset format. Expected something like '2.567s'.[/]"
                )
                continue

            seconds_str = param[:-1]  # remove the trailing 's'
            try:
                float_seconds = float(seconds_str)
            except ValueError:
                console.print(
                    f"[red]Failed to parse the numeric value {seconds_str} in the"
                    " offset.[/red]"
                )
                continue

            int_seconds = int(float_seconds)
            microseconds = int((float_seconds - int_seconds) * 1_000_000)

            if cmd == "time+":
                last_local_time_obj = preprocess_time(last_local_time)
                adjusted_last_local_time = last_local_time_obj + timedelta(
                    seconds=int_seconds, microseconds=microseconds
                )
                adjusted_last_local_time = adjusted_last_local_time.strftime(
                    str_time_format
                )
                first_local_time, last_local_time = fetch_and_print_logs(
                    last_local_time, adjusted_last_local_time, 5000
                )

            if cmd == "time-":
                first_local_time_obj = preprocess_time(first_local_time)
                adjusted_first_local_time = first_local_time_obj - timedelta(
                    seconds=int_seconds, microseconds=microseconds
                )
                adjusted_first_local_time = adjusted_first_local_time.strftime(
                    str_time_format
                )
                first_local_time, last_local_time = fetch_and_print_logs(
                    adjusted_first_local_time, first_local_time, 5000
                )


def add_command(cli_group):
    cli_group.add_command(log)
