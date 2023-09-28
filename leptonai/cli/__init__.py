# flake8: noqa
"""
This implements the CLI for the Lepton AI library. When you install the library,
you get a command line tool called `lep` that you can use to operate local photon
including creating, managing, and running them, and to interact with the cloud.
"""

# Guard so that leptonai.api never depends on things under leptonai.cli.
import leptonai.api as _

from .cli import lep
