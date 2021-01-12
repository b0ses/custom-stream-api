from flask import Blueprint, request
from flask import jsonify
import logging

from custom_stream_api.chatbot import twitchbot
from custom_stream_api.shared import InvalidUsage
from custom_stream_api.chatbot import aliases, timers
from custom_stream_api.auth import twitch_auth

chatbot_endpoints = Blueprint('chatbot', __name__)

logger = logging.getLogger()


@chatbot_endpoints.route('/restart', methods=['POST'])
@twitch_auth.twitch_login_required
def start_post():
    if request.method == 'POST':
        data = request.get_json()
        twitchbot_data = {
            'bot_name': data.get('bot_name', ''),
            'client_id': data.get('client_id', ''),
            'chat_token': data.get('chat_token', ''),
            'channel': data.get('channel', ''),
            'timeout': data.get('timeout', 15)
        }
        try:
            bot_id = twitchbot.setup_chatbot(**twitchbot_data)
            return jsonify({'message': 'started chatbot: {}'.format(bot_id)})
        except Exception as e:
            raise InvalidUsage(str(e))


@chatbot_endpoints.route('/aliases', methods=['GET', 'POST'])
@twitch_auth.twitch_login_required
def list_aliases_get():
    if request.method == 'GET':
        try:
            all_aliases = aliases.list_aliases()
        except Exception as e:
            logger.exception(e)
            raise InvalidUsage(str(e))
        return jsonify(all_aliases)
    else:
        data = request.get_json()
        try:
            aliases.import_aliases(data)
        except Exception as e:
            raise InvalidUsage(str(e))
        return jsonify({'message': 'Aliases imported'})


@chatbot_endpoints.route('/add_alias', methods=['POST'])
@twitch_auth.twitch_login_required
def add_alias_post():
    data = request.get_json()
    alias_data = {
        'alias': data.get('alias', ''),
        'command': data.get('command', ''),
        'badge': data.get('badge', 'broadcaster')
    }
    try:
        aliases.add_alias(**alias_data)
        return jsonify({'message': 'Alias added'})
    except Exception as e:
        raise InvalidUsage(str(e))


@chatbot_endpoints.route('/remove_alias', methods=['POST'])
@twitch_auth.twitch_login_required
def remove_alias_post():
    data = request.get_json()
    alias_data = {
        'alias': data.get('alias', '')
    }
    try:
        aliases.remove_alias(**alias_data)
        return jsonify({'message': 'Alias removed'})
    except Exception as e:
        raise InvalidUsage(str(e))


@chatbot_endpoints.route('/timers', methods=['GET', 'POST'])
@twitch_auth.twitch_login_required
def list_timers_get():
    if request.method == 'GET':
        try:
            all_timers = timers.list_timers()
        except Exception as e:
            logger.exception(e)
            raise InvalidUsage(str(e))
        return jsonify(all_timers)
    else:
        data = request.get_json()
        try:
            timers.import_timers(data)
        except Exception as e:
            raise InvalidUsage(str(e))
        return jsonify({'message': 'Timers imported'})


@chatbot_endpoints.route('/add_timer', methods=['POST'])
@twitch_auth.twitch_login_required
def add_timer_post():
    data = request.get_json()
    timer_data = {
        'command': data.get('command', ''),
        'interval': data.get('interval', 30)
    }
    try:
        timers.add_timer(**timer_data)
        return jsonify({'message': 'Timer added'})
    except Exception as e:
        raise InvalidUsage(str(e))


@chatbot_endpoints.route('/remove_timer', methods=['POST'])
@twitch_auth.twitch_login_required
def remove_timer_post():
    data = request.get_json()
    timer_data = {
        'command': data.get('command', '')
    }
    try:
        timers.remove_timer(**timer_data)
        return jsonify({'message': 'Timer removed'})
    except Exception as e:
        raise InvalidUsage(str(e))
