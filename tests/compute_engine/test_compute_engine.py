import pytest

import jam.libs.compute_engine
import tests.helpers.helpers_compute_engine

jam.libs.compute_engine.TIME_SLEEP_WAIT_FOR_OPERATION = 0
jam.libs.compute_engine.TIME_SLEEP_WAIT_FOR_STATUS = 0
DEFAULT_STALE_AFTER_MS = jam.libs.compute_engine.ComputeEngineInstance.DEFAULT_STALE_AFTER_MS


def test_compute_engine_list_all_instances(compute_engine, http_sequence_factory):
    http = http_sequence_factory([
        ({'status': '200'}, 'file:tests/http/compute-discovery.json'),
        ({'status': '200'}, 'file:tests/http/compute.instances.list.json')],
    )
    compute_engine.http = http
    assert {'build1', 'master'} <= set(compute_engine.instances.iterkeys())


def test_compute_engine_get_instance_exists(compute_engine, http_sequence_factory):
    http = http_sequence_factory([
        ({'status': '200'}, 'file:tests/http/compute-discovery.json'),
        ({'status': '200'}, 'file:tests/http/compute.instances.get.build1-running.json'),
    ])
    compute_engine.http = http
    instance = compute_engine.get_instance('build1')
    assert instance.name == 'build1'
    assert instance.status == 'RUNNING'


def test_compute_engine_get_instance_not_exists(compute_engine, http_sequence_factory):
    http = http_sequence_factory([
        ({'status': '200'}, 'file:tests/http/compute-discovery.json'),
        ({'status': '404'}, 'file:tests/http/compute.instances.get.nonexistentnode.json'),
    ])
    compute_engine.http = http
    instance = compute_engine.get_instance('nonexistentnode')
    assert instance.name == 'nonexistentnode'
    with pytest.raises(jam.libs.compute_engine.InstanceNotFound):
        _ = instance.status  # noqa: F841


def test_compute_engine_start_instance(compute_engine, http_sequence_factory):
    http = http_sequence_factory([
        ({'status': '200'}, 'file:tests/http/compute-discovery.json'),
        ({'status': '200'}, 'file:tests/http/compute.instances.get.build1-terminated.json'),
        ({'status': '200'}, 'file:tests/http/compute.instances.start.build1.json'),
        ({'status': '200'}, 'file:tests/http/compute.operations.get-start-running.json'),
        ({'status': '200'}, 'file:tests/http/compute.operations.get-start-done.json'),
        ({'status': '200'}, 'file:tests/http/compute.instances.get.build1-running.json'),
    ])
    compute_engine.http = http
    instance = compute_engine.get_instance('build1')
    assert instance.status == 'TERMINATED'
    instance.start()
    tests.helpers.helpers_compute_engine.make_info_instantly_stale(instance)
    assert instance.status == 'RUNNING'


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
    instance = compute_engine.get_instance('build1')
    assert instance.status == 'RUNNING'
    instance.stop()
    tests.helpers.helpers_compute_engine.make_info_instantly_stale(instance)
    assert instance.status == 'TERMINATED'


# TODO: Add tests for when things are failing
