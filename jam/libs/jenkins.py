import collections
import logging
import os
import re
import time

import requests

logger = logging.getLogger(__name__)


class ApiCallMixin(object):
    ApiCallSettings = collections.namedtuple('ApiCallSettings', ['base_url', 'auth', 'crumb_url'])

    def __perform_crumb_call(self, session):
        crumb_response = session.get(url=self.api_settings.crumb_url, auth=self.api_settings.auth)
        if crumb_response.status_code != 200:
            logger.error(
                "url=%s\nheaders=%s\nbody=%s\n",
                crumb_response.request.url, crumb_response.request.headers, crumb_response.request.body
            )
            logger.error(self.api_settings.auth)
            logger.error(crumb_response.text)
            raise requests.ConnectionError('Could not issue Jenkins crumb.', response=crumb_response)
        return crumb_response.json()

    def api_call(self, method, api, retries=3):
        if not hasattr(self, 'api_settings') or not isinstance(self.api_settings, self.ApiCallSettings):
            raise AttributeError(
                f"Class {self.__class__.__name__} must have a member called 'api_settings' "
                f"which should be a {self.ApiCallSettings.__name__}!"
            )
        url = f'{self.api_settings.base_url}/{api}'
        header = '[%s %s]' if hasattr(self, 'name') else '[%s]'
        args = [self.__class__.__name__, self.name] if hasattr(self, 'name') else [self.__class__.__name__]
        args_full = args + [method.upper(), url]
        logger.debug(f"{header} External API call %s %s", *args_full)
        exc_info = None
        for retry in range(retries):
            with requests.session() as session:
                try:
                    crumb = self.__perform_crumb_call(session=session)
                    return session.request(method=method, url=url, auth=self.api_settings.auth, headers={
                        crumb['crumbRequestField']: crumb['crumb'],
                    })
                except requests.ConnectionError as err:
                    args_retry_fail = args + [retry + 1, retries]
                    logger.exception(f"{header} Try %d/%d failed.", *args_retry_fail)
                    exc_info = err
        else:
            logger.error(f"{header} API call %s %s failed!", *args_full)
            raise exc_info


class Jenkins(ApiCallMixin):
    def __init__(self, url, username, api_token):
        url_match = re.match(r'^(?P<protocol>.*://)?(?P<bare_url>.*)/?$', url).groupdict()
        self.url = f"{url_match.get('protocol', 'http://')}{url_match['bare_url']}"
        self.crumb_url = f'{self.url}/crumbIssuer/api/json'
        self.agents = collections.OrderedDict()
        self.auth = (username, api_token)
        self.job_url = os.getenv('JOB_URL', f'{self.url}/job/Jam/')
        self.api_settings = self.ApiCallSettings(base_url=self.url, auth=self.auth, crumb_url=self.crumb_url)

    def get_agent(self, name):
        return self.agents.setdefault(
            name, JenkinsAgent(url=self.url, name=name, auth=self.auth, crumb_url=self.crumb_url)
        )

    @property
    def jobs(self):
        try:
            return [job for job in self.api_call('get', 'queue/api/json').json()['items']
                    if not job['task'].get('url', None) == self.job_url]
        except requests.ConnectionError:
            logger.exception("[%s] Impossible to retrieve job queue.", self.__class__.__name__)
            raise


class JenkinsAgent(ApiCallMixin):
    QUIET_OFFLINE_CAUSES = {
        'hudson.slaves.OfflineCause$ChannelTermination',
    }
    WAIT_TIME_FORCE_LAUNCH = 15

    def __init__(self, url, name, auth=None, crumb_url=None):
        self.url = f'{url}/computer/{name}'
        self.name = name
        self.labels = set()
        self.info = {}
        self.auth = auth
        self.crumb_url = crumb_url
        self.api_settings = self.ApiCallSettings(base_url=self.url, auth=self.auth, crumb_url=self.crumb_url)

    @property
    def is_idle(self):
        self.refresh()
        return self.info['idle']

    @property
    def is_online(self):
        self.refresh()
        return not any([self.info['offline'], self.info['temporarilyOffline']])

    @property
    def is_offline(self):
        self.refresh()
        return self.info['offline']

    @property
    def is_temporarily_offline(self):
        self.refresh()
        return self.info['temporarilyOffline']

    @property
    def offline_cause_reason(self):
        self.refresh()
        if not self.info['offlineCauseReason']:
            return None
        if self.info['offlineCause']['_class'] in self.QUIET_OFFLINE_CAUSES:
            return self.info['offlineCause']['_class']
        return f"{self.info['offlineCause']['_class']} || {self.info['offlineCauseReason']}"

    def force_launch(self):
        while not self.is_online:
            logger.info("[%s %s] Agent is not launched.", self.__class__.__name__, self.name)
            offline_cause_reason = self.offline_cause_reason
            if offline_cause_reason is not None:
                logger.info(
                    "[%s %s] Agent is offline because %s.", self.__class__.__name__, self.name, offline_cause_reason
                )
                self.launch()
            time.sleep(self.WAIT_TIME_FORCE_LAUNCH)
        logger.info("[%s %s] Agent is launched.", self.__class__.__name__, self.name)

    def _update_labels(self):
        self.labels = set(label_data['name'] for label_data in self.info.get('assignedLabels', []))

    def refresh(self):
        try:
            self.info = self.api_call('get', 'api/json').json()
            self._update_labels()
        except requests.ConnectionError:
            logger.exception("[%s %s] Impossible to get information about this agent!",
                             self.__class__.__name__, self.name)
            raise

    def launch(self):
        logger.info("[%s %s] Launching Agent.", self.__class__.__name__, self.name)
        self.api_call('post', 'launchSlaveAgent')

    def stop(self):
        logger.info("[%s %s] Stopping Agent.", self.__class__.__name__, self.name)
        self.api_call('post', 'doDisconnect?offlineMessage=jam.stop')
