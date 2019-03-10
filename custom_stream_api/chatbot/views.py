from flask import Blueprint, request
from flask import jsonify
from custom_stream_api.chatbot import twitchbot
from custom_stream_api.shared import InvalidUsage

chatbot_endpoints = Blueprint('chatbot', __name__)

from custom_stream_api.shared import g

@chatbot_endpoints.route('/start', methods=['POST'])
def start_post():
    if request.method == 'POST':
        data = request.get_json()
        twitchbot_data = {
            'bot_name': data.get('bot_name', ''),
            'client_id': data.get('client_id', ''),
            'chat_token': data.get('chat_token', ''),
            'channel': data.get('channel', ''),
            'timeout': data.get('timeout', 30)
        }
        try:
            bot_id = twitchbot.setup_chatbot(**twitchbot_data)
            return jsonify({'message': 'started chatbot: {}'.format(bot_id)})
        except Exception as e:
            raise InvalidUsage(str(e))


@chatbot_endpoints.route('/stop', methods=['POST'])
def stop_post():
    if request.method == 'POST':
        data = request.get_json()
        twitchbot_data = {
            'chatbot_id': data.get('chatbot_id', '')
        }
        try:
            twitchbot.stop_chatbot(**twitchbot_data)
            return jsonify({'message': 'stopped chatbot'})
        except Exception as e:
            raise InvalidUsage(str(e))


@chatbot_endpoints.route('/aliases', methods=['GET', 'POST'])
def aliases():
    if 'chatbot' not in g:
        raise InvalidUsage('No chatbot running. Please start the chatbot beforehand.')
    if request.method == 'GET':
        try:
            all_aliases = [alias.as_dict() for alias in g['chatbot'].list_aliases()]
        except Exception as e:
            raise InvalidUsage(str(e))
        return jsonify(all_aliases)
    else:
        data = request.get_json()
        try:
            g['chatbot'].import_aliases(data)
        except Exception as e:
            raise InvalidUsage(str(e))
        return jsonify({'message': 'Chat reactions imported'})


@chatbot_endpoints.route('/add_alias', methods=['POST'])
def add_alias_post():
    data = request.get_json()
    alias_data = {
        'alias': data.get('alias', ''),
        'command': data.get('command', ''),
        'badge': data.get('badge', 'broadcaster')
    }
    chatbot_id = data.get('chatbot_id', '')
    try:
        chatbot = twitchbot.verify_chatbot_id(chatbot_id)
        chatbot.add_alias(**alias_data)
        return jsonify({'message': 'Alias added'})
    except Exception as e:
        raise InvalidUsage(str(e))


@chatbot_endpoints.route('/remove_alias', methods=['POST'])
def remove_alias_post():
    data = request.get_json()
    alias_data = {
        'alias': data.get('alias', '')
    }
    chatbot_id = data.get('chatbot_id', '')
    try:
        chatbot = twitchbot.verify_chatbot_id(chatbot_id)
        chatbot.remove_alias(**alias_data)
        return jsonify({'message': 'Alias removed'})
    except Exception as e:
        raise InvalidUsage(str(e))