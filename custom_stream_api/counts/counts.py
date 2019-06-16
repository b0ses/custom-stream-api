from custom_stream_api.counts.models import Count
from custom_stream_api.alerts.models import GroupAlert
from custom_stream_api.shared import db


def list_counts():
    return [count.as_dict() for count in db.session.query(Count).order_by(Count.name.asc()).all()]


def import_counts(import_counts):
    for count_dict in import_counts:
        group_name = count_dict.get('group_name', '')
        set_count(count_dict['name'], count_dict['count'], group_name=group_name, save=False)
    db.session.commit()


def get_count(name):
    count_obj = db.session.query(Count).filter(Count.name == name).one_or_none()
    if count_obj:
        return count_obj.count


def add_to_count(name):
    count_obj = db.session.query(Count).filter(Count.name == name).one_or_none()
    if not count_obj:
        count_obj = Count(name=name, count=0)
        db.session.add(count_obj)
    count_obj.count += 1
    db.session.commit()
    return count_obj.count


def subtract_from_count(name):
    count_obj = db.session.query(Count).filter(Count.name == name).one_or_none()
    if not count_obj:
        count_obj = Count(name=name, count=0)
        db.session.add(count_obj)
    count_obj.count -= 1
    db.session.commit()
    return count_obj.count


def reset_count(name, save=True):
    return set_count(name, 0, save=save)


def set_count(name, count, group_name='', save=True):
    count_obj = db.session.query(Count).filter(Count.name == name).one_or_none()
    if not count_obj:
        count_obj = Count(name=name, count=0)
        db.session.add(count_obj)
    count_obj.count = count
    group_alert = db.session.query(GroupAlert).filter_by(group_name=group_name).one_or_none()
    if group_alert:
        count_obj.group_alert = group_alert

    if save:
        db.session.commit()
    return count_obj.count


def copy_count(count1, count2):
    count1_count = get_count(count1)
    if count1_count is not None:
        return set_count(count2, count1_count)
    else:
        raise Exception('{} doesn\'t exist.'.format(count1))


def remove_count(name):
    found_count = db.session.query(Count).filter_by(name=name)
    if found_count.count():
        found_count.delete()
        db.session.commit()
        return found_count
