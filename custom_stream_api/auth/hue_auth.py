import requests
import logging
import json
import base64
from functools import wraps

from custom_stream_api.shared import g
from custom_stream_api import settings

LIGHTS_LOCAL = settings.LIGHTS_LOCAL
HUE_CLIENT_ID = settings.HUE_CLIENT_ID
HUE_CLIENT_SECRET = settings.HUE_CLIENT_SECRET
HUE_REDIRECT_URI = settings.HUE_REDIRECT_URI
HUE_APP_NAME = settings.HUE_APP_NAME

logger = logging.getLogger()

HUE_TOKEN = "https://api.meethue.com/oauth2/token"
HUE_REFRESH = "https://api.meethue.com/oauth2/refresh?grant_type=refresh_token"
HUE_BRIDGE = "https://api.meethue.com/bridge/"


def hue_login_required(func):
    @wraps(func)
    def check_token(*args, **kwargs):
        # Check to see if it's in their session
        if not hue_logged_in():
            # If it isn't return our access denied message (you can also return a redirect or render_template)
            return ("Access denied", 401)

        # Otherwise just send them where they wanted to go
        return func(*args, **kwargs)

    return check_token


def hue_logged_in():
    try:
        logged_in = LIGHTS_LOCAL or ("hue_username" in g)
        if logged_in and not LIGHTS_LOCAL:
            refresh_access_token(g["hue_refresh_token"])
        return logged_in
    except KeyError:
        return False


def get_hue_username(access_token):
    # Push the button
    headers = {"Authorization": "Bearer {}".format(access_token)}
    params = {"linkbutton": True}
    requests.put("{}0/config".format(HUE_BRIDGE), headers=headers, json=params)

    # Get the name
    params = {"devicetype": HUE_APP_NAME}
    r = requests.post(HUE_BRIDGE, headers=headers, json=params)
    response = json.loads(r.content.decode())
    return response[0]["success"]["username"]


def login(code):
    if hue_logged_in():
        return True
    params = {
        "code": code,
        "grant_type": "authorization_code",
    }
    bearer_code = "{}:{}".format(HUE_CLIENT_ID, HUE_CLIENT_SECRET)
    bearer = base64.b64encode(bytes(bearer_code, "utf-8"))
    headers = {"Authorization": "Basic: {}".format(bearer.decode("utf-8"))}
    r = requests.post(HUE_TOKEN, headers=headers, params=params)
    response = json.loads(r.content.decode())

    if r.status_code == 400:
        raise Exception("Failed to confirm token: {}".format(response["message"]))
    else:
        access_token = response["access_token"]
        refresh_token = response["refresh_token"]
        g["hue_access_token"] = access_token
        g["hue_refresh_token"] = refresh_token
        g["hue_username"] = get_hue_username(access_token)

    return True


def refresh_access_token(refresh_token):
    params = {"refresh_token": refresh_token}
    bearer_code = "{}:{}".format(HUE_CLIENT_ID, HUE_CLIENT_SECRET)
    bearer = base64.b64encode(bytes(bearer_code, "utf-8"))
    headers = {"Authorization": "Basic: {}".format(bearer.decode("utf-8"))}
    r = requests.post(HUE_REFRESH, headers=headers, data=params)
    response = json.loads(r.content.decode())

    if r.status_code == 400:
        raise Exception(response["message"])
    else:
        g["hue_access_token"] = response["access_token"]
        g["hue_refresh_token"] = response["refresh_token"]
