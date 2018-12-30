import re
import random

from custom_stream_api.alerts.models import Alert, GroupAlert
from custom_stream_api.shared import db, socketio

VALID_SOUNDS = ['wav', 'mp3', 'ogg']
SOUND_REGEX = '^(http[s]?):\/?\/?([^:\/\s]+)((\/\w+)*\/)([\w\-\.]+)\.({})$'.format('|'.join(VALID_SOUNDS))
VALID_EFFECTS = ['', 'fade']


# HELPERS

def validate_sound(sound=''):
    if sound:
        matches = re.findall(SOUND_REGEX, sound)
        if not matches:
            raise Exception('Invalid sound url: {}'.format(sound))
        else:
            return matches[0][4]  # using the regex, this'll return the filename sans extension


def validate_effect(effect):
    effect = effect or ''
    if effect in VALID_EFFECTS:
        return effect
    else:
        raise Exception('Invalid effect: {}'.format(effect))


def validate_duration(duration):
    if not str(duration).isdigit():
        raise Exception('Invalid duration: {}'.format(duration))
    return int(duration)


def generate_name(name='', text='', sound=''):
    generated_name = name
    if not generated_name and text:
        generated_name = text
    elif not generated_name and sound:
        generated_name = validate_sound(sound)
    elif not generated_name:
        raise Exception('Can\'t generate blank alert name.')

    return generated_name.strip().lower().replace(' ', '_')


# ALERTS

def alert(name='', text='', sound='', effect='', duration=3000):
    if name:
        alert_obj = db.session.query(Alert).filter_by(name=name).one_or_none()
        if not alert_obj:
            raise Exception('Alert not found: {}'.format(name))
        socket_data = alert_obj.as_dict()
    else:
        validate_sound(sound)
        effect = validate_effect(effect)
        duration = validate_duration(duration)
        socket_data = {
            'text': text,
            'sound': sound,
            'effect': effect,
            'duration': duration
        }
    socketio.emit('FromAPI', socket_data, namespace='/', broadcast=True)


def list_alerts():
    return list(db.session.query(Alert).order_by(Alert.name.asc()).all())


def add_alert(name='', text='', sound='', duration=3000, effect=''):
    generated_name = generate_name(name, text, sound)
    validate_sound(sound)
    effect = validate_effect(effect)
    duration = validate_duration(duration)

    found_alert = Alert.query.filter_by(name=generated_name).one_or_none()
    if found_alert:
        found_alert.name = generated_name
        found_alert.text = text
        found_alert.sound = sound
        found_alert.duration = duration
        found_alert.effect = effect
    else:
        new_alert = Alert(name=generated_name, text=text, sound=sound, duration=duration, effect=effect)
        db.session.add(new_alert)
    db.session.commit()
    return generated_name


def remove_alert(name):
    alert = db.session.query(Alert).filter_by(name=name)
    if alert.count():
        alert_name = alert.one_or_none().name
        alert.delete()
        db.session.commit()
        return alert_name
    else:
        raise Exception('Alert not found: {}'.format(name))


# GROUPS

def random_alert(group_name):
    group = [result[0] for result in db.session.query(GroupAlert.alert_name).filter_by(group_name=group_name)]
    r_alert = random.choice(group)
    return alert(r_alert)


def list_groups():
    # {'group_name': ['alert_name1', 'alert_name2', ...]}
    all_associations = list(db.session.query(GroupAlert).all())
    groups = {}
    for assocation in all_associations:
        group_name = assocation.group_name
        alert_name = assocation.alert_name
        if group_name in groups:
            groups[group_name].append(alert_name)
        else:
            groups[group_name] = [alert_name]
    return groups


def add_to_group(group_name, alert_names):
    new_alerts = []
    for alert_name in alert_names:
        alert = db.session.query(Alert).filter_by(name=alert_name)
        if not alert.count():
            raise Exception('Alert not found: {}'.format(alert_name))

        if not GroupAlert.query.filter_by(group_name=group_name, alert_name=alert_name).count():
            new_alerts.append(alert_name)
            new_association = GroupAlert(group_name=group_name, alert_name=alert_name)
            db.session.add(new_association)
    db.session.commit()
    return new_alerts


def remove_from_group(group_name, alert_names):
    removed_alerts = []
    group = db.session.query(GroupAlert).filter_by(group_name=group_name)
    if not group.count():
        raise Exception('Group not found: {}'.format(group_name))

    for alert_name in alert_names:
        alert = Alert.query.filter_by(name=alert_name)
        if not alert.count():
            raise Exception('Alert not found: {}'.format(alert_name))

        association = db.session.query(GroupAlert).filter_by(group_name=group_name, alert_name=alert_name)
        if association.count():
            removed_alerts.append(alert_name)
            association.delete()
    db.session.commit()
    return removed_alerts


def remove_group(group_name):
    group = db.session.query(GroupAlert).filter_by(group_name=group_name)
    if group.count():
        group.delete()
        db.session.commit()
        return group_name
    else:
        raise Exception('Group not found: {}'.format(group_name))
