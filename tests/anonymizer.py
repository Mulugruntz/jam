import collections
import json
import random
import re

import enum


class ItemKind(enum.Enum):
    INSTANCE = 'compute#instance'
    INSTANCE_LIST = 'compute#instanceList'
    OPERATION = 'compute#operation'
    UNKNOWN = 'unknown'


class ItemClass(enum.Enum):
    QUEUE = 'hudson.model.Queue'
    UNKNOWN = 'unknown'


REVERSED_ITEM_CLASS = {ic.value: ic for ic in ItemClass.__members__.values()}


class ApiType(enum.Enum):
    GOOGLE_COMPUTE_ENGINE = 'gce'
    JENKINS = 'jenkins'
    UNKNOWN = 'unknown'


REVERSED_ITEM_KIND = {ik.value: ik for ik in ItemKind.__members__.values()}


def random_ip():
    """Generates a random IP v4.

    :return str: a random IP address.
    """
    return f'{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}'


def anonymize_email(root):
    anon_email = "012345678942-compute@developer.gserviceaccount.com"
    for account in root.get('serviceAccounts', []):
        if 'email' in account:
            # $.serviceAccounts[*].email
            print(f"Replacing email {account['email']} => {anon_email}")
            account['email'] = anon_email


def anonymize_ip(root):
    for interface in root.get('networkInterfaces', []):
        for config in interface.get('accessConfigs', []):
            if 'natIP' in config:
                # $.networkInterfaces[*].accessConfigs[*].natIP
                print(f"Replacing IP {config['natIP']}")
                config['natIP'] = random_ip()


def anonymize_windows_keys(root):
    if 'metadata' in root and 'items' in root['metadata']:
        for index, metadata_item in enumerate(root['metadata']['items'][:]):
            if metadata_item.get('key') == 'windows-keys':
                # $.items[*].metadata.items[?(@.key == "windows-keys")]
                del root['metadata']['items'][index]


def anonymize_instance(root):
    # $.items[*].networkInterfaces[*].accessConfigs[*].natIP
    anonymize_ip(root)
    # $.items[*].serviceAccounts[*].email
    anonymize_email(root)
    # $.items[*].metadata.items[?(@.key == "windows-keys")]
    anonymize_windows_keys(root)


def anonymize_jenkins_queue(root):
    reg = re.compile(r'^.*://.*?(?::\d+)/(?P<api>.*)$')
    for item in root.get('items', []):
        task = item.get('task', {})
        if 'url' in task:
            task['url'] = reg.sub(r'mock://jenkins.mydomain.com:8080/\g<api>', task['url'])


def get_api_type(root):
    if 'kind' in root:
        return ApiType.GOOGLE_COMPUTE_ENGINE
    if '_class' in root:
        return ApiType.JENKINS
    return ApiType.UNKNOWN


def get_item_kind(root):
    return REVERSED_ITEM_KIND[root.get('kind', 'unknown')]


def get_item_class(root):
    return REVERSED_ITEM_CLASS[root.get('_class', 'unknown')]


def anonymize_by_translations(text, translations):
    for translation in translations:
        text = text.replace(translation[0], translation[1])
    return text


def anonymize_json_compute_engine(root):
    kind = get_item_kind(root)

    if kind == ItemKind.INSTANCE_LIST:
        for item in root.get('items', []):
            anonymize_instance(item)
    elif kind == ItemKind.INSTANCE:
        anonymize_instance(root)
    elif kind == ItemKind.OPERATION:
        root['user'] = 'anonymous.user@anonymo.us'


def anonymize_json_jenkins(root):
    class_ = get_item_class(root)

    if class_ == ItemClass.QUEUE:
        anonymize_jenkins_queue(root)


def anonymize_json(root, api_type):
    if api_type == ApiType.GOOGLE_COMPUTE_ENGINE:
        return anonymize_json_compute_engine(root)
    if api_type == ApiType.JENKINS:
        return anonymize_json_jenkins(root)
    raise ValueError('Api Type cannot be deduced!')


def get_indent(api_type):
    if api_type == ApiType.GOOGLE_COMPUTE_ENGINE:
        return 1
    if api_type == ApiType.JENKINS:
        return 2
    return 4


def anonymize(filepath, translations=None):
    """Anonymizes a json file.

    Will perform the following operations:

        * If it's a Google Compute response:
            * for each tuple in `translations`, replace any occurrence of the first member by the second member
            * randomizes natIP (at $.items[*].networkInterfaces[*].accessConfigs[*].natIP )
            * replaces any email (at $.items[*].serviceAccounts[*].email ) by a fake one
            * Removes any windows-key that would be present (at $.items[*].metadata.items[?(@.key == "windows-keys")] )
        * If it's a Jenkins API response:
            *

    Please note: the file in `filepath` will be changed inplace!

    :param str filepath: Path to the file to anonymize.
    :param list(tuple) translations: List of translation table to be done
    """
    with open(filepath, 'r') as f:
        out = f.read()

    if translations is None:
        translations = []
    out = anonymize_by_translations(text=out, translations=translations)

    json_out = json.loads(out, object_pairs_hook=collections.OrderedDict)
    api_type = get_api_type(json_out)
    anonymize_json(json_out, api_type)

    with open(filepath, 'w') as f:
        json.dump(json_out, f, indent=get_indent(api_type), separators=(',', ': '))
