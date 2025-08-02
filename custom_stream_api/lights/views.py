import logging

from flask import Blueprint
from flask import jsonify
from webargs import fields
from webargs.flaskparser import use_kwargs

from custom_stream_api.shared import InvalidUsage
from custom_stream_api.lights import lights
from custom_stream_api.auth import twitch_auth

lights_endpoints = Blueprint("lights", __name__)

logger = logging.getLogger(__name__)


@lights_endpoints.route("/change_lights_hue", methods=["POST"])
@twitch_auth.twitch_login_required
@use_kwargs(
    {
        "on": fields.Bool(load_default=True),
        "saturation": fields.Int(load_default=0),
        "brightness": fields.Int(load_default=254),
        "hue": fields.Int(load_default=0),
        "effect": fields.Str(load_default="none"),
        "xy": fields.List(fields.Str(), load_default=[]),
    },
    location="json",
)
def change_lights_hue_post(**kwargs):
    try:
        lights.change_lights_hue(**kwargs)
        return jsonify({"message": "changed lights"})
    except Exception as e:
        logger.exception(e)
        raise InvalidUsage(str(e))


@lights_endpoints.route("/change_lights_static", methods=["POST"])
@twitch_auth.twitch_login_required
@use_kwargs(
    {
        "color": fields.Str(load_default="#FFFFFF"),
        "brightness": fields.Int(load_default=None),
    },
    location="json",
)
def change_lights_static_post(**kwargs):
    try:
        lights.change_lights_static(**kwargs)
        return jsonify({"message": "changed lights"})
    except Exception as e:
        logger.exception(e)
        raise InvalidUsage(str(e))


@lights_endpoints.route("/lock", methods=["POST"])
@twitch_auth.twitch_login_required
def lock_post():
    try:
        lights.lock()
        return jsonify({"message": "lights locked"})
    except Exception as e:
        logger.exception(e)
        raise InvalidUsage(str(e))


@lights_endpoints.route("/unlock", methods=["POST"])
@twitch_auth.twitch_login_required
def unlock_post():
    try:
        lights.unlock()
        return jsonify({"message": "lights unlocked"})
    except Exception as e:
        logger.exception(e)
        raise InvalidUsage(str(e))
