import pytest

import tests.conftest
import tests.helpers.helpers_jenkins
import tests.helpers.helpers_core
import tests.compute_engine.conftest
import tests.jenkins.conftest


@pytest.fixture
def node():
    return tests.helpers.helpers_core.get_jam().nodes['build1']


@pytest.fixture
def jenkins_agent_manager():
    return tests.helpers.helpers_core.get_jam()
