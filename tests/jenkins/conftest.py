import pytest

import jam.libs.jenkins
import tests.helpers.helpers_jenkins


class ApiCallTestImplementation(jam.libs.jenkins.ApiCallMixin):
    def __init__(self, base_url, auth, crumb_url):
        self.api_settings = self.ApiCallSettings(base_url=base_url, auth=auth, crumb_url=crumb_url)

    __call__ = jam.libs.jenkins.ApiCallMixin.api_call


@pytest.fixture
def base_url():
    return tests.helpers.helpers_jenkins.get_base_url()


@pytest.fixture
def auth():
    return 'user', 'pass'


@pytest.fixture
def crumb_url():
    return tests.helpers.helpers_jenkins.get_crumb_url()


@pytest.fixture
def api_call(base_url, auth, crumb_url):
    return ApiCallTestImplementation(base_url=base_url, auth=auth, crumb_url=crumb_url)


@pytest.fixture
def jenkins(base_url, auth):
    return jam.libs.jenkins.Jenkins(url=base_url, username=auth[0], api_token=auth[1])


@pytest.fixture
def jenkins_agent(base_url, auth, crumb_url):
    return jam.libs.jenkins.JenkinsAgent(url=base_url, name='build1', auth=auth, crumb_url=crumb_url)
