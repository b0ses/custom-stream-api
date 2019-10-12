from flask import Blueprint, request
from flask import jsonify
import logging
from custom_stream_api.shared import get_chatbot
from custom_stream_api.shared import InvalidUsage
from custom_stream_api.notifier.twitch_notifier import start_webhooks, stop_webhooks, NOTIFIER_NAME, TopicName
from custom_stream_api.auth import auth


notifier_endpoints = Blueprint(NOTIFIER_NAME, __name__)

logger = logging.getLogger()


@auth.login_required
@notifier_endpoints.route('/start_webhooks', methods=['POST'])
def setup_webhook_post():
    try:
        start_webhooks()
    except Exception as e:
        raise InvalidUsage(str(e))
    return jsonify({'message': 'Webhooks started'})


@auth.login_required
@notifier_endpoints.route('/stop_webhooks', methods=['POST'])
def stop_webhook_post():
    try:
        stop_webhooks()
    except Exception as e:
        raise InvalidUsage(str(e))
    return jsonify({'message': 'Webhooks stopped'})


@notifier_endpoints.route('/{}'.format(TopicName.STREAM_CHANGED), methods=['GET', 'POST'])
def stream_changed():
    if request.method == 'GET':
        challenge = request.args.get('hub.challenge')
        return challenge
    else:
        data = request.get_json()
        logger.info(data)
        # chatbot = get_chatbot()
        # if chatbot:
        #     chatbot.chat('Stream changed: {}'.format(str(data)))
        return jsonify({'message': 'Stream changed message received'})


@notifier_endpoints.route('/{}'.format(TopicName.FOLLOWED), methods=['GET', 'POST'])
def followed():
    if request.method == 'GET':
        challenge = request.args.get('hub.challenge')
        return challenge
    else:
        data = request.get_json()
        chatbot = get_chatbot()
        if chatbot and data:
            followed_user = data['data'][0]['from_name']
            chatbot.chat('Thanks for following, {}!'.format(followed_user))
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
