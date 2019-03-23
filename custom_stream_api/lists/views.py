from flask import Blueprint, request
from flask import jsonify
from custom_stream_api.shared import InvalidUsage
from custom_stream_api.lists import lists

lists_endpoints = Blueprint('lists', __name__)


@lists_endpoints.route('/', methods=['GET', 'POST'])
def list_lists_get():
    if request.method == 'GET':
        try:
            all_lists = lists.list_lists()
        except Exception as e:
            raise InvalidUsage(str(e))
        return jsonify(all_lists)
    else:
        data = request.get_json()
        try:
            lists.import_lists(data)
        except Exception as e:
            raise InvalidUsage(str(e))
        return jsonify({'message': 'Lists imported'})

@lists_endpoints.route('/set_list', methods=['POST'])
def set_list_post():
    if request.method == 'POST':
        data = request.get_json()
        list_data = {
            'name': data.get('name', ''),
            'items': data.get('items', [])
        }
        try:
            lists.set_list(**list_data)
        except Exception as e:
            raise InvalidUsage(str(e))
        return jsonify({'message': 'List set: {}'.format(list_data['name'])})

@lists_endpoints.route('/add_to_list', methods=['POST'])
def add_to_list_post():
    if request.method == 'POST':
        data = request.get_json()
        list_data = {
            'name': data.get('name', ''),
            'items': data.get('items', [])
        }
        try:
            lists.add_to_list(**list_data)
        except Exception as e:
            raise InvalidUsage(str(e))
        return jsonify({'message': 'Added to list: {}'.format(list_data['items'])})

@lists_endpoints.route('/get_list', methods=['POST'])
def get_list():
    if request.method == 'POST':
        data = request.get_json()
        list_data = {
            'name': data.get('name', '')
        }
        try:
            list_dict = lists.get_list(**list_data)
        except Exception as e:
            raise InvalidUsage(str(e))
        return jsonify(list_dict)

@lists_endpoints.route('/get_list_item', methods=['POST'])
def get_list_item_post():
    if request.method == 'POST':
        data = request.get_json()
        list_data = {
            'name': data.get('name', ''),
            'index': data.get('index', 0)
        }
        try:
            item = lists.get_list_item(**list_data)
        except Exception as e:
            raise InvalidUsage(str(e))
        return jsonify({'item': item})


@lists_endpoints.route('/remove_from_list', methods=['POST'])
def remove_from_list_post():
    if request.method == 'POST':
        data = request.get_json()
        list_data = {
            'name': data.get('name', ''),
            'index': data.get('index', 0)
        }
        try:
            lists.remove_from_list(**list_data)
        except Exception as e:
            raise InvalidUsage(str(e))
        return jsonify({'message': 'Removed item from list (index {})'.format(list_data['index'])})


@lists_endpoints.route('/remove_list', methods=['POST'])
def remove_list_post():
    if request.method == 'POST':
        data = request.get_json()
        list_data = {
            'name': data.get('name', '')
        }
        try:
            lists.remove_list(**list_data)
        except Exception as e:
            raise InvalidUsage(str(e))
        return jsonify({'message': 'List removed: {}'.format(list_data['name'])})
