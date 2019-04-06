from custom_stream_api.chatbot.models import Alias, BADGE_NAMES
from custom_stream_api.shared import db, g


def list_aliases():
    return [alias.as_dict() for alias in db.session.query(Alias).order_by(Alias.command.asc()).all()]


def import_aliases(aliases):
    for alias_dict in aliases:
        add_alias(**alias_dict, save=False)
    db.session.commit()
    if 'chatbot' in g:
        g['chatbot'].set_aliases()


def add_alias(alias, command, badge, save=True):
    found_alias = db.session.query(Alias).filter_by(alias=alias).one_or_none()
    if found_alias:
        found_alias.command = command
        found_alias.badge = badge
    else:
        if badge not in BADGE_NAMES:
            raise Exception('Badge \'{}\' not available.'.format(badge))
        new_alias = Alias(alias=alias, command=command, badge=badge)
        db.session.add(new_alias)
    if save:
        db.session.commit()
        if 'chatbot' in g:
            g['chatbot'].set_aliases()
    return alias


def remove_alias(alias):
    found_alias = db.session.query(Alias).filter_by(alias=alias)
    if found_alias.count():
        found_alias.delete()
        db.session.commit()
        if 'chatbot' in g:
            g['chatbot'].set_aliases()
        return alias
