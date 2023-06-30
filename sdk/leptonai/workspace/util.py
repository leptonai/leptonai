import subprocess
import random
import string

from rich.console import Console

console = Console(highlight=False)


def is_command_installed(command: str):
    try:
        # Run the 'command version' command and capture the output
        output = subprocess.check_output(
            [command, "--version"], stderr=subprocess.STDOUT
        )
        # Convert bytes to string and remove leading/trailing whitespace
        output = output.decode("utf-8").strip()

        # Check if the output contains 'command' to verify it's installed
        if command in output.lower():
            return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return False


def generate_random_string(length):
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(length))
