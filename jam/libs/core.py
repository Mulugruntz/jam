import collections
import logging
import random

import enum

import jam.libs.compute_engine
from jam.libs.compute_engine import InstanceStatus
import jam.libs.jenkins
import jam.libs.utils

logger = logging.getLogger(__name__)


class Jam(object):
    def __init__(self, jenkins_url, jenkins_username, jenkins_api_token, project, gce_zone, usable_nodes):
        self.jenkins_url = jenkins_url
        self.jenkins_username = jenkins_username
        self.jenkins_api_token = jenkins_api_token
        self.project = project
        self.gce_zone = gce_zone
        self.compute_engine = jam.libs.compute_engine.ComputeEngine(project, gce_zone)
        self.jenkins = jam.libs.jenkins.Jenkins(jenkins_url, jenkins_username, jenkins_api_token)
        self.usable_node_names = usable_nodes
        self.__nodes = None

    @property
    def nodes(self):
        if self.__nodes is None:
            self.__nodes = collections.OrderedDict(
                (name, Node(self.jenkins.get_agent(name), self.compute_engine.get_instance(name)))
                for name in self.usable_node_names
            )
        return self.__nodes

    @property
    def idle_nodes(self):
        return {k: v for k, v in self.nodes.items() if v.is_on and v.agent.is_idle}

    @property
    def busy_nodes(self):
        return {k: v for k, v in self.nodes.items() if v.is_on and not v.agent.is_idle}

    @property
    def offline_nodes(self):
        return {k: v for k, v in self.nodes.items() if v.is_off}

    @property
    def starting_nodes(self):
        return {k: v for k, v in self.nodes.items() if v.is_switching_on}

    @property
    def stopping_nodes(self):
        return {k: v for k, v in self.nodes.items() if v.is_switching_off}

    def balance_nodes(self):
        jobs = self.jenkins.jobs
        idle_or_starting_nodes = jam.libs.utils.merge_dicts(self.idle_nodes, self.starting_nodes)
        if jobs:
            if len(idle_or_starting_nodes) == len(jobs):
                logger.info(
                    "[Jam] There should be enough idle/starting nodes (%d) to take care of the jobs (%d) in queue.",
                    len(idle_or_starting_nodes), len(jobs)
                )
            elif len(idle_or_starting_nodes) > len(jobs):
                logger.info(
                    "[Jam] We have too many idle/starting nodes (%s) for the amount of jobs in the queue (%d).",
                    ', '.join(idle_or_starting_nodes.keys()),
                    len(jobs),
                )
                self.scale_down()
            else:
                logger.info(
                    "[Jam] We do not have enough idle/starting nodes (%s) for the amount of jobs in the queue (%d).",
                    ', '.join(idle_or_starting_nodes.keys()),
                    len(jobs),
                )
                self.scale_up()
        elif idle_or_starting_nodes:
            logger.info(
                "[Jam] We have no jobs in the queue and the following node(s) are idle/starting: %s",
                ', '.join(idle_or_starting_nodes.keys())
            )
            self.scale_down()

    def scale_up(self):
        jobs = self.jenkins.jobs
        offline_nodes = self.offline_nodes
        idle_or_starting_nodes = jam.libs.utils.merge_dicts(self.idle_nodes, self.starting_nodes)
        if offline_nodes:
            nb_to_start_up = max(min(len(offline_nodes), len(jobs) - len(idle_or_starting_nodes)), 0)
            selected_offline_nodes = {
                name: offline_nodes[name]
                for name in random.sample(list(offline_nodes), nb_to_start_up)
            }
            logger.info(
                "[Jam] The following nodes will be switched on: %s", ', '.join(selected_offline_nodes.keys())
            )
            for node in selected_offline_nodes.values():
                node.on()  # TODO: put in thread
        else:
            logger.info("[Jam] There are currently no offline nodes.")
            logger.info("[Jam] Currently busy nodes: %s", ', '.join(self.busy_nodes.keys()))

    def scale_down(self):
        jobs = self.jenkins.jobs
        idle_nodes = self.idle_nodes
        if idle_nodes:
            nb_to_shutdown = max(len(idle_nodes) - len(jobs), 0)
            selected_idle_nodes = {
                name: idle_nodes[name]
                for name in random.sample(list(idle_nodes), nb_to_shutdown)
            }
            logger.info(
                "[Jam] The following nodes will be switched off: %s", ', '.join(selected_idle_nodes.keys())
            )
            for node in selected_idle_nodes.values():
                node.off()  # TODO: put in thread
        else:
            logger.error("[Jam] There is an error in the algorithm!")


class NodeStatus(enum.Enum):
    ON = 'ON'
    OFF = 'OFF'
    SWITCHING_ON = 'SWITCHING_ON'
    SWITCHING_OFF = 'SWITCHING_OFF'
    UNKNOWN = 'UNKNOWN'


class Node(object):
    def __init__(self, agent, instance):
        """

        :param libs.jenkins.JenkinsAgent agent:
        :param libs.compute_engine.ComputeEngineInstance instance:
        """
        if not agent.name == instance.name:
            raise ValueError(
                "Agent and Instance must have the same name ({} is not {})".format(agent.name, instance.name)
            )
        self.name = agent.name
        self.agent = agent
        self.instance = instance
        self.__status = None

    @property
    def status(self):
        if self.agent.is_online and self.instance.status == InstanceStatus.RUNNING:
            self.__status = NodeStatus.ON
        elif self.instance.status in [InstanceStatus.STOPPED, InstanceStatus.SUSPENDED, InstanceStatus.TERMINATED]:
            self.__status = NodeStatus.OFF
        elif self.instance.status in [InstanceStatus.PROVISIONING, InstanceStatus.STAGING]:
            self.__status = NodeStatus.SWITCHING_ON
        elif self.instance.status in [InstanceStatus.STOPPING, InstanceStatus.SUSPENDING]:
            self.__status = NodeStatus.SWITCHING_OFF
        else:
            self.__status = NodeStatus.UNKNOWN  # pragma: no cover
        return self.__status

    @property
    def is_on(self):
        return self.status == NodeStatus.ON

    @property
    def is_off(self):
        return self.status == NodeStatus.OFF

    @property
    def is_switching_on(self):
        return self.status == NodeStatus.SWITCHING_ON

    @property
    def is_switching_off(self):
        return self.status == NodeStatus.SWITCHING_OFF

    def on(self):
        logger.info("[%s %s] Switching on.", self.__class__.__name__, self.name)
        if not self.instance.status == InstanceStatus.RUNNING:
            self.instance.start()
            self.instance.wait_for_status(InstanceStatus.RUNNING)
        self.agent.force_launch()
        logger.info("[%s %s] The Node is on.", self.__class__.__name__, self.name)

    def off(self):
        logger.info("[%s %s] Switching off.", self.__class__.__name__, self.name)
        if self.agent.is_online:
            self.agent.stop()
        if self.instance.status in [InstanceStatus.PROVISIONING, InstanceStatus.STAGING, InstanceStatus.RUNNING]:
            self.instance.stop()
            self.instance.wait_for_status(
                [InstanceStatus.STOPPED, InstanceStatus.SUSPENDED, InstanceStatus.TERMINATED]
            )
        logger.info("[%s %s] The Node is off.", self.__class__.__name__, self.name)
