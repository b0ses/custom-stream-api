from custom_stream_api.chatbot.models import Timer
from custom_stream_api.shared import db, g


def list_timers():
    return [timer.as_dict() for timer in db.session.query(Timer).order_by(Timer.command.asc()).all()]


def import_timers(timers):
    for timer_dict in timers:
        add_timer(**timer_dict, save=False)
    db.session.commit()
    if 'chatbot' in g:
        g['chatbot'].restart_timers()


def add_timer(command, interval=30, save=True):
    found_timer = db.session.query(Timer).filter_by(command=command).one_or_none()
    if found_timer:
        found_timer.command = command
        found_timer.interval = interval
    else:
        new_timer = Timer(command=command, interval=interval)
        db.session.add(new_timer)
    if save:
        db.session.commit()
        if 'chatbot' in g:
            g['chatbot'].restart_timers()
    return command


def remove_timer(command):
    found_timer = db.session.query(Timer).filter_by(command=command)
    if found_timer.count():
        found_timer.delete()
        db.session.commit()
        if 'chatbot' in g:
            g['chatbot'].restart_timers()
        return command
