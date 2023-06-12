import shutil
import subprocess
import random
import os
import string
import sys
import json

from rich.console import Console

console = Console(highlight=False)


def is_command_installed(command: str):
    try:
        # Run the 'command version' command and capture the output
        output = subprocess.check_output([command, '--version'], stderr=subprocess.STDOUT)
        # Convert bytes to string and remove leading/trailing whitespace
        output = output.decode('utf-8').strip()

        # Check if the output contains 'command' to verify it's installed
        if command in output.lower():
            return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return False


def run_terraform_apply(dir: str, name: str):
    os.makedirs(dir)

    # TODO: silent the output
    git_clone = subprocess.Popen(['git', 'clone', 'git@github.com:leptonai/lepton.git'], cwd=dir, stdin=sys.stdin, text=True, stdout=sys.stdout, stderr=sys.stderr)
    git_clone.communicate()
    git_clone = subprocess.Popen(['git', 'clone', 'git@github.com:leptonai/infra-ops.git'], cwd=dir, stdin=sys.stdin, text=True, stdout=sys.stdout, stderr=sys.stderr)
    git_clone.communicate()
    console.print(f'Cloned the installation repo to {dir}')

    chart_dir = dir / 'lepton/charts'
    t_dir = dir / 'infra-ops/terraform/eks-lepton'
    shutil.copytree(chart_dir, t_dir / 'charts')

    console.print(f'Initizaling the installer (Terraform) in {dir}... Taking a few minutes...')
    terraform_init = subprocess.Popen(['terraform', 'init'], cwd=t_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if terraform_init.wait() != 0:
        stderr_output, stdout_output = terraform_init.communicate()
        console.print('Failed to initialize terraform')
        console.print("Stderr output:\n", stderr_output.decode())
        console.print("Stdout output:\n", stdout_output.decode())
        return False, ""
    console.print('Initialized the installer (Terraform)')

    terraform_apply = subprocess.Popen(['terraform', 'apply', '-auto-approve', f'-var=cluster_name={name}'], cwd=t_dir, stdin=sys.stdin, text=True, stdout=sys.stdout, stderr=sys.stderr)
    # TODO: silent the output
    terraform_apply.communicate()
    if terraform_apply.returncode != 0:
        console.print(f'Failed to create cluster {name} with terraform')
        return False, ""

    terraform_output = subprocess.Popen(['terraform', 'output', '-json'], cwd=t_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout_output, _ = terraform_output.communicate()
    stdout_output_json = json.loads(stdout_output.decode())
    ingress_hostname = stdout_output_json['lepton_ingress_hostname']['value']

    console.print('Finished installation')

    return True, ingress_hostname


def run_terraform_destroy(dir: str, name: str):
    t_dir = dir + '/infra-ops/terraform/eks-lepton'

    console.print(f'Removing the cluster in {dir}... Taking a few minutes...')
    terraform_destroy = subprocess.Popen(['terraform', 'destroy', '-auto-approve', f'-var=cluster_name={name}'], cwd=t_dir, stdin=sys.stdin, text=True, stdout=sys.stdout, stderr=sys.stderr)
    # TODO: silent the output
    terraform_destroy.communicate()
    if terraform_destroy.returncode != 0:
        console.print(f'Failed to remove cluster {name} with terraform')
        return False
    console.print('Removed the cluster')

    return True


def generate_random_string(length):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))
