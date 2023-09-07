# flake8: noqa
"""
Cloudrun functionality for LeptonAI

The cloudrun functionality allows you to create deployments (services) in a more
interactive way. It is a thin wrapper around the LeptonAI API.

While conventional use of LeptonAI involves creating a photon, and then pushing
and running it, the inline API allows you to create a photon and run it in
the same process as the main local python program. You can use this to run remote
deployments, and directly call them as if you are running a local program.
"""

from .remote import Remote, clean
