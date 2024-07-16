import os
from typing import Type, Union, Dict, List
import warnings

try:
    import ray
except ImportError as e:
    raise RuntimeError(
        "Please install ray before running ray integrations. Lepton Ray integration did"
        " not find ray installed."
    )

from ray.runtime_env import RuntimeEnv

from leptonai.photon import Photon


def get_runtime_env(photon_or_class: Union[Photon, Type[Photon]]) -> RuntimeEnv:
    """
    Get the runtime environment for a photon class, or a Photon object.

    Note that not all runtime environments are supported. Currently, we only support
    pip dependencies, environment variables, and secrets.
    """
    # deals with pip dependencies
    if isinstance(photon_or_class, Photon):
        pip: List[str] = photon_or_class._requirement_dependency
    elif issubclass(photon_or_class, Photon):
        # enumerate bases
        bases = reversed(list(photon_or_class._iter_ancestors()))
        pip: List[str] = sum([base.requirement_dependency or [] for base in bases], [])
    else:
        raise ValueError(
            "photon_or_class must be a Photon object or a subclass of Photon."
        )

    # deals with environment variables
    deployment_template = photon_or_class.deployment_template
    deployment_env: Dict[str, str] = deployment_template.get("env", {})
    deployment_secret: List[str] = deployment_template.get("secret", [])
    env_vars: Dict[str, str] = {}
    for k, v in deployment_env:
        # Set the env vars by giving priority to the current env vars in os.environ.
        env_vars[k] = os.environ.get(k, v)
    for s in deployment_secret:
        # Set the env vars by giving priority to the current env vars in os.environ.
        if s in os.environ:
            env_vars[s] = os.environ[s]
    return RuntimeEnv(pip=pip, env_vars=env_vars)


def ray_remote(photon_class, **kwargs):
    """
    Function to make an already defined photon class a ray remote object. Assuming
    that we have a photon class MyPhoton, then ray_remote(MyPhoton) will return a
    ray remote object of MyPhoton. This is equivalent to ray.remote(MyPhoton), but if the runtime_env is not provided, then ray_remote will automatically add the runtime_env to the kwargs.
    """
    if not issubclass(photon_class, Photon):
        raise TypeError("photon_class must be a subclass of Photon.")
    if "runtime_env" not in kwargs:
        # Add the Photon's runtime env setups to kwarts.
        kwargs["runtime_env"] = get_runtime_env(photon_class)
    else:
        warnings.warn(
            "Photon's runtime env is overwritten by the provided runtime env."
        )
    return ray.remote(**kwargs)(photon_class)
