# flake8: noqa
"""
This implements the CLI for the Lepton AI library. When you install the library,
you get a command line tool called `lep` that you can use to create and manage
deployments, jobs, pods, and other resources on the DGX Cloud Lepton.
"""

# Guard so that leptonai.api never depends on things under leptonai.cli.
import leptonai.api as _

from .cli import lep
