from custom_stream_api.counts.models import Count
from custom_stream_api.alerts.models import Tag
from custom_stream_api.shared import db


def list_counts():
    return [count.as_dict() for count in db.session.query(Count).order_by(Count.name.asc()).all()]


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


def set_count(name, count, tag_name=None, save=True):
    count_obj = db.session.query(Count).filter(Count.name == name).one_or_none()
    if not count_obj:
        count_obj = Count(name=name, count=0)
        db.session.add(count_obj)
    count_obj.count = count

    tag = db.session.query(Tag).filter_by(name=tag_name).one_or_none()
    if tag:
        count_obj.tag_name = tag

    if save:
        db.session.commit()
    return count_obj.count


def copy_count(count1, count2):
    count1_count = get_count(count1)
    if count1_count is not None:
        return set_count(count2, count1_count)
    else:
        raise Exception("{} doesn't exist.".format(count1))


def remove_count(name):
    found_count = db.session.query(Count).filter_by(name=name)
    if found_count.count():
        found_count.delete()
        db.session.commit()
        return found_count
