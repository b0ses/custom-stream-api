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
            'name': data.get('name', ''),
            'text': data.get('text', ''),
            'sound': data.get('sound', ''),
            'duration': data.get('duration', 3000),
            'effect': data.get('effect', '')
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
            'name': data.get('name', ''),
            'text': data.get('text', ''),
            'sound': data.get('sound', ''),
            'duration': data.get('duration', 3000),
            'effect': data.get('effect', '')
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


@alert_endpoints.route('/group_alert', methods=['POST'])
def group_alert_post():
    if request.method == 'POST':
        data = request.get_json()
        alert_data = {
            'group_name': data.get('group_name', '')
        }
        try:
            alerts.random_alert(**alert_data)
            return jsonify({'message': 'Displayed alert'})
        except Exception as e:
            raise InvalidUsage(str(e))


@alert_endpoints.route('/groups', methods=['GET'])
def list_groups_get():
    return jsonify(alerts.list_groups())


@alert_endpoints.route('/add_to_group', methods=['POST'])
def add_to_group_post():
    if request.method == 'POST':
        data = request.get_json()
        add_to_group_data = {
            'group_name': data.get('group_name'),
            'alert_names': data.get('alert_names')
        }
        try:
            alert_names = alerts.add_to_group(**add_to_group_data)
        except Exception as e:
            raise InvalidUsage(str(e))
        return jsonify({'message': 'Added to {}: {}'.format(data.get('group_name'), alert_names)})


@alert_endpoints.route('/remove_from_group', methods=['POST'])
def remove_from_group_post():
    if request.method == 'POST':
        data = request.get_json()
        remove_from_group_data = {
            'group_name': data.get('group_name'),
            'alert_names': data.get('alert_names')
        }
        try:
            alert_names = alerts.remove_from_group(**remove_from_group_data)
        except Exception as e:
            raise InvalidUsage(str(e))
        return jsonify({'message': 'Removed from {}: {}'.format(data.get('group_name'), alert_names)})


@alert_endpoints.route('/remove_group', methods=['POST'])
def remove_group_post():
    if request.method == 'POST':
        data = request.get_json()
        remove_group_data = {
            'group_name': data.get('group_name'),
        }
        try:
            group_name = alerts.remove_group(**remove_group_data)
        except Exception as e:
            raise InvalidUsage(str(e))
        return jsonify({'message': 'Group removed: {}'.format(group_name)})
