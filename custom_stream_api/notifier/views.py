from flask import Blueprint, request
from flask import jsonify
import logging
from custom_stream_api.shared import get_chatbot

notifier_endpoints = Blueprint('notifier', __name__)

logger = logging.getLogger()

# @notifier_endpoints.route('/setup_webhooks', methods=['POST'])
# def setup_webhooks():
#     data = request.get_json()
#     raise NotImplementedError


@notifier_endpoints.route('/stream_changed', methods=['POST'])
def stream_changed():
    data = request.get_json()
    chatbot = get_chatbot()
    if chatbot:
        chatbot.chat('Stream changed: {}'.format(str(data)))
    return jsonify({'message': 'Stream changed message received'})


@notifier_endpoints.route('/followed', methods=['POST'])
def followed():
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
