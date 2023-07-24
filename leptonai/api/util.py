"""
Utility functions for the Lepton AI API.
"""
import json
import requests
from typing import Dict, Optional, Union


class APIError(object):
    """
    An error class for API calls that return status other than 200.
    """

    def __init__(self, response):
        self.status_code = response.status_code
        self.message = response.text

    def __str__(self):
        return f"APIError {self.status_code}: {self.message}"


def json_or_error(response: requests.Response) -> Union[Dict, APIError]:
    """
    A utility function to return json if the response is ok, and otherwise return two types of errors: APIError if the response is not ok and the content is json, and NotJsonError if the response is ok but the content cannot be decoded as json.

    This function is intended to be used to wrap raw api functions to parse the response.

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
            raise RuntimeError(
                "You encountered a programming error. Please report this."
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
