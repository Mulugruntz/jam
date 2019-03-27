import sys

import mock
import pytest

import jam.startup


@pytest.fixture
def argv():
    return [
        '--project=jam-project ',
        '--jenkins-url=mock://jenkins.mydomain.com:8080',
        '--jenkins-api-token=pass',
        '--jenkins-username=user',
    ]


class AlmostAlwaysTrue(object):

    def __init__(self, total_iterations=1):
        self.total_iterations = total_iterations
        self.current_iteration = 0

    def __bool__(self):
        if self.current_iteration < self.total_iterations:
            self.current_iteration += 1
            return bool(1)
        return bool(0)


def test_args_ok(argv):
    sys.argv[1:] = argv + ['build1', 'build2']
    args = jam.startup.parse_args()
    assert ['build1', 'build2'] == args.nodes
    assert 'europe-west1-b' == args.gce_zone
    assert set(vars(args).keys()) == {'project', 'jenkins_api_token', 'jenkins_url', 'gce_zone', 'nodes',
                                      'jenkins_username'}


def test_args_no_node(argv, capsys):
    sys.argv[1:] = argv
    with pytest.raises(SystemExit):
        jam.startup.parse_args()
    captured = capsys.readouterr()
    assert 'the following arguments are required: NODE_LIST' in captured.err


def test_monitor(argv):
    sys.argv[1:] = argv + ['build1', 'build2']
    jam.startup.LOOP_TIME = 0

    with mock.patch('jam.startup.core.Jam.balance_nodes', mock.Mock(spec=jam.startup.core.Jam.balance_nodes)) as bn:
        with mock.patch('jam.startup.keep_running') as mocked_keep_running:
            mocked_keep_running.return_value = AlmostAlwaysTrue(4)
            jam.startup.monitor()
        assert bn.call_count == 4
