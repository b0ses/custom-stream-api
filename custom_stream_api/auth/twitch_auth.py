import requests
import logging
import json
from flask import session
from functools import wraps
import jwt
from jwt.algorithms import RSAAlgorithm
from urllib.parse import urlencode, quote_plus

from custom_stream_api import settings

TWITCH_LOGIN = settings.TWITCH_LOGIN
TWITCH_CLIENT_ID = settings.TWITCH_CLIENT_ID
TWITCH_CLIENT_SECRET = settings.TWITCH_CLIENT_SECRET
TWITCH_REDIRECT_URI = settings.TWITCH_REDIRECT_URI

TWITCH_TOKEN = "https://id.twitch.tv/oauth2/token"
TWITCH_USERINFO = "https://id.twitch.tv/oauth2/userinfo"
TWITCH_JWT_KEYS = "https://id.twitch.tv/oauth2/keys"

logger = logging.getLogger(__name__)


def twitch_login_required(func):
    @wraps(func)
    def check_token(*args, **kwargs):
        # Check to see if it's in their session
        if TWITCH_LOGIN and not twitch_logged_in():
            # If it isn't return our access denied message (you can also return a redirect or render_template)
            return ("Access denied", 401)

        # Otherwise just send them where they wanted to go
        return func(*args, **kwargs)

    return check_token


def validate_jwt(jwt_token):
    jwt_key_r = requests.get(TWITCH_JWT_KEYS)
    json_jwt_key_r = json.loads(jwt_key_r.content.decode())
    jwt_key = json_jwt_key_r["keys"][0]
    public_key = RSAAlgorithm.from_jwk(json.dumps(jwt_key))

    parsed_key = jwt.decode(jwt_token, public_key, algorithms=jwt_key["alg"], audience=TWITCH_CLIENT_ID)
    return parsed_key


def refresh_access_token():
    refresh_token = session["refresh_token"]
    params = {
        "grant_type": "refresh_token",
        "client_id": TWITCH_CLIENT_ID,
        "client_secret": TWITCH_CLIENT_SECRET,
        "refresh_token": refresh_token,
    }
    r = requests.post(TWITCH_TOKEN, params=urlencode(params, quote_via=quote_plus))
    response = json.loads(r.content.decode())

    if r.status_code == 400:
        raise Exception(response["message"])
    else:
        session["access_token"] = response["access_token"]
        session["refresh_token"] = response["refresh_token"]


def login(code):
    params = {
        "code": code,
        "grant_type": "authorization_code",
        "client_id": TWITCH_CLIENT_ID,
        "client_secret": TWITCH_CLIENT_SECRET,
        "redirect_uri": TWITCH_REDIRECT_URI,
    }
    # requests automatically encodes the params when passed as a dict, messing with the redirect uri
    param_string = "&".join(["{}={}".format(key, value) for key, value in params.items()])

    r = requests.post(TWITCH_TOKEN, params=param_string)
    response = json.loads(r.content.decode())

    if r.status_code == 400:
        raise Exception("Failed to confirm token: {}".format(response["message"]))
    else:
        access_token = response["access_token"]
        id_token = response["id_token"]
        refresh_token = response["refresh_token"]
        session["access_token"] = access_token
        session["id_token"] = id_token
        session["refresh_token"] = refresh_token

        parsed_key = validate_jwt(id_token)
        email_verified = parsed_key["email_verified"]
        if not email_verified:
            raise Exception("Gotta verify your Twitch email.")
    return response


def twitch_logged_in():
    try:
        return "access_token" in session
    except KeyError:
        return False


def current_user():
    if not twitch_logged_in():
        return {}

    # Note: this can be extracted from the ID token but the signature may expire
    headers = {"Authorization": "Bearer {}".format(session["access_token"])}
    r = requests.get(TWITCH_USERINFO, headers=headers)
    if r.status_code == 401:
        refresh_access_token()
        r = requests.get(TWITCH_USERINFO, headers=headers)
    ui_response = json.loads(r.content.decode())

    response = {
        "user_id": ui_response["sub"],
        "username": ui_response["preferred_username"],
        "picture": ui_response["picture"],
    }
    return response


def logout():
    [session.pop(key) for key in list(session.keys())]
    session.clear()

    response = {"message": "Logged out"}
    return response
