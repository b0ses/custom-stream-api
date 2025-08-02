import logging

from flask import Blueprint, request
from flask import jsonify

from webargs import fields
from webargs.flaskparser import use_kwargs

from custom_stream_api.shared import InvalidUsage
from custom_stream_api.lists import lists
from custom_stream_api.auth import twitch_auth

lists_endpoints = Blueprint("lists", __name__)

logger = logging.getLogger(__name__)


@lists_endpoints.route("/", methods=["GET", "POST"])
@twitch_auth.twitch_login_required
def list_lists_get():
    try:
        all_lists = lists.list_lists()
    except Exception as e:
        raise InvalidUsage(str(e))
    return jsonify(all_lists)


@lists_endpoints.route("/set_list", methods=["POST"])
@twitch_auth.twitch_login_required
@use_kwargs(
    {
        "name": fields.Str(required=True),
        "items": fields.List(fields.Str(), load_default=[]),
    },
    location="json",
)
def set_list_post(**kwargs):
    try:
        lists.set_list(**kwargs)
    except Exception as e:
        logger.exception(e)
        raise InvalidUsage(str(e))
    return jsonify({"message": "List set: {}".format(kwargs["name"])})


@lists_endpoints.route("/add_to_list", methods=["POST"])
@twitch_auth.twitch_login_required
@use_kwargs(
    {
        "name": fields.Str(required=True),
        "items": fields.List(fields.Str(), load_default=[]),
    },
    location="json",
)
def add_to_list_post(**kwargs):
    try:
        lists.add_to_list(**kwargs)
    except Exception as e:
        logger.exception(e)
        raise InvalidUsage(str(e))
    return jsonify({"message": "Added to list: {}".format(kwargs["items"])})


@lists_endpoints.route("/get_list", methods=["GET"])
@twitch_auth.twitch_login_required
@use_kwargs(
    {
        "name": fields.Str(required=True),
    },
    location="query",
)
def get_list(**kwargs):
    try:
        list_dict = lists.get_list(**kwargs)
    except Exception as e:
        logger.exception(e)
        raise InvalidUsage(str(e))
    return jsonify(list_dict)


@lists_endpoints.route("/get_list_item", methods=["POST"])
@twitch_auth.twitch_login_required
@use_kwargs({"name": fields.Str(required=True), "index": fields.Int(load_default=None)}, location="json")
def get_list_item_post(**kwargs):
    try:
        item, index = lists.get_list_item(**kwargs)
    except Exception as e:
        logger.exception(e)
        raise InvalidUsage(str(e))
    return jsonify({"item": item, "index": index})


@lists_endpoints.route("/remove_from_list", methods=["POST"])
@twitch_auth.twitch_login_required
@use_kwargs({"name": fields.Str(required=True), "index": fields.Int(load_default=0)}, location="json")
def remove_from_list_post(kwargs):
    if request.method == "POST":
        data = request.get_json()
        list_data = {"name": data.get("name", ""), "index": data.get("index", 0)}
        try:
            lists.remove_from_list(**list_data)
        except Exception as e:
            logger.exception(e)
            raise InvalidUsage(str(e))
        return jsonify({"message": "Removed item from list (index {})".format(list_data["index"])})


@lists_endpoints.route("/remove_list", methods=["POST"])
@twitch_auth.twitch_login_required
@use_kwargs(
    {
        "name": fields.Str(required=True),
    },
    location="json",
)
def remove_list_post(**kwargs):
    try:
        lists.remove_list(**kwargs)
    except Exception as e:
        logger.exception(e)
        raise InvalidUsage(str(e))
    return jsonify({"message": "List removed: {}".format(kwargs["name"])})
