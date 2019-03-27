import typing

import pytest
from googleapiclient.http import HttpMockSequence
import json
import httplib2

import logging


logger = logging.getLogger('tests')


def pytest_configure(config):
    logging.getLogger('googleapiclient.discovery').setLevel(logging.WARNING)
    logging.getLogger('flake8').setLevel(logging.ERROR)


class HttpMockIterableSequence(HttpMockSequence):
    """Gives three improvements over :class:`googleapiclient.http.HttpMockSequence`:

        * Accepts now iterators. Useful to avoid loading all resources at once.
        * The content of the response now accepts the following extra value:
            `file:a/b/c/myfile.ext` => The response will be read from `a/b/c/myfile.ext`
        * The last element gets repeated indefinitely.

    """
    def __init__(self, iterable):
        super(HttpMockIterableSequence, self).__init__(
            iterable if isinstance(iterable, typing.Iterator) else iter(iterable),
        )
        self.prev = None, None

    def request(self, uri,  # noqa: C901
                method='GET',
                body=None,
                headers=None,
                redirections=1,
                connection_type=None):
        try:
            resp, content = next(self._iterable)
        except StopIteration:
            resp, content = self.prev
        if content == 'echo_request_headers':
            content = headers
        elif content == 'echo_request_headers_as_json':
            content = json.dumps(headers)
        elif content == 'echo_request_body':
            if hasattr(body, 'read'):
                content = body.read()
            else:
                content = body
        elif content == 'echo_request_uri':
            content = uri
        if isinstance(content, (bytes, str)):
            if isinstance(content, bytes):
                content = content.decode(encoding='utf-8', errors='backslashreplace')
            if content.startswith('file:'):
                logger.debug('Reading file %s', content[len('file:'):])
                with open(content[len('file:'):], 'r') as f:
                    content = f.read()
            content = content.encode(encoding='utf-8')
        self.prev = resp, content
        return httplib2.Response(resp), content


@pytest.fixture
def http_sequence_factory():
    return HttpMockIterableSequence
