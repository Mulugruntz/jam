import json


def get_crumb_url():
    return '{}/crumbIssuer/api/json'.format(get_base_url())


def get_base_url():
    return 'mock://jenkins.mydomain.com:8080'


def headers_to_dict(header_file):
    """Reads from a header file and generates a ``dict`` from it.

    :param str header_file: Path to the header file.
    :return dict: The headers, in a ``dict`` representation.
    """
    headers_dict = {}
    with open(header_file, 'r') as headers:
        for header in headers:
            key, value = header.split(': ', 1)
            if key in headers_dict:
                raise KeyError('key {} is present twice in header file {}'.format(key, header_file))
            headers_dict[key] = value
    return headers_dict


def inject_crumb_issuer(rmock, status_code):
    if status_code == 200:
        rmock.register_uri('GET', get_crumb_url(), [
            {'json': json.load(open('tests/http/jenkins.crumbissuer.200.json')), 'status_code': 200},
        ])

    elif status_code == 401:
        rmock.register_uri('GET', get_crumb_url(), [
            {
                'body': open('tests/http/jenkins.crumbissuer.401.html', mode='rb'),
                'status_code': 401,
                'headers': headers_to_dict(
                    'tests/http/jenkins.crumbissuer.401.headers.txt'
                ),
            },
        ])

    elif status_code == 403:
        rmock.register_uri('GET', get_crumb_url(), [
            {
                'body': open('tests/http/jenkins.crumbissuer.403.html', mode='rb'),
                'status_code': 403,
                'headers': headers_to_dict(
                    'tests/http/jenkins.crumbissuer.403.headers.txt'
                ),
            },
        ])
