import logging

from flask import Blueprint
from flask import jsonify
from webargs import fields
from webargs.flaskparser import use_kwargs

from custom_stream_api.counts import counts
from custom_stream_api.shared import InvalidUsage
from custom_stream_api.auth import twitch_auth

counts_endpoints = Blueprint("counts", __name__)

logger = logging.getLogger(__name__)


@counts_endpoints.route("/", methods=["GET"])
@twitch_auth.twitch_login_required
def list_counts_get():
    try:
        all_counts = counts.list_counts()
    except Exception as e:
        raise InvalidUsage(str(e))
    return jsonify(all_counts)


@counts_endpoints.route("/count", methods=["GET"])
@twitch_auth.twitch_login_required
@use_kwargs(
    {
        "name": fields.Str(required=True),
    },
    location="query",
)
def get_count_get(**kwargs):
    try:
        count = counts.get_count(**kwargs)
    except Exception as e:
        logger.exception(e)
        raise InvalidUsage(str(e))
    return jsonify({kwargs["name"]: count})


@counts_endpoints.route("/add_to_count", methods=["POST"])
@twitch_auth.twitch_login_required
@use_kwargs(
    {
        "name": fields.Str(required=True),
    },
    location="json",
)
def add_to_count_post(**kwargs):
    try:
        count = counts.add_to_count(**kwargs)
    except Exception as e:
        logger.exception(e)
        raise InvalidUsage(str(e))
    return jsonify({kwargs["name"]: count})


@counts_endpoints.route("/subtract_from_count", methods=["POST"])
@twitch_auth.twitch_login_required
@use_kwargs(
    {
        "name": fields.Str(required=True),
    },
    location="json",
)
def subtract_from_count_post(**kwargs):
    try:
        count = counts.subtract_from_count(**kwargs)
    except Exception as e:
        logger.exception(e)
        raise InvalidUsage(str(e))
    return jsonify({kwargs["name"]: count})


@counts_endpoints.route("/reset_count", methods=["POST"])
@twitch_auth.twitch_login_required
@use_kwargs(
    {
        "name": fields.Str(required=True),
    },
    location="json",
)
def reset_count_post(**kwargs):
    try:
        count = counts.reset_count(**kwargs)
    except Exception as e:
        logger.exception(e)
        raise InvalidUsage(str(e))
    return jsonify({kwargs["name"]: count})


@counts_endpoints.route("/set_count", methods=["POST"])
@twitch_auth.twitch_login_required
@use_kwargs(
    {
        "name": fields.Str(required=True),
        "count": fields.Int(load_default=0),
        "tag_name": fields.Str(),
    },
    location="json",
)
def set_count_post(**kwargs):
    try:
        count = counts.set_count(**kwargs)
    except Exception as e:
        logger.exception(e)
        raise InvalidUsage(str(e))
    return jsonify({kwargs["name"]: count})


@counts_endpoints.route("/remove_count", methods=["POST"])
@twitch_auth.twitch_login_required
@use_kwargs(
    {
        "name": fields.Str(required=True),
    },
    location="json",
)
def remove_count_post(**kwargs):
    try:
        counts.remove_count(**kwargs)
    except Exception as e:
        logger.exception(e)
        raise InvalidUsage(str(e))
    return jsonify({"message": "Count removed: {}".format(kwargs["name"])})
