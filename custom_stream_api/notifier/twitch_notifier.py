import requests
import json
from custom_stream_api.settings import APP_CLIENT_CRED_TOKEN

TOKEN_URL = 'https://id.twitch.tv/oauth2/'
HELIX_URL = 'https://api.twitch.tv/helix'
WEBHOOKS_URL = '{}/webhooks'.format(HELIX_URL)


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


def subscribe_webhook(callback_url, mode, topic, token, secret=None):
    data = {
        'hub.callback': callback_url,
        'hub.mode': mode,
        'hub.topic': topic,
    }
    if secret:
        data['hub.secret'] = secret

    response = requests.post('{}/hub'.format(WEBHOOKS_URL), headers=get_headers(token), data=data)
    print(response)
    if response.status_code == 200:
        return json.loads(response.content.decode())
