from flask import Blueprint, request
from flask import jsonify
import logging

from custom_stream_api.shared import InvalidUsage
from custom_stream_api.lights import lights
from custom_stream_api.auth import twitch_auth

lights_endpoints = Blueprint('lights', __name__)

logger = logging.getLogger()


@lights_endpoints.route('/change_lights_hue', methods=['POST'])
@twitch_auth.twitch_login_required
def change_lights_hue_post():
    if request.method == 'POST':
        data = request.get_json()
        lights_data = {
            'on': data.get('on', True),
            'saturation': data.get('saturation', 0),
            'brightness': data.get('brightness', 254),
            'hue': data.get('hue', 0),
            'effect': data.get('effect', 'none'),
            'xy': data.get('xy', [])
        }
        try:
            lights.change_lights_hue(**lights_data)
            return jsonify({'message': 'changed lights'})
        except Exception as e:
            raise InvalidUsage(str(e))


@lights_endpoints.route('/change_lights_static', methods=['POST'])
@twitch_auth.twitch_login_required
def change_lights_static_post():
    if request.method == 'POST':
        data = request.get_json()
        lights_data = {
            'color': data.get('color', '#FFFFFF'),
            'brightness': data.get('brightness', None)
        }
        try:
            lights.change_lights_static(**lights_data)
            return jsonify({'message': 'changed lights'})
        except Exception as e:
            raise InvalidUsage(str(e))


@lights_endpoints.route('/lock', methods=['POST'])
@twitch_auth.twitch_login_required
def lock_post():
    if request.method == 'POST':
        try:
            lights.lock()
            return jsonify({'message': 'lights locked'})
        except Exception as e:
            raise InvalidUsage(str(e))


@lights_endpoints.route('/unlock', methods=['POST'])
@twitch_auth.twitch_login_required
def unlock_post():
    if request.method == 'POST':
        try:
            lights.unlock()
            return jsonify({'message': 'lights unlocked'})
        except Exception as e:
            raise InvalidUsage(str(e))
