import json
from typing import List, Dict
from unittest.mock import Mock

import requests


def create_mock_response(data: Dict | List | str, status_code: int) -> requests.Response:
    """
    Creates a mock response object with the given data and status code.
    Strings are returned as-is, while dictionaries and lists are converted to JSON.
    Non-2xx responses are configured to raise an HTTPError when
    raise_for_status is called.

    :param data: Data to return in the response.
    :param status_code: Status code to return.
    :return: Mock response object.
    """
    mock_response = Mock()
    mock_response.status_code = status_code

    _set_mock_response_body(data, mock_response)

    if status_code >= 400:
        mock_response.raise_for_status.side_effect = requests.HTTPError()
        mock_response.raise_for_status.side_effect.response = mock_response

    return mock_response


def _set_mock_response_body(data: dict | list | str, mock_response: Mock):
    if isinstance(data, str):
        mock_response.text = data
    else:
        mock_response.text = json.dumps(data)
        mock_response.json.return_value = data

    mock_response.iter_lines.return_value = str(mock_response.text).split("\n")
