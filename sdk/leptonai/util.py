from contextlib import contextmanager
import json
import os

from rich.console import Console


console = Console(highlight=False)


def check_and_print_http_error(response):
    if response.status_code >= 200 and response.status_code <= 299:
        return False
    try:
        error_data = response.json()
        error_message = error_data.get("message")
        console.print(f"Error: {error_message}")
    except json.JSONDecodeError:
        console.print(f"Error Code: {response.status_code}")
        console.print(f"Error: {response.text}")

    return True


@contextmanager
def switch_cwd(path):
    old_cwd = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(old_cwd)
