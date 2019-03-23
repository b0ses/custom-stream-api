from flask import Blueprint, request
from flask import jsonify
from custom_stream_api.shared import InvalidUsage
from custom_stream_api.lists import lists

lists_endpoints = Blueprint('lists', __name__)


@lists_endpoints.route('/lists', methods=['GET', 'POST'])
def lists():
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
