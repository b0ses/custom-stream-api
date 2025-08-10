import logging

from flask import Blueprint
from flask import jsonify
from webargs import fields, validate
from webargs.flaskparser import use_kwargs

from custom_stream_api.alerts import alerts
from custom_stream_api.shared import InvalidUsage
from custom_stream_api.auth import twitch_auth

alert_endpoints = Blueprint("alerts", __name__)

logger = logging.getLogger(__name__)


@alert_endpoints.route("/", methods=["GET"])
@twitch_auth.twitch_login_required
@use_kwargs(
    {
        "sort": fields.Str(
            validate=validate.OneOf(["name", "created_at", "-name", "-created_at"]), load_default="-created_at"
        ),
        "page": fields.Int(validate=lambda val: val > 0, load_default=1),
        "limit": fields.Int(validate=lambda val: val > 0, load_default=alerts.MAX_LIMIT),
        "tag_category": fields.Str(allow_none=True),
        "search": fields.Str(load_default=""),
        "include_alerts": fields.Bool(load_default=True),
        "include_tags": fields.Bool(load_default=True),
    },
    location="query",
)
def browse_get(**kwargs):
    try:
        search_results, page_metadata = alerts.browse(**kwargs)
    except Exception as e:
        logger.exception(e)
        raise InvalidUsage(str(e))
    return jsonify({"search_results": search_results, "page_metadata": page_metadata})


@alert_endpoints.route("/alert_details", methods=["GET"])
@twitch_auth.twitch_login_required
@use_kwargs(
    {
        "name": fields.Str(required=True),
    },
    location="query",
)
def alert_details_get(**kwargs):
    try:
        alert = alerts.alert_details(**kwargs)
    except Exception as e:
        logger.exception(e)
        raise InvalidUsage(str(e))
    return jsonify({"alert": alert})


@alert_endpoints.route("/save_alert", methods=["POST"])
@twitch_auth.twitch_login_required
@use_kwargs(
    {
        "name": fields.Str(required=True),
        "text": fields.Str(),
        "sound": fields.Str(),
        "effect": fields.Str(),
        "image": fields.Str(),
        "thumbnail": fields.Str(allow_none=True),
        "tags": fields.List(fields.Str),
    },
    location="json",
)
def save_alert_post(**kwargs):
    try:
        alert = alerts.save_alert(**kwargs)
    except Exception as e:
        logger.exception(e)
        raise InvalidUsage(str(e))
    return jsonify({"message": f"Alert saved: {alert.name}"})


@alert_endpoints.route("/alert", methods=["POST"])
@twitch_auth.twitch_login_required
@use_kwargs(
    {
        "name": fields.Str(),
        "text": fields.Str(),
        "sound": fields.Str(),
        "effect": fields.Str(),
        "image": fields.Str(),
        "live": fields.Bool(load_default=True),
    },
    location="json",
)
def alert_post(**kwargs):
    try:
        alert_text = alerts.alert(**kwargs)
        if not alert_text:
            alert_text = "Displayed alert"
    except Exception as e:
        logger.exception(e)
        raise InvalidUsage(str(e))
    return jsonify({"message": alert_text})


@alert_endpoints.route("/remove_alert", methods=["POST"])
@twitch_auth.twitch_login_required
@use_kwargs({"name": fields.Str(required=True)}, location="json")
def remove_alert_post(**kwargs):
    try:
        alert_name = alerts.remove_alert(**kwargs)
    except Exception as e:
        logger.exception(e)
        raise InvalidUsage(str(e))
    return jsonify({"message": f"Alert removed: {alert_name}"})


@alert_endpoints.route("/tag_alert", methods=["POST"])
@twitch_auth.twitch_login_required
@use_kwargs(
    {
        "name": fields.Str(required=True),
        "random_choice": fields.Bool(load_default=True),
        "live": fields.Bool(load_default=True),
    },
    location="json",
)
def tag_alert_post(**kwargs):
    try:
        alert_text = alerts.tag_alert(**kwargs)
        if not alert_text:
            alert_text = "Displayed alert"
    except Exception as e:
        logger.exception(e)
        raise InvalidUsage(str(e))
    return jsonify({"message": alert_text})


@alert_endpoints.route("/tag_details", methods=["GET"])
@twitch_auth.twitch_login_required
@use_kwargs(
    {
        "name": fields.Str(required=True),
    },
    location="query",
)
def tag_details_get(**kwargs):
    try:
        tag = alerts.tag_details(**kwargs)
    except Exception as e:
        logger.exception(e)
        raise InvalidUsage(str(e))
    return jsonify({"tag": tag})


@alert_endpoints.route("/save_tag", methods=["POST"])
@twitch_auth.twitch_login_required
@use_kwargs(
    {
        "name": fields.Str(required=True),
        "thumbnail": fields.Str(allow_none=True),
        "category": fields.Str(required=True, validate=validate.OneOf(alerts.TAG_CATEGORIES)),
        "alerts": fields.List(fields.Str),
    },
    location="json",
)
def save_tag_post(**kwargs):
    try:
        tag = alerts.save_tag(**kwargs)
    except Exception as e:
        logger.exception(e)
        raise InvalidUsage(str(e))
    return jsonify({"message": f"Tag saved: {tag.name}"})


@alert_endpoints.route("/remove_tag", methods=["POST"])
@twitch_auth.twitch_login_required
@use_kwargs({"name": fields.Str(required=True)}, location="json")
def remove_tag_post(**kwargs):
    try:
        tag_name = alerts.remove_tag(**kwargs)
    except Exception as e:
        logger.exception(e)
        raise InvalidUsage(str(e))
    return jsonify({"message": f"Tag removed: {tag_name}"})
