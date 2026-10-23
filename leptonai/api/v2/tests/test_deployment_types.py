# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
from pydantic import ValidationError

from leptonai.api.v2.types.deployment import LeptonDeploymentUserSpec


@pytest.mark.parametrize("timeout", [None, 300, 600, 3600])
def test_deployment_accepts_valid_or_unset_ingress_timeout(timeout):
    spec = LeptonDeploymentUserSpec(ingress_timeout_seconds=timeout)

    assert spec.ingress_timeout_seconds == timeout


@pytest.mark.parametrize("timeout", [299, 3601, 6000])
def test_deployment_rejects_ingress_timeout_outside_server_range(timeout):
    with pytest.raises(ValidationError, match="between 300 and 3600 seconds"):
        LeptonDeploymentUserSpec(ingress_timeout_seconds=timeout)
