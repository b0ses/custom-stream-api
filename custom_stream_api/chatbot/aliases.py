from custom_stream_api.chatbot.models import Alias, BADGE_NAMES
from custom_stream_api.shared import db, get_app


def list_aliases():
    return [alias.as_dict() for alias in db.session.query(Alias).order_by(Alias.command.asc()).all()]


def add_alias(alias, command, badge, save=True):
    found_alias = db.session.query(Alias).filter_by(alias=alias).one_or_none()
    if found_alias:
        found_alias.command = command
        found_alias.badge = badge
    else:
        if badge not in BADGE_NAMES:
            raise Exception("Badge '{}' not available.".format(badge))
        new_alias = Alias(alias=alias, command=command, badge=badge)
        db.session.add(new_alias)
    if save:
        db.session.commit()

        app = get_app()
        twitch_chatbot = getattr(app, "twitch_chatbot", None)
        if twitch_chatbot:
            twitch_chatbot.update_commands()
    return alias


def remove_alias(alias):
    found_alias = db.session.query(Alias).filter_by(alias=alias)
    if found_alias.count():
        found_alias.delete()
        db.session.commit()

        app = get_app()
        twitch_chatbot = getattr(app, "twitch_chatbot", None)
        if twitch_chatbot:
            twitch_chatbot.update_commands()
        return alias
