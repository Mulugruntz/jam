import collections
import datetime
import json
import logging
import re
import time
import types

import enum
import googleapiclient
import googleapiclient.discovery
import googleapiclient.errors
import oauth2client.client


logger = logging.getLogger(__name__)


TIME_SLEEP_WAIT_FOR_OPERATION = 1
TIME_SLEEP_WAIT_FOR_STATUS = 3


class ComputeEngineError(Exception):
    pass


class InstanceNotFound(ComputeEngineError):
    pass


def wait_for_operation(compute, project, gce_zone, operation):
    logger.debug('Waiting for operation to finish...')
    operation = operation['name'] if isinstance(operation, types.DictionaryType) else operation
    previous_status = None
    while True:
        result = compute.zoneOperations().get(
            project=project,
            zone=gce_zone,
            operation=operation,
        ).execute()

        if not previous_status == result['status']:
            logger.info("Operation %s is %s", result['operationType'], result['status'])
            previous_status = result['status']

        if result['status'] == 'DONE':
            if 'error' in result:
                raise Exception(result['error'])
            return result

        time.sleep(TIME_SLEEP_WAIT_FOR_OPERATION)


class InstanceStatus(str, enum.Enum):
    """https://cloud.google.com/compute/docs/instances/checking-instance-status"""

    """Resources are being reserved for the instance. The instance isn't running yet."""
    PROVISIONING = 'PROVISIONING'

    """Resources have been acquired and the instance is being prepared for launch."""
    STAGING = 'STAGING'

    """The instance is booting up or running. You should be able to ssh into the instance soon, though not
    immediately, after it enters this state."""
    RUNNING = 'RUNNING'

    """The instance is being stopped either due to a failure, or the instance being shut down. This is a temporary
    status and the instance will move to `TERMINATED`."""
    STOPPING = 'STOPPING'

    """No doc? Deprecated?"""
    STOPPED = 'STOPPED'

    """The instance is being suspended, saving its state to persistent storage, and allowed to be resumed at a
    later time. This is a temporary status and the instance will move to `SUSPENDED`."""
    SUSPENDING = 'SUSPENDING'

    """The instance is suspended. Suspended instances incur reduced per-minute, virtual machine usage charges while
    they are suspended. Any resources the virtual machine is using, such as persistent disks and static IP addresses,
    will continue to be charged until they are deleted."""
    SUSPENDED = 'SUSPENDED'

    """The instance was shut down or encountered a failure, either through the API or from inside the guest.
    You can choose to restart the instance or delete it."""
    TERMINATED = 'TERMINATED'


class ComputeEngine(object):
    def __init__(self, project, gce_zone, http=None):
        self.project = project
        self.gce_zone = gce_zone
        self.http = http
        self.credentials = None
        self.__compute = None
        self.__instances = collections.OrderedDict()

    @property
    def compute(self):
        if self.__compute is None:
            if self.http is None:
                self.credentials = oauth2client.client.GoogleCredentials.get_application_default()  # pragma: no cover
            self.__compute = googleapiclient.discovery.build(
                'compute', 'v1', credentials=self.credentials, cache_discovery=False, http=self.http
            )
        return self.__compute

    def get_instance(self, name):
        return self.__instances.setdefault(name, ComputeEngineInstance(
            name=name,
            compute=self.compute,
            project=self.project,
            gce_zone=self.gce_zone,
        ))

    def wait_for_operation(self, operation):
        return wait_for_operation(
            compute=self.compute, project=self.project, gce_zone=self.gce_zone, operation=operation['name']
        )

    @property
    def instances(self):
        result = self.compute.instances().list(project=self.project, zone=self.gce_zone).execute()
        result_ts = datetime.datetime.now()
        self.__instances = {
            item['name']: ComputeEngineInstance.build_from_info(
                compute=self.compute,
                info=item,
                info_ts=result_ts,
            ) for item in result['items']
        }
        logger.info("[%s %s] Discovered the following instances: %s.",
                    self.__class__.__name__, self.project,
                    ', '.join(name for name in self.__instances.iterkeys()))
        return self.__instances


class ComputeEngineInstance(object):
    DEFAULT_STALE_AFTER_MS = 1000

    def __init__(self, name, compute, project, gce_zone, stale_after=None):
        self.name = name
        self.compute = compute
        self.project = project
        self.gce_zone = gce_zone
        self.info = None
        self.stale_after = datetime.timedelta(
            milliseconds=self.DEFAULT_STALE_AFTER_MS if stale_after is None else stale_after,
        )
        self.info_ts = datetime.datetime.min

    @classmethod
    def build_from_info(cls, compute, info, info_ts=None, stale_after=None):
        regex = (r'https://www.googleapis.com/compute/(?:beta|v\d)'
                 r'/projects/(?P<project>.*)'
                 r'/zones/(?P<gce_zone>.*)'
                 r'/instances/(?P<name>.*)')
        match = re.match(regex, info['selfLink']).groupdict()
        instance = cls(
            name=info['name'],
            compute=compute,
            project=match['project'],
            gce_zone=match['gce_zone'],
            stale_after=stale_after,
        )
        instance.info = info
        instance.info_ts = datetime.datetime.now() if info_ts is None else info_ts
        return instance

    def refresh(self):
        try:
            self.info = self.compute.instances().get(
                project=self.project, zone=self.gce_zone, instance=self.name
            ).execute()
            self.info_ts = datetime.datetime.now()
        except googleapiclient.errors.HttpError as err:
            content = json.loads(err.content)
            errors = content.get('error', {}).get('errors', [])
            for error in errors:
                if error['reason'] == 'notFound':
                    raise InstanceNotFound(
                        "Instance {} does not exist in project {}".format(self.name, self.project)
                    )
            else:
                raise ComputeEngineError("Unknown error with Instance {} in project {}: {}".format(  # pragma: no cover
                    self.name, self.project, errors,
                ))

    @property
    def status(self):
        if datetime.datetime.now() - self.info_ts > self.stale_after:
            self.refresh()
        return InstanceStatus(self.info['status'])

    def wait_for_operation(self, operation):
        return wait_for_operation(
            compute=self.compute, project=self.project, gce_zone=self.gce_zone, operation=operation['name']
        )

    def wait_for_status(self, statuses):
        statuses = self.format_status(statuses)
        previous_status = None
        while True:
            if not self.status == previous_status:
                logger.info('[%s %s] Instance is {}'.format(self.status), self.__class__.__name__, self.name)
            if self.status in statuses:
                break
            previous_status = self.status
            time.sleep(TIME_SLEEP_WAIT_FOR_STATUS)

    @staticmethod
    def format_status(statuses):
        if not isinstance(statuses, (types.ListType, types.TupleType, set, frozenset)):
            statuses = [statuses]
        return frozenset(InstanceStatus(status) for status in statuses)

    def start(self):
        logger.info("[%s %s] Starting Instance.", self.__class__.__name__, self.name)
        operation = self.compute.instances().start(
            project=self.project, zone=self.gce_zone, instance=self.name
        ).execute()
        self.wait_for_operation(operation=operation)
        logger.info("[%s %s] Instance status: %s.", self.__class__.__name__, self.name, self.status)

    def stop(self):
        logger.info("[%s %s] Stopping Instance.", self.__class__.__name__, self.name)
        operation = self.compute.instances().stop(
            project=self.project, zone=self.gce_zone, instance=self.name
        ).execute()
        self.wait_for_operation(operation=operation)
        logger.info("[%s %s] Instance status: %s.", self.__class__.__name__, self.name, self.status)
