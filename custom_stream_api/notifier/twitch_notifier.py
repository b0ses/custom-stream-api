import requests
import json
import threading
import time
from custom_stream_api import settings

TOKEN_URL = 'https://id.twitch.tv/oauth2/'
HELIX_URL = 'https://api.twitch.tv/helix'
WEBHOOKS_URL = '{}/webhooks'.format(HELIX_URL)
WEBHOOK_SECRET = settings.WEBHOOK_SECRET
WEBHOOK_LEASE = 60 * 60 * 24  # 24 hours, daily
WEBHOOK_RENEW = WEBHOOK_LEASE - (60 * 60)  # 23 hours so that it renews before expiring


def get_user_data(token, username):
    params = {
        'login': username
    }
    response = requests.get('{}/users'.format(HELIX_URL), headers=get_headers(auth_token=token), params=params)
    if response.status_code == 200:
        return json.loads(response.content.decode())['data']


def get_token(client_id, client_secret, grant_type=None, refresh_token=None):
    if not refresh_token and not grant_type:
        raise Exception('grant_type or refresh_token not provided')
    elif refresh_token:
        grant_type = 'refresh_token'
    params = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': grant_type
    }
    if refresh_token:
        params['refresh_token'] = refresh_token
    response = requests.post('{}/token'.format(TOKEN_URL), params=params)
    if response.status_code == 200:
        return json.loads(response.content.decode())


def revoke_token(client_id, token):
    params = {
        'client_id': client_id,
        'token': token
    }
    response = requests.post('{}/revoke'.format(TOKEN_URL), params=params)
    if response.status_code == 200:
        return json.loads(response.content.decode())


def get_headers(auth_token=None):
    headers = {}
    if auth_token:
        headers['Authorization'] = 'Bearer {}'.format(auth_token)
    return headers


def get_webook_subscriptions(token):
    response = requests.get('{}/subscriptions'.format(WEBHOOKS_URL), headers=get_headers(auth_token=token))
    if response.status_code == 200:
        return json.loads(response.content.decode())


def setup_stream_changed_webhook(token, user_id):
    params = {
        'user_id': user_id
    }
    response = requests.get('{}/streams'.format(HELIX_URL), headers=get_headers(auth_token=token), params=params)
    if response.status_code == 200:
        return json.loads(response.content.decode())


def _subscribe_webhook(data, token):
    return requests.post('{}/hub'.format(WEBHOOKS_URL), headers=get_headers(token), data=data)


def _renew_subscription(subscription_data):
    lease_timer = 0
    # TODO: trigger/flag to kill renew_subscription threads
    while True:
        if lease_timer == WEBHOOK_RENEW:
            _subscribe_webhook(subscription_data)
            lease_timer = 0
        time.sleep(1)
        lease_timer += 1


def setup_webhook(callback_url=None, mode=None, topic=None, token=None):
    if not (callback_url and mode and topic and token):
        raise Exception('Not enough arguments provided (callback_url, mode, topic, or token can\'t be None')
    if mode not in ['subscribe', 'unsubscribe']:
        raise Exception('Mode must be subscribe or unsubscribe')
    if topic not in ['User Follows', 'Stream Changed']:
        raise Exception('Topic must be \'User Follows\' or \'Stream Changed\'')
    data = {
        'hub.callback': callback_url,
        'hub.mode': mode,
        'hub.topic': topic,
        'hub.lease_seconds': WEBHOOK_LEASE
    }
    secret = WEBHOOK_SECRET
    if secret:
        data['hub.secret'] = secret
    else:
        raise('WEBHOOK_SECRET setting not setup. Please just fill it in to continue.')

    response = _subscribe_webhook(data, token)
    if response.status_code == 200:
        renew_thread = threading.Thread(target=_renew_subscription, args=(data, token))
        renew_thread.start()
        return json.loads(response.content.decode())
    else:
        raise Exception('Failed to setup hook')
