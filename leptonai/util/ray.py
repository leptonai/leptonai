try:
    import ray
except ImportError as e:
    raise RuntimeError("Please install ray before running ray integrations. Lepton Ray integration did not find ray installed.")

from leptonai.photon import Photon


def ray_remote(photon_class, **kwargs):
    """
    Function to make an already defined photon class a ray remote object.
    """
    if not issubclass(photon_class, Photon):
        raise TypeError("photon_class must be a subclass of Photon.")
    # Add the photon's requirement_dependency to ray remote's runtime env.
    if photon_class._requirement_dependency:
        if "runtime_env" not in kwargs:
            kwargs["runtime_env"] = {"pip": []}
        kwargs["runtime_env"]["pip"].extend(photon_class._requirement_dependency)
    return ray.remote(**kwargs)(photon_class)


