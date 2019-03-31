from custom_stream_api.counts.models import Count
from custom_stream_api.shared import db


def list_counts():
    return [count.as_dict() for count in db.session.query(Count).order_by(Count.name.asc()).all()]


def import_counts(import_counts):
    for count_dict in import_counts:
        set_count(count_dict['name'], count_dict['count'], save=False)
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


def set_count(name, count, save=True):
    count_obj = db.session.query(Count).filter(Count.name == name).one_or_none()
    if not count_obj:
        count_obj = Count(name=name, count=0)
        db.session.add(count_obj)
    count_obj.count = count
    if save:
        db.session.commit()
    return count_obj.count


def remove_count(name):
    found_count = db.session.query(Count).filter_by(name=name)
    if found_count.count():
        found_count.delete()
        db.session.commit()
        return found_count
