from flask import Blueprint, request
from flask import jsonify
from custom_stream_api.chatbot import twitchbot
from custom_stream_api.shared import InvalidUsage

chatbot_endpoints = Blueprint('chatbot', __name__)


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
