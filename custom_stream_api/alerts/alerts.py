from custom_stream_api.alerts.models import Alert
from custom_stream_api.shared import db, socketio


def clean_name(name):
    return name.strip().lower().replace(' ', '_')


def alert(name=None, message='', sound='', effect='', duration=3000):
    if name is not None:
        alert_obj = Alert.query.filter_by(name=name).one_or_none()
        if not alert_obj:
            return False
        socket_data = alert_obj.as_dict()
    else:
        socket_data = {
            'message': message,
            'sound': sound
        }
    socket_data.update({
        'effect': effect,
        'duration': duration
    })
    socketio.emit('FromAPI', socket_data, namespace='/', broadcast=True)
    return True


def list_alerts():
    return list(Alert.query.order_by(Alert.name.asc()).all())


def add_alert(name='', message='', sound=''):
    if not name:
        name = message
    name = clean_name(name)
    found_alert = Alert.query.filter_by(name=name).one_or_none()
    if found_alert:
        return found_alert.name
    else:
        new_alert = Alert(name=name, text=message, sound=sound)
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
        return None
