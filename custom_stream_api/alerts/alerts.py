import re
import random

from custom_stream_api.alerts.models import Alert, GroupAlertAssociation
from custom_stream_api.shared import db, socketio

VALID_SOUNDS = ['wav', 'mp3', 'ogg']
VALID_IMAGES = ['jpg', 'png', 'tif', 'gif']
URL_REGEX = '^(http[s]?):\/?\/?([^:\/\s]+)((\/.+)*\/)(.+)\.({})$'
SOUND_REGEX = URL_REGEX.format('|'.join(VALID_SOUNDS))
IMAGE_REXEX = URL_REGEX.format('|'.join(VALID_IMAGES))
HEX_CODE_REGEX = '^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'
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


def validate_image(image=''):
    if image:
        matches = re.findall(IMAGE_REXEX, image)
        if not matches:
            raise Exception('Invalid sound url: {}'.format(image))
        else:
            return matches[0][4]  # using the regex, this'll return the filename sans extension


def validate_color_hex(color_hex):
    if color_hex:
        matches = re.findall(HEX_CODE_REGEX, color_hex)
        if not matches:
            raise Exception('Invalid sound url: {}'.format(image))
        else:
            return color_hex


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

def alert(name='', text='', sound='', effect='', duration=3000, image=''):
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
            'image': image,
            'duration': duration
        }
    socketio.emit('FromAPI', socket_data, namespace='/', broadcast=True)
    return socket_data['text']


def list_alerts():
    return list(db.session.query(Alert).order_by(Alert.name.asc()).all())


def import_alerts(alerts):
    for alert_data in alerts:
        add_alert(**alert_data, save=False)
    db.session.commit()


def add_alert(name='', text='', sound='', duration=3000, effect='', image='', thumbnail='', save=True):
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
        found_alert.thumbnail = thumbnail
        found_alert.image = image
        found_alert.effect = effect
    else:
        new_alert = Alert(name=generated_name, text=text, sound=sound, duration=duration, effect=effect, image=image, thumbnail=thumbnail)
        db.session.add(new_alert)
    if save:
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
    group = [result[0] for result in db.session.query(GroupAlertAssociation.alert_name).filter_by(group_name=group_name)]
    r_alert = random.choice(group)
    return alert(r_alert)


def linked_alert(group_name, index=0):
    group = [result[0] for result in db.session.query(GroupAlertAssociation.alert_name).filter_by(group_name=group_name).order_by(GroupAlertAssociation.index)]
    l_alert = group[index]
    return alert(l_alert)


def list_groups():
    # {'group_name': ['alert_name1', 'alert_name2', ...]}
    all_associations = list(db.session.query(GroupAlertAssociation).order_by(GroupAlertAssociation.group_name, GroupAlertAssociation.index).all())
    groups = {}
    for assocation in all_associations:
        group_name = assocation.group_name
        alert_name = assocation.alert_name
        if group_name in groups:
            groups[group_name].append(alert_name)
        else:
            groups[group_name] = [alert_name]
    listed_groups = [{'name': group_name, 'alerts': alerts} for group_name, alerts in groups.items()]
    return sorted(listed_groups, key=lambda group: group['name'])


def import_groups(groups):
    for group_data in groups:
        alerts = group_data['alerts']
        name = group_data['name']
        replace_group(name, alerts, save=False)
    db.session.commit()


def replace_group(group_name, alert_names, save=True):
    # clear out group first
    found_group = GroupAlertAssociation.query.filter_by(group_name=group_name)
    if found_group.count():
        found_group.delete()

    return add_to_group(group_name, alert_names, save=save)


def add_to_group(group_name, alert_names, save=True):
    new_alerts = []

    index = GroupAlertAssociation.query.filter_by(group_name=group_name).count()
    for alert_name in alert_names:
        alert = db.session.query(Alert).filter_by(name=alert_name)
        if not alert.count():
            raise Exception('Alert not found: {}'.format(alert_name))

        if not GroupAlertAssociation.query.filter_by(group_name=group_name, alert_name=alert_name).count():
            new_alerts.append(alert_name)
            new_association = GroupAlertAssociation(group_name=group_name, alert_name=alert_name, index=index)
            db.session.add(new_association)
            index += 1
    if save:
        db.session.commit()
    return new_alerts


def remove_from_group(group_name, alert_names):
    removed_alerts = []
    group = db.session.query(GroupAlertAssociation).filter_by(group_name=group_name)
    if not group.count():
        raise Exception('Group not found: {}'.format(group_name))

    for alert_name in alert_names:
        alert = Alert.query.filter_by(name=alert_name)
        if not alert.count():
            raise Exception('Alert not found: {}'.format(alert_name))

        association = db.session.query(GroupAlertAssociation).filter_by(group_name=group_name, alert_name=alert_name)
        if association.count():
            removed_alerts.append(alert_name)
            association.delete()
    db.session.commit()
    return removed_alerts


def remove_group(group_name):
    group = db.session.query(GroupAlertAssociation).filter_by(group_name=group_name)
    if group.count():
        group.delete()
        db.session.commit()
        return group_name
    else:
        raise Exception('Group not found: {}'.format(group_name))
