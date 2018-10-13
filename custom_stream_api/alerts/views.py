import json
from flask import Blueprint, request
from custom_stream_api.alerts import alerts

alert_endpoints = Blueprint('alerts', __name__)


@alert_endpoints.route('/alert', methods=['POST'])
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
        success = alerts.alert(**alert_data)
        if not success:
            return 'Alert not found: {}'.format(data.get('name'))
        else:
            return 'Displaying alert'


@alert_endpoints.route('/', methods=['GET'])
def list_alerts_get():
    all_alerts = [alert.as_dict() for alert in alerts.list_alerts()]
    return json.dumps(all_alerts)


@alert_endpoints.route('/add_alert', methods=['POST'])
def add_alert_post():
    if request.method == 'POST':
        data = request.get_json()
        add_alert_data = {
            'name': data.get('name'),
            'message': data.get('message'),
            'sound': data.get('sound')
        }
        alert_name = alerts.add_alert(**add_alert_data)
        return 'Alert in database: {}'.format(alert_name)


@alert_endpoints.route('/remove_alert', methods=['POST'])
def remove_alert_post():
    if request.method == 'POST':
        data = request.get_json()
        remove_alert_data = {
            'name': data.get('name'),
        }
        alert_name = alerts.remove_alert(**remove_alert_data)
        if alert_name:
            return 'Alert removed: {}'.format(alert_name)
        else:
            return 'Alert not found: {}'.format(data.get('name'))
