from flask import Blueprint, request
from flask import jsonify
import logging
from custom_stream_api.shared import get_chatbot
from custom_stream_api.shared import InvalidUsage
from custom_stream_api.notifier.twitch_notifier import setup_webhook

notifier_endpoints = Blueprint('notifier', __name__)

logger = logging.getLogger()


@notifier_endpoints.route('/setup_webhook', methods=['POST'])
def setup_webhook_post():
    data = request.get_json()
    webhook_data = {
        'token': data.get('token', None),
        'callback_url': data.get('callback_url', None),
        'mode': data.get('mode', None),
        'topic': data.get('topic', None)
    }
    try:
        setup_webhook(**webhook_data)
    except Exception as e:
        raise InvalidUsage(str(e))


@notifier_endpoints.route('/stream_changed', methods=['GET', 'POST'])
def stream_changed():
    if request.method == 'GET':
        challenge = request.args.get('hub.challenge')
        return challenge
    else:
        data = request.get_json()
        chatbot = get_chatbot()
        if chatbot:
            chatbot.chat('Stream changed: {}'.format(str(data)))
        return jsonify({'message': 'Stream changed message received'})


@notifier_endpoints.route('/followed', methods=['GET', 'POST'])
def followed():
    if request.method == 'GET':
        challenge = request.args.get('hub.challenge')
        return challenge
    else:
        data = request.get_json()
        chatbot = get_chatbot()
        if chatbot:
            chatbot.chat('Followed: {}'.format(str(data)))
        return jsonify({'message': 'Followed message received'})


# @notifier_endpoints.route('/subscribed', methods=['POST'])
# def subscribed():
#     data = request.get_json()
#     raise NotImplementedError
#
#
# @notifier_endpoints.route('/hosted', methods=['POST'])
# def hosted():
#     data = request.get_json()
#     raise NotImplementedError
#
#
# @notifier_endpoints.route('/raided', methods=['POST'])
# def raided():
#     data = request.get_json()
#     raise NotImplementedError
