# Lepton Workloads

Lepton (NVIDIA DGX Cloud Lepton) is a multi-tenant AI cloud platform. Users in
a workspace create **workloads** to consume GPU/CPU capacity. This document
lists the workload types and what each one is for.

## Endpoints

Long-running model inference services exposed at a stable URL. An endpoint
serves traffic, autoscales replicas based on demand (QPM or GPU utilization),
and can scale to zero when idle. The served model can come from an NVIDIA NIM
container, a vLLM or SGLang engine, or an arbitrary container image.

Use an endpoint whenever something needs to serve requests — a chat model,
an embedding service, a custom inference backend.

## Dynamo Endpoints

A specialized endpoint shape where serving is split across multiple services
in a graph — typically separate frontend, prefill, and decode services. Each
service has its own resource shape, image, and replica count, and is scaled
independently. Supported backend frameworks are sglang, vllm, and trtllm.

Use Dynamo when disaggregated serving is needed for better throughput or
latency on large LLMs.

## Dev Pods

Single-replica, long-lived interactive environments. A Dev Pod is a personal
machine — users ssh in, open Jupyter, or attach an IDE. It runs until
explicitly stopped or deleted, does not fan out across replicas, and is not
intended to receive external production traffic.

Use a Dev Pod for day-to-day development, data exploration, debugging, and
notebook work.

## Batch Jobs

Finite workloads that run to completion. A job can fan out into many parallel
pods that communicate with each other (configurable parallelism and
completions count). Jobs support retries, scheduling priority and preemption,
reservation binding, delayed start, TTL-after-finish, and per-attempt history.

Use a Batch Job for training runs, evaluations, hyperparameter sweeps, data
processing, or any work with a defined end state. Built-in templates exist
for `torchrun` (multi-GPU PyTorch) and MPI (multi-node) patterns.

## Ray Clusters

A managed Ray cluster — one head plus one or more worker groups, each with
its own resource shape and min/max replica count. The cluster can autoscale
its worker groups based on demand and can be suspended (paused without
deletion) to release capacity. Users submit Ray jobs and inspect Ray actors
against the running cluster.

Use a Ray Cluster for distributed Python workloads — RLHF, large-scale data
processing, ML pipelines built on Ray's actor model.

## Slurm Clusters

A managed Slurm cluster — controller plus login nodes. Lepton provisions and
operates the cluster; users use Slurm normally (ssh to a login node, submit
jobs via `sbatch` / `srun`). Slurm jobs are not independently managed Lepton
resources — they live inside the cluster and are surfaced as a queryable list.

Slurm clusters are **not self-serve** — they are provisioned on request by the
Lepton team. Use them for teams already on Slurm workflows or doing classic
HPC work.

## Fine-Tuning Jobs

A specialized job flavor for model fine-tuning, configured by picking a base
model, a dataset, and a recipe (LoRA, full SFT, etc.) rather than by writing
a job spec from scratch. Internally it shares the Batch Job machinery but
with a guided configuration path and a recipe-aware view of the run.

Use a Fine-Tuning Job to tune a model without authoring a custom training
spec. For workflows that need full control over the training entrypoint, use
a Batch Job instead.

## Quick comparison

| Workload    | Lifetime                   | Replica model              | Self-serve       | Primary purpose                |
|-------------|----------------------------|----------------------------|------------------|--------------------------------|
| Endpoint    | long-running               | autoscaled                 | yes              | Serve inference traffic        |
| Dynamo      | long-running               | per-service autoscaled     | yes              | Disaggregated LLM serving      |
| Dev Pod     | long-running (manual stop) | single                     | yes              | Interactive development        |
| Batch Job   | runs to completion         | parallelism × completions  | yes              | Finite training / processing   |
| Ray Cluster | long-running (suspendable) | head + worker groups       | yes              | Distributed Python / Ray       |
| Slurm       | long-running               | controller + login nodes   | **request only** | Slurm / classic HPC            |
| Fine-Tune   | runs to completion         | parallel pods              | yes              | Guided model fine-tuning       |
