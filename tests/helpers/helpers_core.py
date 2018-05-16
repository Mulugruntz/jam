import contextlib

import mock

import jam.libs.core
import tests.helpers.helpers_compute_engine


def get_jam():
    manager = jam.libs.core.Jam(
        jenkins_url=tests.helpers.helpers_jenkins.get_base_url(),
        jenkins_username='user',
        jenkins_api_token='pass',
        project='jam-project',
        gce_zone='europe-west1-b',
        usable_nodes=['build1', 'build2'],
    )
    return manager


@contextlib.contextmanager
def no_pause():
    try:
        with tests.helpers.helpers_compute_engine.no_pause(), \
             mock.patch('jam.libs.jenkins.JenkinsAgent.WAIT_TIME_FORCE_LAUNCH', 0):
            yield
    finally:
        pass
