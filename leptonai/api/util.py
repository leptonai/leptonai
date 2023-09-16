"""
Utility functions for the Lepton AI API.
"""
import json
import requests
from typing import Dict, List, Optional, Union


class APIError(object):
    """
    An error class for API calls that return status other than 200.
    """

    def __init__(self, response: requests.Response, message: Optional[str] = None):
        self.status_code = response.status_code
        self.message = message if message else response.text

    def __str__(self) -> str:
        return f"APIError (API response code {self.status_code}): {self.message}"


def json_or_error(
    response: requests.Response, additional_debug_info: str = ""
) -> Union[Dict, List, APIError]:
    """
    A utility function to return json if the response is ok, and otherwise returns an APIError object
    that details the error encountered.

    This function is intended to be used to wrap raw api functions and parse the response, which should
    contain a json response if the response is ok.

    :param requests.Response response: the response to parse
    :return: the json content of the response if the response is ok, otherwise an APIError or NotJsonError
    """
    if response.ok:
        try:
            return response.json()
        except json.JSONDecodeError:
            # This should not happen: apis that use json_or_error should make sure
            # that the response is json. If this happens, it is either a programming
            # error, or the api has changed, or the lepton ai cloud side has a bug.
            return APIError(
                response,
                message=(
                    "You encountered a programming error. Please report this, and"
                    " include the following debug info:\n*** begin of debug info"
                    f" ***\n{additional_debug_info}\nresponse returned 200 OK, but the"
                    " content cannot be decoded as json.\nresponse.text:"
                    f" {response.text}\n\n*** end of debug info ***"
                ),
            )
    else:
        return APIError(response)


def create_header(auth_token: Optional[str]) -> Dict[str, str]:
    """
    Generate HTTP header for a request given an auth token.

    :param str auth_token: auth token to use in the header. None if the request does not require an auth token.
    :return: the generated HTTP header
    :rtype: dict[str, str]
    """
    return {"Authorization": "Bearer " + auth_token} if auth_token else {}
