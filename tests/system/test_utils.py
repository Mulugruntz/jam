import pytest

import jam.libs
import jam.libs.utils


@pytest.mark.parametrize(['dicts', 'expected_dict'], [
    pytest.param(
        [{'a': 4, 'b': 8}],
        {'a': 4, 'b': 8},
        id='One dict',
    ),
    pytest.param(
        [{'a': 4, 'b': 8}, {'c': 15, 'd': 16}],
        {'a': 4, 'b': 8, 'c': 15, 'd': 16},
        id='Two dicts',
    ),
    pytest.param(
        [{'a': 4, 'b': 8}, {'c': 15, 'd': 16}, {'e': 23, 'f': 42}],
        {'a': 4, 'b': 8, 'c': 15, 'd': 16, 'e': 23, 'f': 42},
        id='Three dicts',
    ),
    pytest.param(
        [{'a': 4, 'b': 100}, {'b': 8, 'c': 15}],
        {'a': 4, 'b': 8, 'c': 15},
        id='Two intersected dicts',
    ),
    pytest.param(
        [{'a': 4, 'b': 8}, {'c': 15, 'd': 16}],
        {'a': 4, 'b': 8, 'c': 15, 'd': 16},
        id='Two disjoint dicts',
    ),
])
def test_merge_dicts(dicts, expected_dict):
    assert jam.libs.utils.merge_dicts(*dicts) == expected_dict
