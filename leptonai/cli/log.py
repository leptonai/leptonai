import re
import sys
import os

from .job import _get_newest_job_by_name
from .util import click_group, console

from ..api.v2.client import APIClient

import json
import click

from datetime import datetime, timedelta, timezone
from rich.progress import Progress

str_time_format = "%Y-%m-%d %H:%M:%S.%f"
str_date_format = "%Y-%m-%d"

supported_formats = """
        Please note that all times must be in UTC. 
        Keywords such as “now,” “today,” and “yesterday” will be interpreted as UTC timestamps. 
        For example, “now” corresponds to datetime.now(timezone.utc).

        - now
          Example: now (indicates the current time in UTC)

        - Full Date and Time:
          Format: YYYY/MM/DD HH:MM:SS.123456
          Example: 2024/12/25 13:10:01.123456

          Alternate Format: YYYY-MM-DD HH:MM:SS.123456
          Example: 2024-12-25 13:10:01.123456

        - today or td:
          Example Variations:
          today (defaults to midnight of the current day in UTC)
          today 01 (1 AM of the current day)
          today 01:10 (1:10 AM of the current day)
          today 01:10:01 (1:10:01 AM of the current day)
          today 01:10:01.123456 (1:10:01 AM with microseconds precision)

        - yesterday or yd:
          Example Variations:
          yesterday (defaults to midnight of the previous day in UTC)
          yesterday 13 (1 PM of the previous day)
          yesterday 13:10 (1:10 PM of the previous day)
          yesterday 13:10:05 (1:10:05 PM of the previous day)
          yesterday 13:10:01.123456 (1:10:01 PM with microseconds precision on the previous day)
        """


def _preprocess_time(input_time, epoch=False):
    """
    Preprocesses custom time formats like YD (yesterday) or TD (today).
    """
    if epoch:
        search_time_offset_ns = 0
        if input_time.startswith("search_before,"):
            input_time = input_time[len("search_before,") :]
            console.print(input_time)
            search_time_offset_ns = -2 * 24 * 60 * 60 * 1_000_000_000

    now = datetime.now(timezone.utc)
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

    # Parse the time and ensure it uses the utc timezone
    try:
        parsed_time = datetime.fromisoformat(input_time).replace(tzinfo=timezone.utc)
    except ValueError:
        console.print(
            "[red]Invalid time format. Supported formats are:[/]\n" + supported_formats
        )
        sys.exit(1)

    if epoch:
        return int(parsed_time.timestamp() * 1_000_000_000) + search_time_offset_ns

    return parsed_time


def _epoch_to_utc_time_str(nanoseconds):
    """
    Convert a timestamp in nanoseconds to the utc time

    Args:
        nanoseconds (int or str): The timestamp in nanoseconds.

    Returns:
        str: The utc time string.
    """
    if isinstance(nanoseconds, str):
        nanoseconds = int(nanoseconds)

    # Convert nanoseconds to seconds
    seconds = nanoseconds / 1e9
    # Create an aware UTC datetime object
    utc_time = datetime.fromtimestamp(seconds, tz=timezone.utc)

    return utc_time.strftime(str_time_format)


def safe_load_json(string):
    try:
        return json.loads(string)
    except json.JSONDecodeError:
        return string


@click_group()
def log():
    pass


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
    "--job-name",
    "-jn",
    type=str,
    default=None,
    help=(
        "Specifies the job name. If multiple jobs share this name, "
        "the logs for the newest job found will be retrieved by default."
    ),
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
)
@click.option(
    "--end",
    type=str,
    default=None,
    help="The end time in ISO format.",
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
@click.option(
    "--query",
    type=str,
    default="",
    help="Specify the query string",
)
def log_command(
    deployment,
    job,
    job_name,
    replica,
    job_history_name,
    start,
    end,
    limit,
    path,
    query,
):
    if (
        not deployment
        and not job
        and not job_name
        and not replica
        and not job_history_name
    ):
        console.print(
            "[red]No deployment name, job id, job name or replica id provided.[/red]"
        )
        sys.exit(1)

    if sum(bool(var) for var in [deployment, job, job_name, job_history_name]) > 1:
        raise ValueError(
            "Only one of 'deployment', 'job', or 'job_history_name' can be specified."
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

    if job_name is not None:
        job = _get_newest_job_by_name(job_name)
        if job is None:
            console.print(
                f"[bold red]Warning:[/bold red] No job named '{job_name}' found."
            )
            sys.exit(1)
        job = job.metadata.id_

    def fetch_log(start, end, limit):
        unix_start = _preprocess_time(start, epoch=True)
        unix_end = _preprocess_time(end, epoch=True)
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
                    q=query,
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

        first_utc_time = (
            _epoch_to_utc_time_str(log_list[-1][0]) if len(log_list) > 0 else start
        )
        last_utc_time = (
            _epoch_to_utc_time_str(log_list[0][0]) if len(log_list) > 0 else end
        )

        if path:
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            if os.path.isdir(path):
                default_filename = f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                path = os.path.join(path, default_filename)

            with open(path, "w", encoding="utf-8") as f:
                f.write(
                    f"Time range: UTC|{first_utc_time} → "
                    f"UTC|{last_utc_time} | total {len(log_list)} lines \n"
                )
                for log in reversed(log_list):
                    utc_time = _epoch_to_utc_time_str(log[0])
                    cur_line = safe_load_json(log[1])
                    f.write(f"{utc_time}｜{cur_line}\n")
            console.print(
                f"\n[bold green]Successfully saved the log to:[/bold green] {path}\n"
            )
            sys.exit(0)
        else:
            for log in reversed(log_list):
                utc_time = _epoch_to_utc_time_str(log[0])
                cur_line = safe_load_json(log[1])
                console.print(f"[green]{utc_time}|[/]", end="")
                console.print(json.dumps(cur_line, ensure_ascii=False), markup=False)

            console.print(
                f"\n👆Time range: [blue]UTC|{first_utc_time}[/] →"
                f" [blue]UTC|{last_utc_time}[/] total"
                f" [green]{len(log_list)}[/] lines \n"
            )
        return first_utc_time, last_utc_time

    first_utc_time, last_utc_time = fetch_and_print_logs(start, end, limit, path)

    while True and sys.stdin.isatty():
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
            first_utc_time, last_utc_time = fetch_and_print_logs(
                last_utc_time, "now", line_count
            )

        elif cmd == "last":
            try:
                line_count = int(param)
            except (IndexError, ValueError):
                console.print("[red]Please specify a valid number of lines.[/red]")
                continue
            first_utc_time, last_utc_time = fetch_and_print_logs(
                "search_before," + first_utc_time, first_utc_time, line_count
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
                last_utc_time_obj = _preprocess_time(last_utc_time)
                adjusted_last_utc_time = last_utc_time_obj + timedelta(
                    seconds=int_seconds, microseconds=microseconds
                )
                adjusted_last_utc_time = adjusted_last_utc_time.strftime(
                    str_time_format
                )
                first_utc_time, last_utc_time = fetch_and_print_logs(
                    last_utc_time, adjusted_last_utc_time, 5000
                )

            if cmd == "time-":
                first_utc_time_obj = _preprocess_time(first_utc_time)
                adjusted_first_utc_time = first_utc_time_obj - timedelta(
                    seconds=int_seconds, microseconds=microseconds
                )
                adjusted_first_utc_time = adjusted_first_utc_time.strftime(
                    str_time_format
                )
                first_utc_time, last_utc_time = fetch_and_print_logs(
                    adjusted_first_utc_time, first_utc_time, 5000
                )


def add_command(cli_group):
    cli_group.add_command(log)
