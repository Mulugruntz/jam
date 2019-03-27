import pytest
from googleapiclient.errors import HttpError

import jam.libs.compute_engine
from jam.libs.compute_engine import InstanceStatus
import tests.helpers.helpers_compute_engine


def test_compute_engine_wait_for_operation(compute_engine, http_sequence_factory):
    http = http_sequence_factory([
        ({'status': '200'}, 'file:tests/http/compute-discovery.json'),
        ({'status': '404'}, 'file:tests/http/compute.operations.get-invalid.json'),
    ])
    compute_engine.http = http
    with tests.helpers.helpers_compute_engine.no_pause():
        with pytest.raises(HttpError):
            compute_engine.wait_for_operation({'name': 'invalid_id'})


def test_compute_engine_list_all_instances(compute_engine, http_sequence_factory):
    http = http_sequence_factory([
        ({'status': '200'}, 'file:tests/http/compute-discovery.json'),
        ({'status': '200'}, 'file:tests/http/compute.instances.list.json')],
    )
    compute_engine.http = http
    with tests.helpers.helpers_compute_engine.no_pause():
        assert {'build1', 'master'} <= set(compute_engine.instances.keys())


def test_compute_engine_get_instance_exists(compute_engine, http_sequence_factory):
    http = http_sequence_factory([
        ({'status': '200'}, 'file:tests/http/compute-discovery.json'),
        ({'status': '200'}, 'file:tests/http/compute.instances.get.build1-running.json'),
    ])
    compute_engine.http = http
    with tests.helpers.helpers_compute_engine.no_pause():
        instance = compute_engine.get_instance('build1')
        assert instance.name == 'build1'
        assert instance.status is InstanceStatus.RUNNING


def test_compute_engine_get_instance_not_exists(compute_engine, http_sequence_factory):
    http = http_sequence_factory([
        ({'status': '200'}, 'file:tests/http/compute-discovery.json'),
        ({'status': '404'}, 'file:tests/http/compute.instances.get.nonexistentnode.json'),
    ])
    compute_engine.http = http
    with tests.helpers.helpers_compute_engine.no_pause():
        instance = compute_engine.get_instance('nonexistentnode')
        assert instance.name == 'nonexistentnode'
        with pytest.raises(jam.libs.compute_engine.InstanceNotFound):
            _ = instance.status  # noqa: F841


def test_compute_engine_wait_for_status(compute_engine, http_sequence_factory):
    http = http_sequence_factory([
        ({'status': '200'}, 'file:tests/http/compute-discovery.json'),
        ({'status': '200'}, 'file:tests/http/compute.instances.get.build1-terminated.json'),
        ({'status': '200'}, 'file:tests/http/compute.instances.get.build1-terminated.json'),
        ({'status': '200'}, 'file:tests/http/compute.instances.get.build1-provisioning.json'),
        ({'status': '200'}, 'file:tests/http/compute.instances.get.build1-provisioning.json'),
        ({'status': '200'}, 'file:tests/http/compute.instances.get.build1-provisioning.json'),
        ({'status': '200'}, 'file:tests/http/compute.instances.get.build1-running.json'),
    ])
    compute_engine.http = http
    with tests.helpers.helpers_compute_engine.no_pause():
        instance = compute_engine.get_instance('build1')
        assert instance.status is InstanceStatus.TERMINATED
        instance.wait_for_status(InstanceStatus.RUNNING)
        assert instance.status is InstanceStatus.RUNNING


def test_compute_engine_start_instance(compute_engine, http_sequence_factory):
    http = http_sequence_factory([
        ({'status': '200'}, 'file:tests/http/compute-discovery.json'),
        ({'status': '200'}, 'file:tests/http/compute.instances.get.build1-terminated.json'),
        ({'status': '200'}, 'file:tests/http/compute.instances.start.build1.json'),
        ({'status': '200'}, 'file:tests/http/compute.operations.get-start-running.json'),
        ({'status': '200'}, 'file:tests/http/compute.operations.get-start-running.json'),
        ({'status': '200'}, 'file:tests/http/compute.operations.get-start-done.json'),
        ({'status': '200'}, 'file:tests/http/compute.instances.get.build1-running.json'),
    ])
    compute_engine.http = http
    with tests.helpers.helpers_compute_engine.no_pause():
        instance = compute_engine.get_instance('build1')
        assert instance.status is InstanceStatus.TERMINATED
        instance.start()
        tests.helpers.helpers_compute_engine.make_info_instantly_stale(instance)
        assert instance.status is InstanceStatus.RUNNING


def test_compute_engine_stop_instance(compute_engine, http_sequence_factory):
    http = http_sequence_factory([
        ({'status': '200'}, 'file:tests/http/compute-discovery.json'),
        ({'status': '200'}, 'file:tests/http/compute.instances.get.build1-running.json'),
        ({'status': '200'}, 'file:tests/http/compute.instances.stop.build1.json'),
        ({'status': '200'}, 'file:tests/http/compute.operations.get-stop-running.json'),
        ({'status': '200'}, 'file:tests/http/compute.operations.get-stop-done.json'),
        ({'status': '200'}, 'file:tests/http/compute.instances.get.build1-terminated.json'),
    ])
    compute_engine.http = http
    with tests.helpers.helpers_compute_engine.no_pause():
        instance = compute_engine.get_instance('build1')
        assert instance.status is InstanceStatus.RUNNING
        instance.stop()
        tests.helpers.helpers_compute_engine.make_info_instantly_stale(instance)
        assert instance.status is InstanceStatus.TERMINATED


@pytest.mark.parametrize(['status', 'expected_statuses'], [
    pytest.param(
        InstanceStatus.RUNNING,
        frozenset([InstanceStatus.RUNNING]),
        id='Put in set',
    ),
    pytest.param(
        'RUNNING',
        frozenset([InstanceStatus.RUNNING]),
        id='Put in set and enum',
    ),
    pytest.param(
        [InstanceStatus.RUNNING],
        frozenset([InstanceStatus.RUNNING]),
        id='one element list',
    ),
    pytest.param(
        [InstanceStatus.RUNNING, InstanceStatus.STAGING],
        frozenset([InstanceStatus.RUNNING, InstanceStatus.STAGING]),
        id='two elements list',
    ),
    pytest.param(
        ['RUNNING', 'STAGING'],
        frozenset([InstanceStatus.RUNNING, InstanceStatus.STAGING]),
        id='two elements (str) list',
    ),
    pytest.param(
        ['RUNNING', InstanceStatus.STAGING],
        frozenset([InstanceStatus.RUNNING, InstanceStatus.STAGING]),
        id='two elements (mixed) list',
    ),
    pytest.param(
        ['RUNNING', InstanceStatus.RUNNING],
        frozenset([InstanceStatus.RUNNING]),
        id='two elements (mixed) redundant list',
    ),
    pytest.param(
        [InstanceStatus.RUNNING, InstanceStatus.RUNNING],
        frozenset([InstanceStatus.RUNNING]),
        id='two elements (enum) redundant list',
    ),
])
def test_format_status(status, expected_statuses):
    assert jam.libs.compute_engine.ComputeEngineInstance.format_status(status) == expected_statuses


# TODO: Add tests for when things are failing
