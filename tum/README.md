TUM - Torch Unified Memory
----

## Installation

Install `torch` first, you will need a relatively new version of torch (>= 2.0) to work with TUM.

`pip install -U torch`

Then install TUM by checking out this repo and do:

`pip install .` or `pip install -e .`

## Usage

```python
import tum
tum.enable()
```
That's it. It works seamlessly with existing torch code.

Note you need to make sure `tum.enable` is called before any cuda
allocations (aka. creating new gpu tensors) happened with torch,
because switching gpu memory allocator after existing one already
initialized is not allowed.

## Advanced usage

TUM uses CUDA Unified Virtual Memory under the hood, which means if there are multiple processes over-subscribing the gpu memory at the same time, CUDA will move around pages between device and host. In order to get best performance, if there are chances that your memory have been evicted to host, and you are about to run workload that are gpu memory (read) intensive, you should hint cuda to prefetch your memory back to device asap:
```python
tum.prefetch()
```
TUM keeps tracks of all allocated (and still live) memory blocks, and `tum.prefetch()` hints cuda to prefetch (all of) them.
