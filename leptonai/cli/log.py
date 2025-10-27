import re
import sys
import os

from .util import _get_newest_job_by_name
from .util import click_group, console

from ..api.v2.client import APIClient

import json
import click
import time

from datetime import datetime, timedelta, timezone
from rich.progress import Progress
from concurrent.futures import ThreadPoolExecutor, as_completed

str_time_format = "%Y-%m-%d %H:%M:%S.%f"
str_date_format = "%Y-%m-%d"

_supported_formats_log = """
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


def _preprocess_time(
    input_time, local_time=False, epoch=False, supported_formats=_supported_formats_log
):
    """Parse user time input into a timezone-aware datetime (UTC by default) or a
    nanosecond epoch timestamp.

    Supported inputs:
    - Keywords (can be combined with time of day):
      - now
      - today / td
      - yesterday / yd
      - tomorrow / tm
      Examples: "today", "today 01", "today 01:10", "today 01:10:01.123456"

    - Standard formats (microseconds optional):
      - YYYY-MM-DD HH:MM:SS[.ffffff]
      - YYYY/MM/DD HH:MM:SS[.ffffff]

    Behavior:
    - Parsed as UTC by default; if local_time=True, parse/convert in local timezone.
    - If epoch=True, return a nanosecond timestamp; otherwise return a datetime.
    - If epoch=True and input starts with "search_before,", subtract an extra 2 days
      from the resulting timestamp (used by historical search windows).

    On invalid formats, prints supported formats and exits the program.
    """
    if epoch:
        search_time_offset_ns = 0
        if isinstance(input_time, str) and input_time.startswith("search_before,"):
            input_time = input_time[len("search_before,") :]
            console.print(input_time)
            search_time_offset_ns = -2 * 24 * 60 * 60 * 1_000_000_000

        if isinstance(input_time, (int, float)) or (
            isinstance(input_time, str) and re.fullmatch(r"-?\d+", input_time.strip())
        ):
            epoch_int = int(input_time)
            abs_val = abs(epoch_int)
            if abs_val < 100_000_000_000:  # seconds
                ns = epoch_int * 1_000_000_000
            elif abs_val < 100_000_000_000_000:  # milliseconds
                ns = epoch_int * 1_000_000
            elif abs_val < 100_000_000_000_000_000:  # microseconds
                ns = epoch_int * 1_000
            else:  # nanoseconds
                ns = epoch_int
            return ns + search_time_offset_ns

    now = datetime.now(timezone.utc) if not local_time else datetime.now().astimezone()

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
    input_time = input_time.lower().replace(
        "tomorrow", (now + timedelta(days=1)).strftime(str_date_format), 1
    )
    input_time = input_time.lower().replace(
        "tm", (now + timedelta(days=1)).strftime(str_date_format), 1
    )
    if input_time.lower() == "now":
        input_time = now.strftime(str_time_format)

    # Parse the time and ensure it uses the utc timezone
    try:
        parsed_time = datetime.fromisoformat(input_time)
        if not local_time:
            parsed_time = parsed_time.replace(tzinfo=timezone.utc)

    except ValueError:
        console.print(
            "[red]Invalid time format. Supported formats are:[/]\n" + supported_formats
        )
        sys.exit(1)

    if epoch:
        return int(parsed_time.timestamp() * 1_000_000_000) + search_time_offset_ns

    return parsed_time


def _epoch_to_time_str(nanoseconds, local_time=False):
    """Convert a nanosecond timestamp to a formatted time string.

    Args:
        nanoseconds (int or str): Timestamp in nanoseconds since epoch
        local_time (bool): If True, convert to local timezone; if False, use UTC

    Returns:
        str: Formatted time string in format 'YYYY-MM-DD HH:MM:SS.ffffff'

    Examples:
        >>> _epoch_to_time_str(1710928800000000000)  # UTC
        '2024-03-20 10:00:00.000000'
        >>> _epoch_to_time_str(1710928800000000000, local_time=True)  # Local time
        '2024-03-20 03:00:00.000000'  # Example for Los Angeles (UTC-7)
    """
    if isinstance(nanoseconds, str):
        nanoseconds = int(nanoseconds)

    # Convert nanoseconds to seconds
    seconds = nanoseconds / 1e9
    # Create an aware UTC datetime object
    if local_time:
        time_obj = datetime.fromtimestamp(seconds)
    else:
        time_obj = datetime.fromtimestamp(seconds, tz=timezone.utc)

    return time_obj.strftime(str_time_format)


def safe_load_json(string):
    try:
        return json.loads(string)
    except json.JSONDecodeError:
        return string


def fetch_all_within_time_slot(
    deployment,
    job,
    replica,
    job_history_name,
    query,
    time_start,
    time_end,
    cur_log_result,
):
    client = APIClient()
    while time_end >= time_start:
        log_dict = client.log.get_log(
            name_or_deployment=deployment,
            name_or_job=job,
            replica=replica,
            job_history_name=job_history_name,
            start=time_start,
            end=time_end,
            limit=10000,
            q=query,
        )

        lines = log_dict["data"]["result"]
        cur_log_list = []
        for line in lines:
            values = line["values"]
            for value in values:
                cur_log_list.append((int(value[0]), value[1]))

        if len(cur_log_list) == 0:
            break
        cur_log_list.sort(key=lambda x: x[0], reverse=True)
        time_end = cur_log_list[-1][0]
        if len(cur_log_list) > 0:
            cur_log_result.extend(cur_log_list)


@click_group()
def log():
    """
    Manage and retrieve the logs history of specific jobs, deployments and replicas.
    """
    pass


@log.command(
    name="get", help="Retrieve and display logs from deployments, jobs, or replicas"
)
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
    help="The start time in ISO format. " + _supported_formats_log,
)
@click.option(
    "--end",
    type=str,
    default=None,
    help="The end time in ISO format. " + _supported_formats_log,
)
@click.option(
    "--limit",
    type=int,
    default=None,
    help="[Deprecated] This option is deprecated and not recommended.",
    hidden=True,
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
@click.option(
    "--without-timestamp",
    is_flag=True,
    default=False,
    help="Without timestamp",
)
@click.option(
    "--workers",
    "-w",
    type=click.IntRange(1, 128),
    default=None,
    show_default=False,
    help=(
        "Set the number of concurrent worker threads for fetching logs. "
        "Effective only when --limit is not used. Defaults to 32 when unspecified. "
        "Note: --limit is deprecated and not recommended."
    ),
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
    without_timestamp,
    workers,
):
    """
    Retrieve and display logs from deployments, jobs, or replicas.

    IMPORTANT:
    - 'lep log get' and 'lep log get --path' are intended for lightweight jobs and
      short time ranges.
    - They are NOT recommended for downloading logs of long-running jobs with many
      replicas.
    - Prefer using Workspace Dashboard -> Settings -> Logs Export for downloading
      large-volume logs (jobs/endpoints long-running or with many replicas).
    - Concurrency (workers) is applied only when --limit is NOT used.
    - --limit is deprecated and not recommended. When set, logs will be fetched
      sequentially without parallelism. It will be removed in a future release.
    - Interactive mode (next/last/time+/time-) is deprecated and not recommended.
      It will be removed in a future release.

    JOB DEFAULT TIME RANGE:
    - For jobs, --start/--end can be omitted. If omitted, the job's creation_time
      and completion_time (when available) will be used automatically.

    EXAMPLE:
    # Get logs from a job by ID using default job time range
    lep log get -j job-abc123
    lep log get -j job-abc123 --path ./logs/

    TIME FORMATS:
    All times must be in UTC. Supported formats include:
    - 'now' - Current UTC time
    - 'today' or 'td' - Today at midnight UTC (can add time: 'today 14:30')
    - 'yesterday' or 'yd' - Yesterday at midnight UTC (can add time: 'yesterday 09:15')
    - Full datetime: '2024-12-25 13:10:01.123456' or '2024/12/25 13:10:01.123456'

    EXAMPLES:
    # Get logs from a deployment for the last hour
    lep log get -d my-deployment --start "today 13:00" --end "today 14:00"

    # Get logs from a job by name for today
    lep log get -jn my-job-name --start today --end now

    # Get logs from a specific job ID with query filter
    lep log get -j job-abc123 --start yesterday --end today --query "error"

    # Save logs to file
    lep log get -d my-deployment --start "today 09:00" --end now --path ./logs/
    """

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

    client = APIClient()

    if job_name is not None:
        job = _get_newest_job_by_name(job_name)
        if job is None:
            console.print(
                f"[bold red]Warning:[/bold red] No job named '{job_name}' found."
            )
            sys.exit(1)
        job = job.metadata.id_

    if (job or deployment) and replica:
        replicas = (
            client.job.get_replicas(job)
            if job
            else client.deployment.get_replicas(deployment)
        )
        if replica not in [replica.metadata.id_ for replica in replicas]:
            console.print(
                f"[bold red]Warning:[/bold red] No replica named '{replica}' found for"
                f" {job if job else deployment}."
            )
            sys.exit(1)

    if (not start or not end) and job:
        job_obj = client.job.get(job)
        if job_obj.status is not None and job_obj.status.completion_time is not None:
            start = start or job_obj.status.creation_time
            end = end or job_obj.status.completion_time

    if not end:
        console.print("[red]Warning[/red] No end time provided. will be set to Now")
        end = "now"
    if not start:
        console.print(
            "[red]Warning[/red] No start time provided. will be set to today (today"
            " 00:00:00)"
        )
        start = "today"

    def fetch_log(start, end, limit, path=None):
        unix_start = _preprocess_time(start, epoch=True)
        unix_end = _preprocess_time(end, epoch=True)
        if unix_end <= unix_start:
            console.print(
                "[red]Warning[/red] End time must be greater than start time."
            )
            sys.exit(1)

        if limit is None:

            time_range = unix_end - unix_start
            MIN_SLOT_NS = 1_000_000_000
            time_slot = max(MIN_SLOT_NS, time_range // 1600)

            time_windows = []
            for start_ns in range(unix_start, unix_end, time_slot):
                end_ns = min(start_ns + time_slot, unix_end)
                time_windows.append((start_ns, end_ns))
            log_list = [[] for _ in range(len(time_windows))]
            start_perf = time.perf_counter()
            with Progress() as progress:
                worker_count = (
                    min(len(time_windows), workers)
                    if workers is not None
                    else min(len(time_windows), 32)
                )
                with ThreadPoolExecutor(max_workers=worker_count) as executor:
                    task = progress.add_task(
                        "Fetching logs...", total=len(time_windows)
                    )
                    futures = []
                    future_to_index = {}
                    for index, (time_start, time_end) in enumerate(time_windows):

                        future = executor.submit(
                            fetch_all_within_time_slot,
                            deployment,
                            job,
                            replica,
                            job_history_name,
                            query,
                            time_start,
                            time_end,
                            log_list[index],
                        )
                        futures.append(future)
                        future_to_index[future] = index

                    future_complete_list = [False for _ in range(len(time_windows))]
                    if path:
                        directory = os.path.dirname(path)
                        if directory and not os.path.exists(directory):
                            try:
                                os.makedirs(directory)
                            except Exception as e:
                                console.print(
                                    f"[red][ERROR]{directory} not exist and failed to"
                                    f" create directory:[/] {directory} ({e})"
                                )
                                sys.exit(1)
                        if os.path.isdir(path):
                            default_filename = (
                                f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                            )
                            path = os.path.join(path, default_filename)

                        next_writing_index = 0
                        total_lines = 0
                        first_utc_time = ""
                        last_utc_time = ""
                        with open(path, "w", encoding="utf-8") as f:
                            for future in as_completed(futures):
                                future.result()
                                index = future_to_index[future]
                                while next_writing_index < len(time_windows) and (
                                    future_complete_list[next_writing_index] is True
                                    or index == next_writing_index
                                ):
                                    if len(log_list[next_writing_index]) > 0:
                                        if total_lines == 0:
                                            first_utc_time = _epoch_to_time_str(
                                                log_list[next_writing_index][-1][0]
                                            )

                                        total_lines += len(log_list[next_writing_index])

                                        if next_writing_index == len(time_windows) - 1:
                                            last_utc_time = _epoch_to_time_str(
                                                log_list[next_writing_index][0][0]
                                            )
                                        for log in reversed(
                                            log_list[next_writing_index]
                                        ):
                                            utc_time = _epoch_to_time_str(log[0])
                                            cur_line = safe_load_json(log[1])
                                            if without_timestamp:
                                                f.write(f"{cur_line}\n")
                                            else:
                                                f.write(f"{utc_time}｜{cur_line}\n")
                                    log_list[next_writing_index] = None
                                    next_writing_index += 1
                                    if index == next_writing_index:
                                        progress.update(task, advance=1)
                                else:
                                    future_complete_list[index] = True
                                    progress.update(task, advance=1)
                            elapsed_sec = time.perf_counter() - start_perf
                            f.write(
                                f"Time range: UTC|{first_utc_time} → "
                                f"UTC|{last_utc_time} | total {total_lines} lines \n"
                            )
                        console.print(
                            f"\n[bold]Time range[/]: [bold cyan]UTC|{first_utc_time}[/]"
                            f" → [blue]UTC|{last_utc_time}[/]\n[bold]Total[/]:"
                            f" [green]{total_lines}[/] lines \n[bold cyan]Duration[/]:"
                            f" [magenta]{elapsed_sec:.2f}s[/]\n"
                        )
                        console.print(
                            "\n[bold green]Successfully saved the log to:[/bold green]"
                            f" {path}\n"
                        )

                        sys.exit(0)
                    else:
                        result_log_list = []
                        for future in as_completed(futures):
                            future.result()
                            index = future_to_index[future]
                            progress.update(task, advance=1)

                        for log in log_list:
                            result_log_list.extend(log)

                    return reversed(result_log_list)

        # ======================================================================
        # LEGACY MODE
        # The following code is legacy and will be removed in the future.
        # Everything below handles the "limit" workflow for log processing and
        # output. Keep in mind this entire section is considered legacy.
        # ======================================================================
        log_list = []
        cur_unix_end = unix_end
        cur_limit = limit
        time_total_ns = max(1, unix_end - unix_start)
        with Progress() as progress:
            task = progress.add_task("Fetching logs...", total=time_total_ns)
            while cur_limit > 0:
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
                    progress.update(task, completed=True)
                    break
                # By setting reverse=True, the resulting list will be ordered from newest to oldest.
                # The subsequent while loop also produces a list from newest to oldest, allowing us
                # to easily extend them and, if desired, reverse the final combined list just once.
                cur_log_list.sort(key=lambda x: x[0], reverse=True)

                cur_limit -= len(cur_log_list)
                prev_unix_end = cur_unix_end
                cur_unix_end = cur_log_list[-1][0]
                progress.update(task, advance=prev_unix_end - cur_unix_end)

                log_list.extend(cur_log_list)

        return log_list

    def fetch_and_print_logs(start, end, limit, path=None):

        log_list = fetch_log(start, end, limit, path)
        if not limit:
            return

        # ======================================================================
        # LEGACY MODE
        # The following code is legacy and will be removed in the future.
        # Everything below handles the "limit" workflow for log processing and
        # output. Keep in mind this entire section is considered legacy.
        # ======================================================================
        first_utc_time = (
            _epoch_to_time_str(log_list[-1][0]) if len(log_list) > 0 else start
        )
        last_utc_time = _epoch_to_time_str(log_list[0][0]) if len(log_list) > 0 else end
        if path and limit is not None:
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                try:
                    os.makedirs(directory)
                except Exception as e:
                    console.print(
                        f"[red][ERROR]{directory} not exist and failed to create"
                        f" directory:[/] {directory} ({e})"
                    )
                    sys.exit(1)
            if os.path.isdir(path):
                default_filename = f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                path = os.path.join(path, default_filename)

            with open(path, "w", encoding="utf-8") as f:
                f.write(
                    f"Time range: UTC|{first_utc_time} → "
                    f"UTC|{last_utc_time} | total {len(log_list)} lines \n"
                )
                for log in reversed(log_list):
                    utc_time = _epoch_to_time_str(log[0])
                    cur_line = safe_load_json(log[1])
                    if without_timestamp:
                        f.write(f"{cur_line}\n")
                    else:
                        f.write(f"{utc_time}｜{cur_line}\n")
            console.print(
                f"Time range: UTC|{first_utc_time} → "
                f"UTC|{last_utc_time} | total {len(log_list)} lines \n"
            )
            console.print(
                f"\n[bold green]Successfully saved the log to:[/bold green] {path}\n"
            )
            sys.exit(0)
        else:
            for log in reversed(log_list):
                utc_time = _epoch_to_time_str(log[0])
                cur_line = safe_load_json(log[1])
                if not without_timestamp:
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
