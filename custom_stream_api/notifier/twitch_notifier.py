import requests
import json
import threading
import time
from enum import Enum
from collections import namedtuple

from flask import session, request
from custom_stream_api import settings
from custom_stream_api.auth.auth import get_headers, current_user

NOTIFIER_NAME = 'notifier'

HELIX_URL = 'https://api.twitch.tv/helix'
WEBHOOKS_URL = '{}/webhooks'.format(HELIX_URL)

WEBHOOK_SECRET = settings.WEBHOOK_SECRET
WEBHOOK_LEASE = 60 * 60 * 24  # 24 hours, daily
WEBHOOK_RENEW = WEBHOOK_LEASE - (60 * 60)  # 23 hours so that it renews before expiring


class TopicName(Enum):
    FOLLOWED = 'followed'
    STREAM_CHANGED = 'stream_changed'


Topic = namedtuple('Topic', ['name', 'url', 'activated'])
TOPICS = [
    Topic(
        name=TopicName.FOLLOWED,
        url='{helix_url}/users/follows?first=1&to_id={user_id}',
        activated=settings.CHAT_FOLLOWS
    ),
    Topic(
        name=TopicName.STREAM_CHANGED,
        url='{helix_url}/users/streams?user_id={user_id}',
        activated=settings.CHAT_STREAM_CHANGES
    )
]
ACTIVATED_TOPICS = list(filter(lambda topic: topic.activated, TOPICS))
renew_webhooks = False


def get_webook_subscriptions(token):
    response = requests.get('{}/subscriptions'.format(WEBHOOKS_URL), headers=get_headers(auth_token=token))
    if response.status_code == 200:
        return json.loads(response.content.decode())


def _hit_webhook_endpoint(data, token):
    return requests.post('{}/hub'.format(WEBHOOKS_URL), headers=get_headers(client_id=token), data=data)


def _renew_subscription(subscription_data, token):
    global renew_webhooks

    lease_timer = 0
    while renew_webhooks:
        if lease_timer == WEBHOOK_RENEW:
            _hit_webhook_endpoint(subscription_data, token)
            lease_timer = 0
        time.sleep(1)
        lease_timer += 1


def _update_webhook(topic, mode, user_id, token):
    if topic not in ACTIVATED_TOPICS:
        raise ValueError('Topic not activated.')
    if mode not in ('subscribe', 'unsubscribe'):
        raise ValueError('Mode must be subscribe or unsubscribe.')
    if not WEBHOOK_SECRET:
        raise ValueError('WEBHOOK_SECRET setting not setup. Please just fill it in and redo.')
    if not (user_id and token):
        raise ValueError('user_id or token not provided')

    data = {
        'hub.callback': '{}/{}/{}'.format(request.host_url, NOTIFIER_NAME, topic.name),
        'hub.mode': mode,
        'hub.topic': topic.url.format(helix_url=HELIX_URL, user_id=user_id),
        'hub.lease_seconds': WEBHOOK_LEASE,
        'hub.secret': WEBHOOK_SECRET
    }

    response = _hit_webhook_endpoint(data, token)
    print(response.status_code)
    if response.status_code != 202:
        raise Exception('Failed to update hook')
    if mode == 'subscribe':
        renew_thread = threading.Thread(target=_renew_subscription, args=(data, token))
        renew_thread.start()


def start_webhooks():
    global renew_webhooks
    renew_webhooks = True
    admin_user_id = current_user()['user_id']
    token = session['access_token']
    for topic in ACTIVATED_TOPICS:
        _update_webhook(topic, 'subscribe', admin_user_id, token)


def stop_webhooks():
    global renew_webhooks
    renew_webhooks = False
    admin_user_id = current_user()['user_id']
    token = session['access_token']
    for topic in ACTIVATED_TOPICS:
        _update_webhook(topic, 'unsubscribe', admin_user_id, token)
