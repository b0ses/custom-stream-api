from flask import Blueprint, request
from flask import jsonify
from custom_stream_api.alerts import alerts
from custom_stream_api.shared import InvalidUsage

alert_endpoints = Blueprint('alerts', __name__)


@alert_endpoints.route('/alert', methods=['POST'])
def alert_post():
    if request.method == 'POST':
        data = request.get_json()
        alert_data = {
            'name': data.get('name'),
            'text': data.get('text'),
            'sound': data.get('sound'),
            'effect': data.get('effect'),
            'duration': data.get('duration')
        }
        try:
            alerts.alert(**alert_data)
            return jsonify({'message': 'Displayed alert'})
        except Exception as e:
            raise InvalidUsage(str(e))


@alert_endpoints.route('/', methods=['GET'])
def list_alerts_get():
    all_alerts = [alert.as_dict() for alert in alerts.list_alerts()]
    return jsonify(all_alerts)


@alert_endpoints.route('/add_alert', methods=['POST'])
def add_alert_post():
    if request.method == 'POST':
        data = request.get_json()
        add_alert_data = {
            'name': data.get('name'),
            'text': data.get('text'),
            'sound': data.get('sound'),
            'duration': data.get('duration'),
            'effect': data.get('effect')
        }
        try:
            alert_name = alerts.add_alert(**add_alert_data)
        except Exception as e:
            raise InvalidUsage(str(e))
        return jsonify({'message': 'Alert in database: {}'.format(alert_name)})


@alert_endpoints.route('/remove_alert', methods=['POST'])
def remove_alert_post():
    if request.method == 'POST':
        data = request.get_json()
        remove_alert_data = {
            'name': data.get('name'),
        }
        try:
            alert_name = alerts.remove_alert(**remove_alert_data)
        except Exception as e:
            raise InvalidUsage(str(e))
        return jsonify({'message': 'Alert removed: {}'.format(alert_name)})
