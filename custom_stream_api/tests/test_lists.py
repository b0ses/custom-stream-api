import pytest

from custom_stream_api.shared import db
from custom_stream_api.lists import lists
from custom_stream_api.lists.models import ListItem

from custom_stream_api.tests.factories.lists_factories import ListFactory, ListItemFactory

TEST_LISTS_DICTS = []


@pytest.fixture(scope="function")
def import_lists(session):
    global TEST_LISTS_DICTS

    session.query(ListItemFactory._meta.model).delete()
    session.query(ListFactory._meta.model).delete()
    session.commit()

    TEST_LISTS = [
        ListFactory(
            name="list1",
        ),
        ListFactory(
            name="list2",
        ),
    ]
    start = ListItemFactory(list_name="list1", item="one")
    TEST_LIST_ITEMS = [
        start,
        ListItemFactory(id=start.id + 1, list_name="list1", item="two"),
        ListItemFactory(id=start.id + 2, list_name="list1", item="three"),
        ListItemFactory(id=start.id + 3, list_name="list2", item="four"),
        ListItemFactory(id=start.id + 4, list_name="list2", item="five"),
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
    assert (lists.get_list_item("list1", 2)[0].item, lists.get_list_item("list1", 2)[1]) == ("two", 2)
    assert (lists.get_list_item("list1", -1)[0].item, lists.get_list_item("list1", -1)[1]) == ("three", 3)
    assert lists.get_list_item("list1")[0].item in ["one", "two", "three"]
    with pytest.raises(Exception, match="Index too high"):
        lists.get_list_item("list1", 4)


def test_get_list_size(import_lists):
    assert lists.get_list_size("list1") == 3


def test_remove_from_list(import_lists):
    removed, index = lists.remove_from_list("list2", 1)
    assert removed == "four"
    assert index == 1
    assert lists.get_list("list2") == ["five"]

    with pytest.raises(Exception, match="Lists are 1-indexed."):
        lists.remove_from_list("list2", 0)

    # make sure the indexes are reset
    list_item = db.session.query(ListItem).filter_by(list_name="list2").order_by(ListItem.id.desc()).first()
    assert list_item.item == "five"


def test_remove_list(import_lists):
    with pytest.raises(Exception, match="List not found"):
        lists.remove_list("list3")
    assert lists.list_lists() == TEST_LISTS_DICTS
