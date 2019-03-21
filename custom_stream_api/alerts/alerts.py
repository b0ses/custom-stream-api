import re
import random

from custom_stream_api.alerts.models import Alert, GroupAlert, GroupAlertAssociation
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
            raise Exception('Invalid image url: {}'.format(image))
        else:
            return matches[0][4]  # using the regex, this'll return the filename sans extension


def validate_color_hex(color_hex):
    if color_hex:
        matches = re.findall(HEX_CODE_REGEX, color_hex)
        if not matches:
            raise Exception('Invalid color hex: {}'.format(color_hex))
        else:
            return color_hex


def validate_thumbnail(thumbnail):
    if thumbnail:
        if thumbnail[0] == '#':
            validate_color_hex(thumbnail)
        elif thumbnail[:4] == 'http':
            validate_image(thumbnail)
        else:
            raise Exception('Invalid thumbnail: {}'.format(thumbnail))
    return thumbnail


def generate_name(name='', text='', sound='', image=''):
    generated_name = name
    if not generated_name and text:
        generated_name = text
    elif not generated_name and sound:
        generated_name = validate_sound(sound)
    elif not generated_name and image:
        generated_name = validate_image(image)
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
        validate_image(image)
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
    return [alert.as_dict() for alert in db.session.query(Alert).order_by(Alert.name.asc()).all()]


def import_alerts(alerts):
    for alert_data in alerts:
        add_alert(**alert_data, save=False)
    db.session.commit()


def add_alert(name='', text='', sound='', duration=3000, effect='', image='', thumbnail='', save=True):
    generated_name = generate_name(name, text, sound)
    validate_sound(sound)
    effect = validate_effect(effect)
    duration = validate_duration(duration)
    validate_image(image)
    thumbnail = validate_thumbnail(thumbnail)

    found_alert = db.session.query(Alert).filter_by(name=generated_name).one_or_none()
    if found_alert:
        found_alert.name = generated_name
        found_alert.text = text
        found_alert.sound = sound
        found_alert.duration = duration
        found_alert.thumbnail = thumbnail
        found_alert.image = image
        found_alert.effect = effect
    else:
        new_alert = Alert(name=generated_name, text=text, sound=sound, duration=duration, effect=effect, image=image,
                          thumbnail=thumbnail)
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

def group_alert(group_name, random_choice=True):
    group_alert = db.session.query(GroupAlert).filter_by(group_name=group_name).one_or_none()
    if not group_alert:
        raise Exception('Group not found: {}'.format(group_name))
    group_alerts = [result.alert_name for result in group_alert.alerts]
    if random_choice:
        chosen_alert = random.choice(group_alerts)
    else:
        chosen_alert = group_alerts[group_alert.current_index]
        group_alert.current_index = (group_alert.current_index + 1) % len(group_alerts)
        db.session.commit()

    return alert(chosen_alert)


def list_groups():
    # {'group_name': ['alert_name1', 'alert_name2', ...]}
    groups = {}
    group_alerts = list(db.session.query(GroupAlert).all())
    for group_alert in group_alerts:
        alerts = sorted(group_alert.alerts, key=lambda group_alert: group_alert.index)
        alerts = [alert.alert_name for alert in alerts]
        groups[group_alert.group_name] = {
            'name': group_alert.group_name,
            'alerts': alerts,
            'thumbnail': group_alert.thumbnail
        }
    listed_groups = list(groups.values())
    return sorted(listed_groups, key=lambda group: group['name'])


def import_groups(groups):
    for group_data in groups:
        alerts = group_data['alerts']
        name = group_data['name']
        thumbnail = group_data.get('thumbnail', '')
        set_group(name, alerts, thumbnail=thumbnail, save=False)
    db.session.commit()


def set_group(group_name, alert_names, thumbnail='', save=True):
    thumbnail = validate_thumbnail(thumbnail)
    group_alert = GroupAlert.query.filter_by(group_name=group_name).one_or_none()
    if group_alert:
        group_alert.thumbnail = thumbnail
        for alert in group_alert.alerts:
            db.session.delete(alert)
    else:
        group_alert = GroupAlert(group_name=group_name, thumbnail=thumbnail)
        db.session.add(group_alert)

    if save:
        db.session.commit()

    return add_to_group(group_name, alert_names, save=save)


def add_to_group(group_name, alert_names, save=True):
    new_alerts = []

    group_alert = GroupAlert.query.filter_by(group_name=group_name).one_or_none()
    if not group_alert:
        group_alert = GroupAlert(group_name=group_name)
        db.session.add(group_alert)

    index = GroupAlertAssociation.query.filter_by(group_name=group_name).count()
    for alert_name in alert_names:
        alert = db.session.query(Alert).filter_by(name=alert_name)
        if not alert.count():
            raise Exception('Alert not found: {}'.format(alert_name))

        if not GroupAlertAssociation.query.filter_by(group_name=group_name, alert_name=alert_name).count():
            new_alerts.append(alert_name)
            new_association = GroupAlertAssociation(group_name=group_alert.group_name, alert_name=alert_name,
                                                    index=index)
            db.session.add(new_association)
            index += 1
    if save:
        db.session.commit()
    return new_alerts


def remove_from_group(group_name, alert_names):
    group_alert = db.session.query(GroupAlert).filter_by(group_name=group_name).one_or_none()
    if not group_alert:
        raise Exception('Group not found: {}'.format(group_name))

    for alert_name in alert_names:
        alert = Alert.query.filter_by(name=alert_name)
        if not alert.count():
            raise Exception('Alert not found: {}'.format(alert_name))

    alerts = [alert for alert in group_alert.alerts if alert.alert_name in alert_names]
    removed_alerts = [alert.alert_name for alert in alerts]
    for alert in alerts:
        db.session.delete(alert)

    db.session.commit()
    return removed_alerts


def remove_group(group_name):
    group = db.session.query(GroupAlert).filter_by(group_name=group_name).one_or_none()
    if group:
        for alert in group.alerts:
            db.session.delete(alert)
        db.session.delete(group)
        db.session.commit()
        return group_name
    else:
        raise Exception('Group not found: {}'.format(group_name))
