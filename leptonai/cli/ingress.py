import json
import sys

import click
from datetime import datetime
from rich.table import Table
from .util import console, click_group
from leptonai.api.v2.client import APIClient
from ..api.v1.types.common import Metadata
from ..api.v1.types.ingress import (
    LeptonIngress,
    LeptonIngressUserSpec,
    LeptonIngressEndpoint,
)


@click_group()
def ingress():
    """
    Manage ingress on the DGX Cloud Lepton.
    """
    pass


@ingress.command(name="list")
def list_all():
    """
    List all ingress
    """
    client = APIClient()
    ingress_list = client.ingress.list_all()
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Name")
    table.add_column("Created At")
    table.add_column("Domain Name")
    table.add_column("Status")
    for ingress in ingress_list:
        created_time = datetime.fromtimestamp(
            ingress.metadata.created_at / 1000
        ).strftime("%Y-%m-%d\n%H:%M:%S")

        table.add_row(
            ingress.metadata.name,
            created_time,
            ingress.spec.domain_name,
            ingress.status.message,
        )
    table.title = "Ingress"
    console.print(table)


@ingress.command()
@click.option(
    "--domain-name", "-d", help="domain-name of the ingress", type=str, required=True
)
def create(domain_name):
    """
    Create an ingress
    """
    client = APIClient()
    lepton_ingress = LeptonIngress(
        metadata=Metadata(),
        spec=LeptonIngressUserSpec(domain_name=domain_name),
    )
    client.ingress.create(lepton_ingress)
    console.print(f"Ingress successfully created for [green]{domain_name}[/]:")


@ingress.command()
@click.option("--name", "-n", help="name of the ingress", type=str, required=True)
def get(name):
    """
    Get a ingress by name and print it in json
    """
    client = APIClient()
    ingress = client.ingress.get(name)
    console.print(f"Ingress details for [green]{name}[/]:")
    console.print(json.dumps(client.ingress.safe_json(ingress), indent=2))


@ingress.command()
@click.option("--name", "-n", help="name of the ingress", type=str, required=True)
def delete(name):
    """
    Delete a ingress by name
    """
    client = APIClient()
    client.ingress.delete(name)
    console.print(f"Ingress [green]{name}[/] deleted successfully.")


@ingress.command(name="add-endpoint")
@click.option("--name", "-n", help="name of the ingress", type=str, required=True)
@click.option(
    "--endpoint",
    "-e",
    "deployment",  # internal parameter name (matches API field)
    help="endpoint name to add to the ingress",
    type=str,
    required=True,
)
@click.option(
    "--weight",
    "-w",
    help="traffic weight for this endpoint (default: 100)",
    type=int,
    default=100,
)
def add_endpoint(name, deployment, weight):
    """
    Add an endpoint to an ingress with a specified traffic weight.

    This is useful for canary deployments where you want to route a portion of
    traffic to a new endpoint. Weights are relative - if you have two endpoints
    with weights 80 and 20, they'll receive 80% and 20% of traffic respectively.

    Example:
        # Add a new endpoint with 20% traffic weight
        lep ingress add-endpoint -n my-ingress --endpoint new-endpoint -w 20
        # or: lep ingress add-endpoint -n my-ingress -e new-endpoint -w 20
    """
    client = APIClient()

    # Get current ingress
    current_ingress = client.ingress.get(name)

    # Check if deployment already exists in endpoints
    if current_ingress.spec.endpoints:
        for endpoint in current_ingress.spec.endpoints:
            if endpoint.deployment == deployment:
                console.print(
                    f"[yellow]Warning[/]: Endpoint [cyan]{deployment}[/] already"
                    f" exists in ingress [cyan]{name}[/].\nUse 'lep ingress"
                    " update-endpoint' to change its weight."
                )
                return

    # Create new endpoint
    new_endpoint = LeptonIngressEndpoint(deployment=deployment, weight=weight)

    # Add to existing endpoints or create new list
    if current_ingress.spec.endpoints:
        current_ingress.spec.endpoints.append(new_endpoint)
    else:
        current_ingress.spec.endpoints = [new_endpoint]

    # Update ingress
    client.ingress.update(name, current_ingress)

    console.print(
        f"✓ Successfully added endpoint [green]{deployment}[/] to ingress"
        f" [green]{name}[/] with weight [green]{weight}[/]"
    )

    # Show current traffic distribution
    _show_traffic_distribution(current_ingress.spec.endpoints)


@ingress.command(name="remove-endpoint")
@click.option("--name", "-n", help="name of the ingress", type=str, required=True)
@click.option(
    "--endpoint",
    "-e",
    "deployment",  # internal parameter name (matches API field)
    help="endpoint name to remove from the ingress",
    type=str,
    required=True,
)
def remove_endpoint(name, deployment):
    """
    Remove an endpoint from an ingress.

    Example:
        lep ingress remove-endpoint -n my-ingress --endpoint old-endpoint
        # or: lep ingress remove-endpoint -n my-ingress -e old-endpoint
    """
    client = APIClient()

    # Get current ingress to check if endpoint exists
    current_ingress = client.ingress.get(name)

    if not current_ingress.spec.endpoints:
        console.print(f"[red]Error[/]: Ingress [cyan]{name}[/] has no endpoints.")
        sys.exit(1)

    # Check if deployment exists
    endpoint_exists = any(
        ep.deployment == deployment for ep in current_ingress.spec.endpoints
    )

    if not endpoint_exists:
        console.print(
            f"[red]Error[/]: Endpoint [cyan]{deployment}[/] not found in ingress"
            f" [cyan]{name}[/]."
        )
        sys.exit(1)

    # Use the dedicated delete_endpoint API method
    updated_ingress = client.ingress.delete_endpoint(name, deployment)

    console.print(
        f"✓ Successfully removed endpoint [green]{deployment}[/] from ingress"
        f" [green]{name}[/]"
    )

    # Show current traffic distribution
    if updated_ingress.spec.endpoints:
        _show_traffic_distribution(updated_ingress.spec.endpoints)
    else:
        console.print("[yellow]Note[/]: Ingress now has no endpoints.")


@ingress.command(name="update-endpoint")
@click.option("--name", "-n", help="name of the ingress", type=str, required=True)
@click.option(
    "--endpoint",
    "-e",
    "deployment",  # internal parameter name (matches API field)
    help="endpoint name to update",
    type=str,
    required=True,
)
@click.option(
    "--weight",
    "-w",
    help="new traffic weight for this endpoint",
    type=int,
    required=True,
)
def update_endpoint(name, deployment, weight):
    """
    Update the traffic weight of an existing endpoint in an ingress.

    Example:
        # Change endpoint weight to 50%
        lep ingress update-endpoint -n my-ingress --endpoint my-endpoint -w 50
        # or: lep ingress update-endpoint -n my-ingress -e my-endpoint -w 50
    """
    client = APIClient()

    # Get current ingress
    current_ingress = client.ingress.get(name)

    if not current_ingress.spec.endpoints:
        console.print(
            f"[red]Error[/]: Ingress [cyan]{name}[/] has no endpoints. "
            "Use 'lep ingress add-endpoint' first."
        )
        sys.exit(1)

    # Find and update the endpoint
    found = False
    for endpoint in current_ingress.spec.endpoints:
        if endpoint.deployment == deployment:
            endpoint.weight = weight
            found = True
            break

    if not found:
        console.print(
            f"[red]Error[/]: Endpoint [cyan]{deployment}[/] not found in ingress"
            f" [cyan]{name}[/].\nUse 'lep ingress add-endpoint' to add it first."
        )
        sys.exit(1)

    # Update ingress
    client.ingress.update(name, current_ingress)

    console.print(
        f"✓ Successfully updated weight for endpoint [green]{deployment}[/] in"
        f" ingress [green]{name}[/] to [green]{weight}[/]"
    )

    # Show current traffic distribution
    _show_traffic_distribution(current_ingress.spec.endpoints)


@ingress.command(name="set-endpoints")
@click.option("--name", "-n", help="name of the ingress", type=str, required=True)
@click.option(
    "--endpoints",
    "-e",
    help=(
        "endpoint configurations in format 'endpoint:weight' (can be specified"
        " multiple times). This replaces all existing endpoints."
    ),
    type=str,
    multiple=True,
    required=True,
)
def set_endpoints(name, endpoints):
    """
    Set all endpoints for an ingress at once, REPLACING any existing endpoints.

    ⚠️  WARNING: This command is DESTRUCTIVE - it replaces the entire endpoint list.
    Any endpoints not specified in this command will be REMOVED from the ingress.

    Use add-endpoint or update-endpoint for incremental changes.

    Examples:
        # Set up 80/20 canary split (any other endpoints will be removed!)
        lep ingress set-endpoints -n my-ingress -e stable-endpoint:80 -e canary-endpoint:20

        # Switch to 50/50 split (must specify both endpoints)
        lep ingress set-endpoints -n my-ingress -e stable-endpoint:50 -e canary-endpoint:50

        # Route 100% traffic to one endpoint (removes all others)
        lep ingress set-endpoints -n my-ingress -e new-endpoint:100
    """
    client = APIClient()

    # Parse endpoint specifications
    new_endpoints = []
    for endpoint_spec in endpoints:
        try:
            deployment, weight_str = endpoint_spec.split(":")
            weight = int(weight_str)
            if weight < 0:
                console.print(
                    f"[red]Error[/]: Weight must be non-negative, got {weight} for"
                    f" endpoint {deployment}"
                )
                sys.exit(1)
            new_endpoints.append(
                LeptonIngressEndpoint(deployment=deployment.strip(), weight=weight)
            )
        except ValueError:
            console.print(
                f"[red]Error[/]: Invalid endpoint specification '{endpoint_spec}'. "
                "Expected format: 'endpoint:weight'"
            )
            sys.exit(1)

    if not new_endpoints:
        console.print("[red]Error[/]: At least one endpoint must be specified.")
        sys.exit(1)

    # Validate that sum of weights is greater than zero
    total_weight = sum(ep.weight for ep in new_endpoints)
    if total_weight == 0:
        console.print(
            "[red]Error[/]: Sum of endpoint weights must be greater than zero. "
            "At least one endpoint must have a positive weight."
        )
        sys.exit(1)

    # Get current ingress
    current_ingress = client.ingress.get(name)

    # Replace endpoints
    current_ingress.spec.endpoints = new_endpoints

    # Update ingress
    client.ingress.update(name, current_ingress)

    console.print(f"✓ Successfully updated endpoints for ingress [green]{name}[/]")

    # Show current traffic distribution
    _show_traffic_distribution(new_endpoints)


def _show_traffic_distribution(endpoints):
    """
    Display a table showing the traffic distribution across endpoints.
    """
    if not endpoints:
        return

    total_weight = sum(ep.weight or 0 for ep in endpoints)

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Endpoint")
    table.add_column("Weight")
    table.add_column("Traffic %")

    for endpoint in endpoints:
        weight = endpoint.weight or 0
        percentage = (weight / total_weight * 100) if total_weight > 0 else 0
        table.add_row(
            endpoint.deployment,
            str(weight),
            f"{percentage:.1f}%",
        )

    table.title = "Traffic Distribution"
    console.print(table)


def add_command(cli_group):
    cli_group.add_command(ingress)
