# flake8: noqa
"""
This implements the api for the Lepton AI library. It provides an easy wrapper
around the Lepton AI web API. Note that, the Lepton AI web API is intended to be
used by "human interactions", and not programmatical interactions. This means
that there is no SLA guarantee for the api, especially if you plan to use it in
a high frequency manner. If you need to use the Lepton AI web API in a
programmatical way, please let us know and discuss options.

In general, the api is organized into several modules, each of which corresponds
to a specific functionality of the Lepton AI web API. For example, the
:mod:`leptonai.api.v1.deployment` module contains functions that interact with the
Lepton AI web API to manage deployments.

Lepton AI web APIs usually return two types of responses:
- For web apis that return contents, such as listing photons and deployments,
  the response is json if successful, and an error message if unsuccessful. The
  python api then converts it to: a json object if successful, and an APIError
  object if the response is not successful.
- For apis that does not return contents but use HTTP status codes to indicate
  success or failure, such as pushing a photon or removing a deployment, the
  python api simply returns the response itself.
"""

from . import v0
from . import v1
