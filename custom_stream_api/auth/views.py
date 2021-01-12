from flask import Blueprint, request
from flask import jsonify
import logging

from custom_stream_api.shared import InvalidUsage
from custom_stream_api.auth import twitch_auth
from custom_stream_api.auth import hue_auth

auth_endpoints = Blueprint('auth', __name__)

logger = logging.getLogger()


@auth_endpoints.route('/twitch_login', methods=['POST'])
def login_post():
    data = request.get_json()
    login_data = {
        'code': data.get('code', None)
    }
    try:
        response = twitch_auth.login(**login_data)
    except Exception as e:
        raise InvalidUsage(str(e))
    return jsonify(response)


@auth_endpoints.route('/twitch_logged_in', methods=['GET'])
def twitch_logged_in_get():
    try:
        response = {'logged_in': twitch_auth.twitch_logged_in()}
    except Exception as e:
        raise InvalidUsage(str(e))
    return jsonify(response)


@auth_endpoints.route('/current_user', methods=['GET'])
@twitch_auth.twitch_login_required
def current_user_get():
    try:
        response = twitch_auth.current_user()
    except Exception as e:
        raise InvalidUsage(str(e))
    return jsonify(response)


@auth_endpoints.route('/logout', methods=['GET'])
@twitch_auth.twitch_login_required
def logout_post():
    try:
        response = twitch_auth.logout()
    except Exception as e:
        raise InvalidUsage(str(e))
    return jsonify(response)


@auth_endpoints.route('/hue_login', methods=['POST'])
def hue_login_post():
    data = request.get_json()
    login_data = {
        'code': data.get('code', None)
    }
    try:
        response = hue_auth.login(**login_data)
    except Exception as e:
        raise InvalidUsage(str(e))
    return jsonify(response)


@auth_endpoints.route('/hue_logged_in', methods=['GET'])
def hue_logged_in_get():
    try:
        response = {'logged_in': hue_auth.hue_logged_in()}
    except Exception as e:
        raise InvalidUsage(str(e))
    return jsonify(response)
