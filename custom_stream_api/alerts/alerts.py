import re

from custom_stream_api.alerts.models import Alert
from custom_stream_api.shared import db, socketio

VALID_SOUNDS = ['wav', 'mp3']
SOUND_REGEX = '^(http[s]?):\/?\/?([^:\/\s]+)((\/\w+)*\/)([\w\-\.]+)\.({})$'.format('|'.join(VALID_SOUNDS))
VALID_EFFECTS = ['', 'fade']


def validate_sound(sound=''):
    if sound:
        matches = re.findall(SOUND_REGEX, sound)
        if not matches:
            raise Exception('Invalid sound url: {}'.format(sound))
        else:
            return matches[0][4]  # using the regex, this'll return the filename sans extension


def validate_effect(effect=''):
    if effect in VALID_EFFECTS:
        return effect
    else:
        raise Exception('Invalid effect: {}'.format(effect))


def validate_duration(duration=3000):
    if not str(duration).isdigit():
        raise Exception('Invalid duration: {}'.format(duration))
    return int(duration)


def generate_name(name='', message='', sound=''):
    generated_name = name
    if not generated_name and message:
        generated_name = message
    elif not generated_name and sound:
        generated_name = validate_sound(sound)
    elif not generated_name:
        raise Exception('Can\'t generate blank alert name.')

    return generated_name.strip().lower().replace(' ', '_')


def alert(name='', message='', sound='', effect='', duration=3000):
    if not name:
        alert_obj = Alert.query.filter_by(name=name).one_or_none()
        if not alert_obj:
            raise Exception('Alert not found: {}'.format(name))
        socket_data = alert_obj.as_dict()
    else:
        validate_sound(sound)
        socket_data = {
            'message': message,
            'sound': sound
        }
    effect = validate_effect(effect)
    duration = validate_duration(duration)
    socket_data.update({
        'effect': effect,
        'duration': duration
    })
    socketio.emit('FromAPI', socket_data, namespace='/', broadcast=True)


def list_alerts():
    return list(Alert.query.order_by(Alert.name.asc()).all())


def add_alert(name='', message='', sound=''):
    generated_name = generate_name(name, message, sound)
    found_alert = Alert.query.filter_by(name=generated_name).one_or_none()
    if found_alert:
        return found_alert.name
    else:
        validate_sound(sound)
        new_alert = Alert(name=generated_name, text=message, sound=sound)
        db.session.add(new_alert)
        db.session.commit()
        return new_alert.name


def remove_alert(name):
    alert = Alert.query.filter_by(name=name)
    if alert.count():
        alert_name = alert.one_or_none().name
        alert.delete()
        db.session.commit()
        return alert_name
    else:
        raise Exception('Alert not found: {}'.format(name))
