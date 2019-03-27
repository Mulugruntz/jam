import json

import pytest
import requests
import requests_mock

import jam.libs.jenkins
import tests.helpers.helpers_jenkins


def test_jenkins_get_agent(jenkins):
    agent = jenkins.get_agent('build1')
    assert isinstance(agent, jam.libs.jenkins.JenkinsAgent)
    assert agent.name == 'build1'


def test_jenkins_get_jobs_fail(jenkins):
    with requests_mock.mock() as rmock:
        tests.helpers.helpers_jenkins.inject_crumb_issuer(rmock, 403)
        with pytest.raises(requests.ConnectionError):
            _ = jenkins.jobs  # noqa: F841


def test_jenkins_get_jobs_empty_queue_without_jam(jenkins, base_url):
    with requests_mock.mock() as rmock:
        tests.helpers.helpers_jenkins.inject_crumb_issuer(rmock, 200)
        rmock.register_uri('GET', f'{base_url}/queue/api/json', [
            {
                'json': {"_class": "hudson.model.Queue", "discoverableItems": [], "items": []},
                'status_code': 200
            },
        ])
        jobs = jenkins.jobs
        assert len(jobs) == 0


def test_jenkins_get_jobs_empty_queue_with_jam(jenkins, base_url):
    with requests_mock.mock() as rmock:
        tests.helpers.helpers_jenkins.inject_crumb_issuer(rmock, 200)
        rmock.register_uri('GET', f'{base_url}/queue/api/json', [
            {
                'json': json.load(open('tests/http/jenkins.queue.0.json')),
                'status_code': 200
            },
        ])
        jobs = jenkins.jobs
        assert len(jobs) == 0


def test_jenkins_get_jobs_one_item_in_queue(jenkins, base_url):
    with requests_mock.mock() as rmock:
        tests.helpers.helpers_jenkins.inject_crumb_issuer(rmock, 200)
        rmock.register_uri('GET', f'{base_url}/queue/api/json', [
            {
                'json': json.load(open('tests/http/jenkins.queue.1.json')),
                'status_code': 200
            },
        ])
        jobs = jenkins.jobs
        assert len(jobs) == 1
