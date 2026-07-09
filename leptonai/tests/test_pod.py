import unittest
import warnings

from leptonai.api.v2.pod import PodAPI
from leptonai.api.v2.types.deployment import (
    ContainerPort,
    LeptonContainer,
    LeptonDeploymentUserSpec,
)


class TestSanityCheckPodSpec(unittest.TestCase):
    def setUp(self):
        # _sanity_check_pod_spec does not touch the API client, so we can build a
        # bare PodAPI instance without a workspace connection.
        self.api = PodAPI.__new__(PodAPI)

    def test_container_command_is_preserved(self):
        # The pod sanity check used to unconditionally strip the container
        # command (a guard from 2024 when the backend ignored pod commands).
        # The backend now honors a user-provided command, so the guard must
        # not drop it -- otherwise a dev pod always falls back to the backend
        # default ["sleep", "infinity"] no matter what the user requested.
        command = ["/bin/bash", "-c", "echo DATADOG_POD_MARKER && sleep 120"]
        spec = LeptonDeploymentUserSpec(
            is_pod=True,
            container=LeptonContainer(image="ubuntu", command=list(command)),
        )

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            checked = self.api._sanity_check_pod_spec(spec)

        self.assertIsNotNone(checked)
        self.assertEqual(checked.container.command, command)

    def test_container_ports_are_preserved(self):
        # Pods support container port exposure (hostmap/proxy strategies) since
        # the container port exposure strategy feature, so the sanity check must
        # not strip ports from the spec.
        ports = [ContainerPort(container_port=8080)]
        spec = LeptonDeploymentUserSpec(
            is_pod=True,
            container=LeptonContainer(
                image="ubuntu",
                command=["/bin/bash", "-c", "sleep 1"],
                ports=list(ports),
            ),
        )

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            checked = self.api._sanity_check_pod_spec(spec)

        self.assertEqual(checked.container.ports, ports)
        self.assertEqual(checked.container.command, ["/bin/bash", "-c", "sleep 1"])


if __name__ == "__main__":
    unittest.main()
