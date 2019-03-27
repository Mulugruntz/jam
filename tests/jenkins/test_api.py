import pytest
import requests
import requests_mock

import tests.helpers.helpers_jenkins


def test_crumb_ok(base_url, api_call):
    with requests_mock.mock() as rmock:
        tests.helpers.helpers_jenkins.inject_crumb_issuer(rmock, 200)
        rmock.register_uri('GET', f'{base_url}/some/api', [
            {'json': {}, 'status_code': 200},
        ])
        assert api_call('get', 'some/api').json() == {}


def test_crumb_ko_invalid_auth(api_call):
    with requests_mock.mock() as rmock:
        tests.helpers.helpers_jenkins.inject_crumb_issuer(rmock, 401)
        with pytest.raises(requests.ConnectionError) as err:
            api_call('get', 'some/api')
        assert str(err.value) == "Could not issue Jenkins crumb."


def test_crumb_ko_no_auth(api_call):
    with requests_mock.mock() as rmock:
        tests.helpers.helpers_jenkins.inject_crumb_issuer(rmock, 403)
        with pytest.raises(requests.ConnectionError) as err:
            api_call('get', 'some/api')
        assert str(err.value) == "Could not issue Jenkins crumb."


def test_api_call_no_settings(api_call):
    del api_call.api_settings
    with pytest.raises(AttributeError):
        api_call('get', 'some/api')
