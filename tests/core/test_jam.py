import collections
import json

import mock
import pytest
import requests_mock

import jam.libs.core
import tests.conftest
import tests.helpers.helpers_jenkins


NodeDataTest = collections.namedtuple(
    'NodeDataTest', ['name', 'gce_file_status', 'jenkins_file_status']
)
ExpectedDataTest = collections.namedtuple('ExpectedDataTest', ['initial_state', 'final_state'])
# NodeDescription = collections.namedtuple('NodeDescription', ['name', 'gce_state', 'jenkins_state', 'node_state'])
# InitialState = collections.namedtuple('InitialState', ['node_descriptions', 'job_number'])
# ExpectedBehaviour = collections.namedtuple('ExpectedBehaviour', ['scale_up_called', 'scale_down_called'])


@pytest.mark.parametrize(['nodes'], [
    pytest.param(
        [],
        id='No node',
    ),
    pytest.param(
        ['build1'],
        id='One node',
    ),
    pytest.param(
        ['build1', 'build2', 'build3'],
        id='Three nodes',
    ),
])
def test_jam_nodes(jenkins_agent_manager, nodes):
    jenkins_agent_manager.usable_node_names = nodes
    jenkins_agent_manager.compute_engine.http = tests.conftest.HttpMockIterableSequence([
        ({'status': '200'}, 'file:tests/http/compute-discovery.json'),
    ])
    assert frozenset(nodes) == frozenset(jenkins_agent_manager.nodes.keys())
    assert all(isinstance(node, jam.libs.core.Node) for node in jenkins_agent_manager.nodes.values())


params_node1 = [
    pytest.param(
        NodeDataTest(
            name=None, gce_file_status=None, jenkins_file_status=None
        ),
        id='build1-nonexistent',
    ),
    pytest.param(
        NodeDataTest(
            name='build1', gce_file_status='running', jenkins_file_status='idle'
        ),
        id='build1-idle',
    ),
    pytest.param(
        NodeDataTest(
            name='build1', gce_file_status='running', jenkins_file_status='busy'
        ),
        id='build1-busy',
    ),
    pytest.param(
        NodeDataTest(
            name='build1', gce_file_status='terminated', jenkins_file_status='offline-terminated'
        ),
        id='build1-terminated',
    ),
    pytest.param(
        NodeDataTest(
            name='build1', gce_file_status='provisioning', jenkins_file_status='offline-terminated'
        ),
        id='build1-starting',
    ),
]


params_node2 = [
    pytest.param(
        NodeDataTest(
            name=None, gce_file_status=None, jenkins_file_status=None
        ),
        id='build2-nonexistent',
    ),
    pytest.param(
        NodeDataTest(
            name='build2', gce_file_status='running', jenkins_file_status='idle'
        ),
        id='build2-idle',
    ),
    pytest.param(
        NodeDataTest(
            name='build2', gce_file_status='running', jenkins_file_status='busy'
        ),
        id='build2-busy',
    ),
    pytest.param(
        NodeDataTest(
            name='build2', gce_file_status='terminated', jenkins_file_status='offline-terminated'
        ),
        id='build2-terminated',
    ),
    pytest.param(
        NodeDataTest(
            name='build2', gce_file_status='provisioning', jenkins_file_status='offline-terminated'
        ),
        id='build2-starting',
    ),
]


params_num_job = [
    pytest.param(0, id="no-job"),
    pytest.param(1, id="one-job"),
    pytest.param(2, id="two-jobs"),
    pytest.param(3, id="three-jobs"),
]

node1_param = pytest.mark.parametrize(['node1'], params_node1)
node2_param = pytest.mark.parametrize(['node2'], params_node2)
num_jobs_param = pytest.mark.parametrize(['num_jobs'], params_num_job)


def helper_gce_mock(manager, nodes):
    manager.usable_node_names = [node.name for node in nodes]
    manager.compute_engine.http = tests.conftest.HttpMockIterableSequence([
        ({'status': '200'}, 'file:tests/http/compute-discovery.json'),
    ] + [
        ({'status': '200'}, 'file:tests/http/compute.instances.get.{name}-{status}.json'.format(
            name=node.name, status=node.gce_file_status
        )) for node in nodes
    ])


def helper_jenkins_mock(manager, nodes, rmock, num_jobs):
    tests.helpers.helpers_jenkins.inject_crumb_issuer(rmock, 200)
    for node in nodes:
        rmock.register_uri('GET', '{url}/computer/{name}/api/json'.format(
            url=manager.jenkins_url, name=node.name
        ), [
            {
                'json': json.load(open('tests/http/jenkins.{name}.{status}.json'.format(
                    name=node.name, status=node.jenkins_file_status
                ))),
                'status_code': 200
            },
        ])
    rmock.register_uri('GET', '{}/queue/api/json'.format(manager.jenkins_url), [
        {
            'json': json.load(open('tests/http/jenkins.queue.{}.json'.format(num_jobs))),
            'status_code': 200
        },
    ])


@pytest.mark.parametrize(['node1'], params_node1)
@pytest.mark.parametrize(['node2'], params_node2)
@pytest.mark.parametrize(['num_jobs'], params_num_job)
def test_balance_nodes(jenkins_agent_manager, node1, node2, num_jobs):
    nodes = [node for node in [node1, node2] if node.name is not None]
    helper_gce_mock(manager=jenkins_agent_manager, nodes=nodes)

    usable_candidates = [node for node in nodes
                         if node.jenkins_file_status == 'idle' or node.gce_file_status == 'provisioning']
    should_scale_up = len(usable_candidates) < num_jobs
    should_scale_down = len(usable_candidates) > num_jobs

    with requests_mock.mock() as rmock:
        helper_jenkins_mock(manager=jenkins_agent_manager, nodes=nodes, rmock=rmock, num_jobs=num_jobs)
        with mock.patch('jam.libs.core.Jam.scale_up') as mocked_scale_up, \
                mock.patch('jam.libs.core.Jam.scale_down') as mocked_scale_down:

            jenkins_agent_manager.balance_nodes()
            if should_scale_up:
                mocked_scale_up.assert_called()
            else:
                mocked_scale_up.assert_not_called()
            if should_scale_down:
                mocked_scale_down.assert_called()
            else:
                mocked_scale_down.assert_not_called()


@pytest.mark.parametrize(['node1'], params_node1)
@pytest.mark.parametrize(['node2'], params_node2)
@pytest.mark.parametrize(['num_jobs'], params_num_job)
def test_scale_up(jenkins_agent_manager, node1, node2, num_jobs):
    nodes = [node for node in [node1, node2] if node.name is not None]

    usable_candidates = [node for node in nodes
                         if node.jenkins_file_status == 'idle' or node.gce_file_status == 'provisioning']
    bootup_candidates = [node for node in nodes if node.gce_file_status == 'terminated']
    should_scale_up = len(usable_candidates) < num_jobs

    if not should_scale_up:
        pytest.skip("scale_up is unreachable with these parameters.")

    can_scale_up = should_scale_up and len(bootup_candidates) > 0
    how_many_up = min(num_jobs - len(usable_candidates), len(bootup_candidates))
    helper_gce_mock(manager=jenkins_agent_manager, nodes=nodes)

    with requests_mock.mock() as rmock:
        helper_jenkins_mock(manager=jenkins_agent_manager, nodes=nodes, rmock=rmock, num_jobs=num_jobs)
        with mock.patch('jam.libs.core.Node.on') as mocked_on:

            jenkins_agent_manager.scale_up()
            if can_scale_up:
                mocked_on.assert_called()
                assert mocked_on.call_count == how_many_up
            else:
                mocked_on.assert_not_called()


@pytest.mark.parametrize(['node1'], params_node1)
@pytest.mark.parametrize(['node2'], params_node2)
@pytest.mark.parametrize(['num_jobs'], params_num_job)
def test_scale_down(jenkins_agent_manager, node1, node2, num_jobs):
    nodes = [node for node in [node1, node2] if node.name is not None]
    helper_gce_mock(manager=jenkins_agent_manager, nodes=nodes)

    shutdown_candidates = [node for node in nodes if node.jenkins_file_status == 'idle']
    usable_candidates = [node for node in nodes
                         if node.jenkins_file_status == 'idle' or node.gce_file_status == 'provisioning']
    should_scale_down = len(usable_candidates) > num_jobs
    how_many_down = len(shutdown_candidates) - num_jobs

    if not should_scale_down:
        pytest.skip()

    with requests_mock.mock() as rmock:
        helper_jenkins_mock(manager=jenkins_agent_manager, nodes=nodes, rmock=rmock, num_jobs=num_jobs)
        with mock.patch('jam.libs.core.Node.off') as mocked_off:

            jenkins_agent_manager.scale_down()
            if how_many_down > 0:
                mocked_off.assert_called()
                assert mocked_off.call_count == how_many_down
            else:
                mocked_off.assert_not_called()
