import random

from custom_stream_api.lists.models import List, ListItem
from custom_stream_api.shared import db


def import_lists(import_lists):
    for list_dict in import_lists:
        set_list(list_dict['name'], list_dict['items'], save=False)
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

    found_list = List.query.filter_by(name=name).one_or_none()
    if not found_list:
        found_list = List(name=name)
        db.session.add(found_list)

    index = ListItem.query.filter_by(list_name=name).count()
    for item in items:
        new_items.append(item)
        new_item = ListItem(list_name=name, item=item, index=index)
        db.session.add(new_item)
        index += 1
    if save:
        db.session.commit()
    return items


def list_lists(specific_list=None):
    list_query = db.session.query(List)
    if specific_list:
        list_query = list_query.filter(List.name == specific_list)
    return [list_obj.as_dict() for list_obj in list_query.order_by(List.name.asc())]


def get_list_item(name, item_index=None):
    found_list = db.session.query(List).filter_by(name=name).one_or_none()
    if not found_list:
        return
    items = found_list.items
    if not item_index:
        item_index = random.choice(range(0, len(items)))
    else:
        if not isinstance(item_index, int):
            if not item_index.isdigit():
                return
            item_index = int(item_index)
        if item_index > len(items):
            return
    return items[item_index].item


def remove_from_list(name, index):
    found_list_item = db.session.query(ListItem).filter(ListItem.list_name == name, ListItem.index >= index).\
        order_by(ListItem.index.asc())
    if not found_list_item.count():
        return
    db.session.delete(found_list_item.first())

    # reset indexes
    new_index = index
    for list_item in found_list_item.all():
        list_item.index = new_index
        new_index += 1

    db.session.commit()

    return found_list_item


def remove_list(list_name):
    found_list = db.session.query(List).filter_by(name=list_name)
    if found_list.count():
        found_list.delete()
        db.session.commit()
        return list_name
