# flake8: noqa
"""
General utilities for LeptonAI
"""

from .util import (
    create_cached_dir_if_needed,
    switch_cwd,
    check_photon_name,
    patch,
    asyncfy,
    asyncfy_with_semaphore,
    _is_local_url,
    _is_valid_url,
    is_valid_url,
    find_available_port,
)

# Note: we do not import the S3Cache here because it depends on boto3, which is
# not a dependency of the SDK. If you want to use the S3Cache, you need to
# install boto3 yourself and explicitly import it.
# from .s3cache import S3Cache
