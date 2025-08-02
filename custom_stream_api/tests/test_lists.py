import pytest

from custom_stream_api.shared import db
from custom_stream_api.lists import lists
from custom_stream_api.lists.models import ListItem

from custom_stream_api.tests.factories.lists_factories import ListFactory, ListItemFactory

TEST_LISTS_DICTS = []


@pytest.fixture(scope="function")
def import_lists(session):
    global TEST_LISTS_DICTS

    TEST_LISTS = [
        ListFactory(
            name="list1",
        ),
        ListFactory(
            name="list2",
        ),
    ]
    TEST_LIST_ITEMS = [
        ListItemFactory(list_name="list1", index=0, item="one"),
        ListItemFactory(list_name="list1", index=1, item="two"),
        ListItemFactory(list_name="list1", index=2, item="three"),
        ListItemFactory(list_name="list2", index=0, item="four"),
        ListItemFactory(list_name="list2", index=1, item="five"),
    ]

    session.add_all(TEST_LISTS)
    session.add_all(TEST_LIST_ITEMS)
    session.commit()

    TEST_LISTS_DICTS = [test_list.as_dict() for test_list in TEST_LISTS]

    yield session

    session.query(ListItemFactory._meta.model).delete()
    session.query(ListFactory._meta.model).delete()
    session.commit()


def test_import_export(import_lists):
    assert lists.list_lists() == TEST_LISTS_DICTS


def test_set_list(import_lists):
    lists.set_list("list3", ["six", "seven"])
    assert lists.get_list("list3") == ["six", "seven"]


def test_get_list_item(import_lists):
    assert lists.get_list_item("list1", 1) == ("two", 1)
    assert lists.get_list_item("list1")[0] in ["one", "two", "three"]
    assert lists.get_list_item("list1", 3) == (None, None)


def test_get_list_size(import_lists):
    assert lists.get_list_size("list1") == 3


def test_remove_from_list(import_lists):
    removed = lists.remove_from_list("list2", 0)
    expected_removed = "four"
    assert removed == expected_removed
    assert lists.get_list("list2") == ["five"]

    # make sure the indexes are reset
    list_item = db.session.query(ListItem).filter_by(list_name="list2", index=0).first()
    assert list_item.item == "five"


def test_remove_list(import_lists):
    lists.remove_list("list3")
    assert lists.list_lists() == TEST_LISTS_DICTS
