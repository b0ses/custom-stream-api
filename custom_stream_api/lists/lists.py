import random

from custom_stream_api.lists.models import List, ListItem
from custom_stream_api.shared import db


def import_lists(import_lists):
    for list_dict in import_lists:
        set_list(list_dict["name"], list_dict["items"], save=False)
    db.session.commit()


def set_list(name, items, save=True):
    found_list = db.session.query(List).filter_by(name=name).one_or_none()
    if not found_list:
        found_list = List(name=name, current_index=0)
        db.session.add(found_list)
    else:
        for item in found_list.items:
            db.session.delete(item)
    if save:
        db.session.commit()
    return add_to_list(name, items, save=save)


def add_to_list(name, items, save=True):
    new_items = []

    found_list = db.session.query(List).filter_by(name=name).one_or_none()
    if not found_list:
        found_list = List(name=name)
        db.session.add(found_list)

    for item in items:
        new_items.append(item)
        new_item = ListItem(list_name=name, item=item)
        db.session.add(new_item)
    if save:
        db.session.commit()
    return items


def list_lists():
    list_query = db.session.query(List)
    return [list_obj.as_dict() for list_obj in list_query.order_by(List.name.asc())]


def get_list(name):
    list_query = db.session.query(List).filter(List.name == name).first()
    if list_query:
        return list(list_query.as_dict()["items"])
    else:
        return []


def represents_int(s):
    try:
        int(s)
    except ValueError:
        return False
    else:
        return True


def get_list_item(list_name, index):
    """Index is 1-indexed, string random or next"""
    found_list = db.session.query(List).filter_by(name=list_name).one_or_none()
    if not found_list:
        raise Exception("List not found")
    if len(found_list.items) == 0:
        raise Exception("Empty list")
    items = sorted(found_list.items, key=lambda list_item: list_item.id)

    if index is None:
        raise Exception("index not provided")
    elif isinstance(index, int) or (isinstance(index, str) and represents_int(index)):
        index = int(index)
        if index > len(items):
            raise Exception("Index too high")
        elif index == 0:
            raise Exception("Lists are 1-indexed.")
    elif isinstance(index, str) and index.lower() == "random":
        index = random.choice(range(1, len(items) + 1))
    elif isinstance(index, str) and index.lower() == "next":
        # current_index is 0-indexed, adding 1 to be in sync with the rest
        index = (found_list.current_index + 1) % len(items)
        found_list.current_index = index
        index += 1
    else:
        raise Exception("Invalid index. Must be a non-zero integer, 'random', or 'next'")

        # Negative nonzero indexes are already 1-indexed
        # Positive non-zero indexes need correction
    if index > 0:
        index = index - 1

    # Need to return the index too as it could be random
    return items[index], index + 1 if index >= 0 else len(items) + index + 1


def get_list_size(list_name):
    found_list = db.session.query(List).filter_by(name=list_name).one_or_none()
    if not found_list:
        raise Exception("List not found")
    return len(found_list.items)


def remove_from_list(list_name, index):
    """Index is 1-indexed"""
    if not isinstance(index, int):
        if not represents_int(index):
            raise Exception("Invalid index")
        index = int(index)

    found_list = db.session.query(List).filter_by(name=list_name).one_or_none()
    if not found_list:
        raise Exception("List not found")

    found_list_item, index = get_list_item(list_name, index)
    found_list_item_value = found_list_item.item
    db.session.delete(found_list_item)
    # current_index is 0-indexed
    if index - 1 <= found_list.current_index:
        found_list.current_index -= 1
    db.session.commit()

    return found_list_item_value, index


def remove_list(name):
    found_list = db.session.query(List).filter_by(name=name)
    if not found_list.count():
        raise Exception("List not found")
    found_list.delete()
    db.session.commit()
    return name
