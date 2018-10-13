import logging
import json
from flask import Flask, request
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_migrate import Migrate

from custom_stream_api.models import db, Alert
from custom_stream_api import settings

app = Flask(__name__)
CORS(app, resources={r'/*': {'origins': '*'}})
logger = logging.getLogger()

app.config['SECRET_KEY'] = settings.SECRET
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
socketio = SocketIO(app)
db.init_app(app)
migrate = Migrate(app, db)


def clean_name(name):
    return name.lower().replace(' ', '_')


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
    return list(Alert.query.all())


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


@app.route('/alert', methods=['POST'])
def alert_post():
    if request.method == 'POST':
        data = request.get_json()
        alert_data = {
            'name': data.get('name'),
            'message': data.get('message'),
            'sound': data.get('sound'),
            'effect': data.get('effect'),
            'duration': data.get('duration')
        }
        success = alert(**alert_data)
        if not success:
            return 'Alert not found: {}'.format(data.get('name'))
        else:
            return 'Displaying alert'


@app.route('/alerts', methods=['GET'])
def list_alerts_get():
    alerts = [alert.as_dict() for alert in list_alerts()]
    return json.dumps(alerts)


@app.route('/add_alert', methods=['POST'])
def add_alert_post():
    if request.method == 'POST':
        data = request.get_json()
        add_alert_data = {
            'name': data.get('name'),
            'message': data.get('message'),
            'sound': data.get('sound')
        }
        alert_name = add_alert(**add_alert_data)
        return 'Alert in database: {}'.format(alert_name)


@app.route('/remove_alert', methods=['POST'])
def remove_alert_post():
    if request.method == 'POST':
        data = request.get_json()
        remove_alert_data = {
            'name': data.get('name'),
        }
        alert_name = remove_alert(**remove_alert_data)
        if alert_name:
            return 'Alert removed: {}'.format(alert_name)
        else:
            return 'Alert not found: {}'.format(data.get('name'))


if __name__ == '__main__':
    if not settings.SECRET:
        logger.error('Go to settings and fill in the SECRET with something.')
        exit()
    socketio.run(app, host=settings.HOST, port=settings.PORT)
