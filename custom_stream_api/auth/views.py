from flask import Blueprint, request
from flask import jsonify
import logging

from custom_stream_api.shared import InvalidUsage
from custom_stream_api.auth import auth

auth_endpoints = Blueprint('auth', __name__)

logger = logging.getLogger()


@auth_endpoints.route('/login', methods=['POST'])
def login_post():
    data = request.get_json()
    login_data = {
        'code': data.get('code', None)
    }
    try:
        response = auth.login(**login_data)
    except Exception as e:
        raise InvalidUsage(str(e))
    return jsonify(response)


@auth_endpoints.route('/logged_in', methods=['GET'])
def logged_in_get():
    try:
        response = {'logged_in': auth.logged_in()}
    except Exception as e:
        raise InvalidUsage(str(e))
    return jsonify(response)


@auth_endpoints.route('/current_user', methods=['GET'])
@auth.login_required
def current_user_get():
    try:
        response = auth.current_user()
    except Exception as e:
        raise InvalidUsage(str(e))
    return jsonify(response)


@auth_endpoints.route('/logout', methods=['GET'])
@auth.login_required
def logout_post():
    try:
        response = auth.logout()
    except Exception as e:
        raise InvalidUsage(str(e))
    return jsonify(response)
