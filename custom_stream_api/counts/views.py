from flask import Blueprint, request
from flask import jsonify

from custom_stream_api.counts import counts
from custom_stream_api.shared import InvalidUsage

counts_endpoints = Blueprint('counts', __name__)


@counts_endpoints.route('/', methods=['GET', 'POST'])
def list_counts_get():
    if request.method == 'GET':
        try:
            all_counts = counts.list_counts()
        except Exception as e:
            raise InvalidUsage(str(e))
        return jsonify(all_counts)
    else:
        data = request.get_json()
        try:
            counts.import_counts(data)
        except Exception as e:
            raise InvalidUsage(str(e))
        return jsonify({'message': 'Counts imported'})


@counts_endpoints.route('/count', methods=['POST'])
def get_count_post():
    if request.method == 'POST':
        data = request.get_json()
        count_data = {
            'name': data.get('name', '')
        }
        try:
            count = counts.get_count(**count_data)
        except Exception as e:
            raise InvalidUsage(str(e))
        return jsonify({count_data['name']: count})


@counts_endpoints.route('/add_to_count', methods=['POST'])
def add_to_count_post():
    if request.method == 'POST':
        data = request.get_json()
        count_data = {
            'name': data.get('name', '')
        }
        try:
            count = counts.add_to_count(**count_data)
        except Exception as e:
            raise InvalidUsage(str(e))
        return jsonify({count_data['name']: count})


@counts_endpoints.route('/subtract_from_count', methods=['POST'])
def subtract_from_count_post():
    if request.method == 'POST':
        data = request.get_json()
        count_data = {
            'name': data.get('name', '')
        }
        try:
            count = counts.subtract_from_count(**count_data)
        except Exception as e:
            raise InvalidUsage(str(e))
        return jsonify({count_data['name']: count})


@counts_endpoints.route('/reset_count', methods=['POST'])
def reset_count_post():
    if request.method == 'POST':
        data = request.get_json()
        count_data = {
            'name': data.get('name', '')
        }
        try:
            count = counts.reset_count(**count_data)
        except Exception as e:
            raise InvalidUsage(str(e))
        return jsonify({count_data['name']: count})


@counts_endpoints.route('/set_count', methods=['POST'])
def set_count_post():
    if request.method == 'POST':
        data = request.get_json()
        count_data = {
            'name': data.get('name', ''),
            'count': data.get('count', '')
        }
        try:
            count = counts.set_count(**count_data)
        except Exception as e:
            raise InvalidUsage(str(e))
        return jsonify({count_data['name']: count})


@counts_endpoints.route('/remove_count', methods=['POST'])
def remove_count_post():
    if request.method == 'POST':
        data = request.get_json()
        count_data = {
            'name': data.get('name', '')
        }
        try:
            count = counts.remove_count(**count_data)
        except Exception as e:
            raise InvalidUsage(str(e))
        return jsonify({'message': 'Count removed: {}'.format(count_data['name'])})
