import pytest

from custom_stream_api.shared import db
from custom_stream_api.lists import lists
from custom_stream_api.lists.models import ListItem

LISTS_IMPORT = [
    {
        'name': 'list1',
        'items': [
            'one',
            'two',
            'three'
        ]
    },
    {
        'name': 'list2',
        'items': [
            'four',
            'five'
        ]
    }
]


@pytest.fixture
def import_lists(app):
    lists.import_lists(LISTS_IMPORT)


def test_import_export(import_lists):
    assert lists.list_lists() == LISTS_IMPORT


def test_set_list(import_lists):
    lists.set_list('list3', ['six', 'seven'])
    assert lists.get_list('list3') == ['six', 'seven']


def test_get_list_item(import_lists):
    assert lists.get_list_item('list1', 1) == ('two', 1)
    assert lists.get_list_item('list1')[0] in ['one', 'two', 'three']
    assert lists.get_list_item('list1', 3) == (None, None)


def test_get_list_size(import_lists):
    assert lists.get_list_size('list1') == 3


def test_remove_from_list(import_lists):
    removed = lists.remove_from_list('list2', 0)
    expected_removed = 'four'
    assert removed == expected_removed
    assert lists.get_list('list2') == ['five']

    # make sure the indexes are reset
    list_item = db.session.query(ListItem).filter_by(list_name='list2', index=0).first()
    assert list_item.item == 'five'


def test_remove_list(import_lists):
    lists.remove_list('list3')
    assert lists.list_lists() == LISTS_IMPORT
