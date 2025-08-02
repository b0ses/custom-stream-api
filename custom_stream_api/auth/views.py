import logging

from flask import Blueprint
from flask import jsonify
from webargs import fields
from webargs.flaskparser import use_kwargs

from custom_stream_api.shared import InvalidUsage
from custom_stream_api.auth import twitch_auth
from custom_stream_api.auth import hue_auth

auth_endpoints = Blueprint("auth", __name__)

logger = logging.getLogger(__name__)


@auth_endpoints.route("/twitch_login", methods=["POST"])
@use_kwargs(
    {
        "code": fields.Str(),
    },
    location="json",
)
def login_post(**kwargs):
    try:
        response = twitch_auth.login(**kwargs)
    except Exception as e:
        raise InvalidUsage(str(e))
    return jsonify(response)


@auth_endpoints.route("/twitch_logged_in", methods=["GET"])
def twitch_logged_in_get():
    try:
        response = {"logged_in": twitch_auth.twitch_logged_in()}
    except Exception as e:
        raise InvalidUsage(str(e))
    return jsonify(response)


@auth_endpoints.route("/current_user", methods=["GET"])
@twitch_auth.twitch_login_required
def current_user_get():
    try:
        response = twitch_auth.current_user()
    except Exception as e:
        raise InvalidUsage(str(e))
    return jsonify(response)


@auth_endpoints.route("/logout", methods=["GET"])
@twitch_auth.twitch_login_required
def logout_post():
    try:
        response = twitch_auth.logout()
    except Exception as e:
        raise InvalidUsage(str(e))
    return jsonify(response)


@auth_endpoints.route("/hue_login", methods=["POST"])
@use_kwargs(
    {
        "code": fields.Str(),
    },
    location="json",
)
def hue_login_post(**kwargs):
    try:
        response = hue_auth.login(**kwargs)
    except Exception as e:
        raise InvalidUsage(str(e))
    return jsonify(response)


@auth_endpoints.route("/hue_logged_in", methods=["GET"])
def hue_logged_in_get():
    try:
        response = {"logged_in": hue_auth.hue_logged_in()}
    except Exception as e:
        raise InvalidUsage(str(e))
    return jsonify(response)
