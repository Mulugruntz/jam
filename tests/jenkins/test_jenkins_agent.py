import json

import mock
import pytest
import requests
import requests_mock

import jam.libs.jenkins
import tests.helpers.helpers_jenkins


def test_status_online_idle(jenkins_agent):
    with requests_mock.mock() as rmock:
        tests.helpers.helpers_jenkins.inject_crumb_issuer(rmock, 200)
        rmock.register_uri('GET', '{}/api/json'.format(jenkins_agent.url), [
            {
                'json': json.load(open('tests/http/jenkins.build1.idle.json')),
                'status_code': 200
            },
        ])

        assert all([jenkins_agent.is_idle, jenkins_agent.is_online,
                    not jenkins_agent.is_offline, not jenkins_agent.is_temporarily_offline])

        assert jenkins_agent.offline_cause_reason is None


def test_status_online_busy(jenkins_agent):
    with requests_mock.mock() as rmock:
        tests.helpers.helpers_jenkins.inject_crumb_issuer(rmock, 200)
        rmock.register_uri('GET', '{}/api/json'.format(jenkins_agent.url), [
            {
                'json': json.load(open('tests/http/jenkins.build1.busy.json')),
                'status_code': 200
            },
        ])

        assert all([not jenkins_agent.is_idle, jenkins_agent.is_online,
                    not jenkins_agent.is_offline, not jenkins_agent.is_temporarily_offline])

        assert jenkins_agent.offline_cause_reason is None


def test_status_is_temporarilyoffline(jenkins_agent):
    with requests_mock.mock() as rmock:
        tests.helpers.helpers_jenkins.inject_crumb_issuer(rmock, 200)
        rmock.register_uri('GET', '{}/api/json'.format(jenkins_agent.url), [
            {
                'json': json.load(open('tests/http/jenkins.build1.temporarilyoffline.json')),
                'status_code': 200
            },
        ])

        assert all([jenkins_agent.is_idle, not jenkins_agent.is_online,
                    jenkins_agent.is_offline, jenkins_agent.is_temporarily_offline])

        assert jenkins_agent.offline_cause_reason == 'hudson.slaves.OfflineCause$UserCause || testing purposes'


def test_status_is_offline(jenkins_agent):
    with requests_mock.mock() as rmock:
        tests.helpers.helpers_jenkins.inject_crumb_issuer(rmock, 200)
        rmock.register_uri('GET', '{}/api/json'.format(jenkins_agent.url), [
            {
                'json': json.load(open('tests/http/jenkins.build1.offline-terminated.json')),
                'status_code': 200
            },
        ])

        assert all([jenkins_agent.is_idle, not jenkins_agent.is_online,
                    jenkins_agent.is_offline, not jenkins_agent.is_temporarily_offline])

        assert jenkins_agent.offline_cause_reason == 'hudson.slaves.OfflineCause$UserCause || jam.stop'


def test_status_is_offline_long_causereason(jenkins_agent):
    with requests_mock.mock() as rmock:
        tests.helpers.helpers_jenkins.inject_crumb_issuer(rmock, 200)
        rmock.register_uri('GET', '{}/api/json'.format(jenkins_agent.url), [
            {
                'json': json.load(open('tests/http/jenkins.build1.offline-long-causereason.json')),
                'status_code': 200
            },
        ])

        assert all([jenkins_agent.is_idle, not jenkins_agent.is_online,
                    jenkins_agent.is_offline, not jenkins_agent.is_temporarily_offline])

        assert jenkins_agent.offline_cause_reason == 'hudson.slaves.OfflineCause$ChannelTermination'


def test_status_no_auth(jenkins_agent):
    with requests_mock.mock() as rmock:
        tests.helpers.helpers_jenkins.inject_crumb_issuer(rmock, 403)

        with pytest.raises(requests.ConnectionError):
            _ = jenkins_agent.is_idle  # noqa: F841


def test_force_launch(jenkins_agent):
    with mock.patch('jam.libs.jenkins.JenkinsAgent.WAIT_TIME_FORCE_LAUNCH', 0):
        with requests_mock.mock() as rmock:
            tests.helpers.helpers_jenkins.inject_crumb_issuer(rmock, 200)
            rmock.register_uri('GET', '{}/api/json'.format(jenkins_agent.url), [
                {'json': json.load(open('tests/http/jenkins.build1.offline-terminated.json')), 'status_code': 200},
                {'json': json.load(open('tests/http/jenkins.build1.offline-terminated.json')), 'status_code': 200},
                {'json': json.load(open('tests/http/jenkins.build1.offline-terminated.json')), 'status_code': 200},
                {'json': json.load(open('tests/http/jenkins.build1.offline-starting-up.json')), 'status_code': 200},
                {'json': json.load(open('tests/http/jenkins.build1.offline-starting-up.json')), 'status_code': 200},
                {'json': json.load(open('tests/http/jenkins.build1.offline-starting-up.json')), 'status_code': 200},
                {'json': json.load(open('tests/http/jenkins.build1.offline-starting-up.json')), 'status_code': 200},
                {'json': json.load(open('tests/http/jenkins.build1.idle.json')), 'status_code': 200},
            ])
            rmock.register_uri('POST', '{}/launchSlaveAgent'.format(jenkins_agent.url), [
                {
                    'headers': {'Location': '{}/log'.format(jenkins_agent.url)},
                    'status_code': 302,
                },
            ])
            rmock.register_uri('GET', '{}/log'.format(jenkins_agent.url), [
                {
                    'text': '<html><head/><body>Some mocked shortened response!</body></html>',
                    'status_code': 200,
                },
            ])
            assert not jenkins_agent.is_online
            jenkins_agent.force_launch()
            assert jenkins_agent.is_online


def test_launch(jenkins_agent):
    with mock.patch('jam.libs.jenkins.JenkinsAgent.WAIT_TIME_FORCE_LAUNCH', 0):
        with mock.patch.object(jam.libs.jenkins.JenkinsAgent, 'api_call') as mock_api_call:
            jenkins_agent.launch()
        mock_api_call.assert_called_once_with('post', 'launchSlaveAgent')


def test_stop(jenkins_agent):
    with mock.patch('jam.libs.jenkins.JenkinsAgent.WAIT_TIME_FORCE_LAUNCH', 0):
        with mock.patch.object(jam.libs.jenkins.JenkinsAgent, 'api_call') as mock_api_call:
            jenkins_agent.stop()
        mock_api_call.assert_called_once_with('post', 'doDisconnect?offlineMessage=jam.stop')


def test_labels_several(jenkins_agent):
    with requests_mock.mock() as rmock:
        tests.helpers.helpers_jenkins.inject_crumb_issuer(rmock, 200)
        rmock.register_uri('GET', '{}/api/json'.format(jenkins_agent.url), [
            {
                'json': json.load(open('tests/http/jenkins.build1.busy.json')),
                'status_code': 200
            },
        ])

        assert jenkins_agent.labels == set()
        jenkins_agent.refresh()
        assert jenkins_agent.labels == {'agent', 'build1', 'windows-agent'}


def test_labels_none(jenkins_agent):
    with requests_mock.mock() as rmock:
        tests.helpers.helpers_jenkins.inject_crumb_issuer(rmock, 200)
        rmock.register_uri('GET', '{}/api/json'.format(jenkins_agent.url), [
            {
                'json': json.load(open('tests/http/jenkins.build2.offline-terminated.json')),
                'status_code': 200
            },
        ])

        assert jenkins_agent.labels == set()
        jenkins_agent.refresh()
        assert jenkins_agent.labels == set()
