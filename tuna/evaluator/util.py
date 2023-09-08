import json
from typing import List
import socket
from rich.console import Console
from rich.table import Table
import requests
import rich
from rich.tree import Tree


def ask_for_numbers(question):
    while True:
        response = input(question).strip()
        try:
            numbers = list(map(int, response.split(",")))
            return numbers
        except ValueError:
            rich.print(
                "[bold red]Invalid input. Please enter numbers separated by"
                " commas.[/bold red]"
            )


def ask_yes_no(question):
    while True:
        response = input(question + " (y/n): ").lower().strip()
        if response in ("y", "yes"):
            return True
        elif response in ("n", "no"):
            return False
        else:
            rich.print("Invalid input. Please answer with 'y' or 'n'.")


def show_tree(title, nodes):
    colors = ["cyan", "magenta", "green", "yellow", "blue", "red"]
    # Create a tree instance
    tree = Tree(f"[bold blue]{title}[/bold blue]")

    def node_add(node, str_val, depth):
        color = colors[depth % len(colors)]
        return node.add(f"[bold {color}]{str_val}[/bold {color}]")

    def add_nodes(node, sub_nodes, depth=1):
        if isinstance(sub_nodes, str):
            return node_add(node, sub_nodes, depth)
        elif isinstance(sub_nodes, list):
            for sn in sub_nodes:
                add_nodes(node, sn, depth)
        elif isinstance(sub_nodes, dict):
            for k in sub_nodes:
                new_node = add_nodes(node, k)
                add_nodes(new_node, sub_nodes=list(sub_nodes[k]), depth=depth + 1)

    add_nodes(tree, nodes, depth=1)
    # Display the tree
    rich.print(tree)


def add_http_if_not_exist(url):
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "http://" + url
    return url


def request_model_list(base, key):
    headers = {
        "Authorization": f"Bearer {key}",
    }

    response = requests.get(f"{base}/v1/models", headers=headers)
    return response.json()["data"]


def request_chat_completion(messages, model, base, key, kwargs={}):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
    }

    data = {"model": model, "messages": messages, **kwargs}

    response = requests.post(
        f"{base}/v1/chat/completions", headers=headers, data=json.dumps(data)
    )
    return response.json().get("choices", [])[0].get("message", {})


def show_bar_chart(data, title=""):
    console = Console()

    console.print(f"{title}\n")

    max_value = max(data.values())
    increment = max_value / 25  # Adjust to fit the width of your terminal
    max_key_length = max(len(key) for key in data.keys())

    for key, value in data.items():
        bar = "█" * int(value / increment)  # Using block element as a bar
        console.print(f"{key.rjust(max_key_length)}: {bar} {value}")


def show_table(columns, rows, kwargs=None):
    if kwargs is None:
        kwargs = [{} for x in columns]
    console = Console()
    table = Table(show_header=True, header_style="bold magenta")
    for i in range(len(columns)):
        column = columns[i]
        table.add_column(column, **kwargs[i])

    for row in rows:
        table.add_row(*row)
    console.print(table)


def read_json_file(file_path):
    with open(file_path, "r") as file:
        json_data = json.load(file)
    return json_data


def write_json_file(data, file_path):
    with open(file_path, "w") as json_file:
        json.dump(data, json_file, indent=4)


def find_available_port(start_port):
    max_port = 65535  # Maximum port number
    for port in range(start_port, max_port + 1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("localhost", port))
                return port
        except OSError:
            continue

    raise RuntimeError("No available ports found in the specified range.")


def validate_input_dataset(dataset):
    if not isinstance(dataset, list):
        raise ValueError(f"dataset should be of type `list`, but got {type(dataset)}")
    for item in dataset:
        if not isinstance(item, dict):
            raise ValueError(
                f"data sample should be of type `dict`, but got {type(item)}"
            )
        if item.get("messages", None) is None or (
            not isinstance(item.get("messages"), List)
        ):
            raise ValueError("data sample got no `messages`")
        roles = set([x["role"] for x in item["messages"]]) - set(
            ["user", "assistant", "system"]
        )
        if len(roles) != 0:
            raise ValueError(
                "Only `user`, `assistant`, `system` is allowed for `role`, but god"
                f" {roles}"
            )
    return True
