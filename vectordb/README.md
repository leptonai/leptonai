# Vector Database

Our vector db is implemented on top of the [hnsqlite](https://github.com/jiggy-ai/hnsqlite) which is a text-centric integration of SQLite and [Hnswlib](https://github.com/nmslib/hnswlib) to provide a persistent collection of embeddings (strings, vectors, and metadata) and search time filtering based on the metadata.

## Features

The Vector DB client can communicate with the database backend in two modes: in-memory and remote connection.

- **in-memory**: The client runs the vector DB in the same process, providing users with a faster way to conduct experiments.
- **remote**: The client establishes a connection to a separate DB server, which can be run either locally or remotely.

## Terminologies

Our vectordb client creates a `collection` which is self-contained embedding group. It is similar to pinecone's [index][https://docs.pinecone.io/docs/indexes]

## Dependencies

- leptonai
- `lep` command-line interface (see [install lep](TODO))
- [hnsqlite](https://github.com/bddppq/hnsqlite)
- python3
- pip

## Prerequesites

Make sure that you have downloaded the Lepton repository locally. In this guide, we will refer to the path `lepton` as the project's root directory.

## Installation

You can install the `vectordb` via pip:

```bash
# download lepton repo locally
$ cd lepton/
$ pip install -r ./vectordb/vectordb/db/requirements.txt 
$ pip install ./vectordb/vectordb
```

## Getting Started

### Create the in-memory client

```python
from vectordb.client.client import Client
import logging
import numpy as np

# in-memory mode when connection information is not provided.
cli = Client()
dim = 32
try:
    cli.delete_collection("demo")
except Exception as e:
    logging.warning(e)
collection = cli.create_collection("demo", dim=dim)
```

### Create remote client

#### Create the local vectordb server

You can create the a local `vectordb` server as a photon:

```bash
# Download the lepton repo locally
$ cd lepton
# Install the lepton CLI
$ pip install sdk/
# Create vectordb photon
$ lep photon create -n vec-db -m py:./vectordb/vectordb/db/vecdb.py:VecDB
# Start the vectordb server
$ lep photon run -n vec-db
...
2023-07-05 18:16:59,596 - INFO:  If you are using standard photon, a few urls that may be helpful:
2023-07-05 18:16:59,596 - INFO:         - http://0.0.0.0:8080/docs OpenAPI documentation
2023-07-05 18:16:59,596 - INFO:         - http://0.0.0.0:8080/redoc Redoc documentation
2023-07-05 18:16:59,596 - INFO:         - http://0.0.0.0:8080/openapi.json Raw OpenAPI schema
2023-07-05 18:16:59,597 - INFO:         - http://0.0.0.0:8080/metrics Prometheus metrics
2023-07-05 18:16:59,633 - INFO:     Started server process [134955]
2023-07-05 18:16:59,635 - INFO:     Waiting for application startup.
2023-07-05 18:16:59,638 - INFO:     Application startup complete.
2023-07-05 18:16:59,639 - INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
```

You can test the server via the following

```bash
curl -X 'POST' \
  'http://localhost:8080/list_collections' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{}'
```

#### Create the remote connection

```python
from vectordb.client import Client
from vectordb.client import Config

import logging
import random

cli = Client(Config(url="http://0.0.0.0:8080", token=""))
dim = 32
try:
    cli.delete_collection("demo")
except Exception as e:
    logging.warning(e)
collection = cli.create_collection("demo", dim=dim)
```

### Simple vectordb operations

```python
for i in range(100):
    md = [{"i": "val"}]
    emb = np.random.rand(dim)
    collection.insert(keys=[f"doc-id-{i}"], embeddings=[emb], metadatas=md)

emb = np.random.rand(dim)
resp = collection.search(embedding=emb, top_k=3)
for result in resp.results:
    # do something
    result.key
    result.embedding
    result.metadata
    result.distance
```

## APIs Reference

TODO(fanminshi)