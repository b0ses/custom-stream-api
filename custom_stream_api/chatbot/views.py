import logging

from flask import Blueprint, request
from flask import jsonify
from webargs import fields
from webargs.flaskparser import use_kwargs

from custom_stream_api.chatbot import twitchbot
from custom_stream_api.shared import InvalidUsage
from custom_stream_api.chatbot import aliases, timers
from custom_stream_api.auth import twitch_auth

chatbot_endpoints = Blueprint("chatbot", __name__)

logger = logging.getLogger(__name__)


@chatbot_endpoints.route("/restart", methods=["POST"])
@twitch_auth.twitch_login_required
@use_kwargs(
    {
        "bot_name": fields.Str(required=True),
        "client_id": fields.Str(required=True),
        "chat_token": fields.Str(required=True),
        "channel": fields.Str(required=True),
        "timeout": fields.Int(load_default=15),
    },
    location="json",
)
def start_post(**kwargs):
    try:
        bot_id = twitchbot.setup_chatbot(**kwargs)
        return jsonify({"message": "started chatbot: {}".format(bot_id)})
    except Exception as e:
        logger.exception(e)
        raise InvalidUsage(str(e))


@chatbot_endpoints.route("/aliases", methods=["GET"])
@twitch_auth.twitch_login_required
def list_aliases_get():
    try:
        all_aliases = aliases.list_aliases()
    except Exception as e:
        logger.exception(e)
        raise InvalidUsage(str(e))
    return jsonify(all_aliases)


@chatbot_endpoints.route("/add_alias", methods=["POST"])
@twitch_auth.twitch_login_required
@use_kwargs(
    {
        "alias": fields.Str(required=True),
        "command": fields.Str(required=True),
        "badge": fields.Str(load_default="broadcaster"),
    },
    location="json",
)
def add_alias_post(**kwargs):
    try:
        aliases.add_alias(**kwargs)
        return jsonify({"message": "Alias added"})
    except Exception as e:
        logger.exception(e)
        raise InvalidUsage(str(e))


@chatbot_endpoints.route("/remove_alias", methods=["POST"])
@twitch_auth.twitch_login_required
@use_kwargs(
    {
        "alias": fields.Str(required=True),
    },
    location="json",
)
def remove_alias_post():
    data = request.get_json()
    alias_data = {"alias": data.get("alias", "")}
    try:
        aliases.remove_alias(**alias_data)
        return jsonify({"message": "Alias removed"})
    except Exception as e:
        logger.exception(e)
        raise InvalidUsage(str(e))


@chatbot_endpoints.route("/timers", methods=["GET"])
@twitch_auth.twitch_login_required
def list_timers_get():
    try:
        all_timers = timers.list_timers()
    except Exception as e:
        logger.exception(e)
        raise InvalidUsage(str(e))
    return jsonify(all_timers)


@chatbot_endpoints.route("/add_timer", methods=["POST"])
@twitch_auth.twitch_login_required
@use_kwargs(
    {
        "command": fields.Str(required=True),
        "interval": fields.Int(load_default=30),
    },
    location="json",
)
def add_timer_post(**kwargs):
    try:
        timers.add_timer(**kwargs)
        return jsonify({"message": "Timer added"})
    except Exception as e:
        logger.exception(e)
        raise InvalidUsage(str(e))


@chatbot_endpoints.route("/remove_timer", methods=["POST"])
@twitch_auth.twitch_login_required
@use_kwargs(
    {
        "command": fields.Str(required=True),
    },
    location="json",
)
def remove_timer_post(**kwargs):
    try:
        timers.remove_timer(**kwargs)
        return jsonify({"message": "Timer removed"})
    except Exception as e:
        logger.exception(e)
        raise InvalidUsage(str(e))
