import logging
import threading
from cron_converter import Cron
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from zoneinfo import ZoneInfo


from custom_stream_api.settings import TIMER_TZ
from custom_stream_api.chatbot.models import Timer
from custom_stream_api.shared import run_async_in_thread, db

logger = logging.getLogger(__name__)

# redundant but allows different variable names
SUPPORTED_BOTS = {
    "twitch_chatbot": "twitch_chatbot",
    "discord_chatbot": "discord_chatbot",
}


INTERRUPTER = threading.Event()

TZ = ZoneInfo(TIMER_TZ) if TIMER_TZ else None


def list_timers():
    return [timer.as_dict() for timer in db.session.query(Timer).order_by(Timer.command.asc()).all()]


# Note: Next time values in the database are *not* UTC like the rest of the database, it's relative to TIMER_TZ
def calculate_next_time(cron):
    now = datetime.now(TZ)
    cron_instance = Cron(cron)
    schedule = cron_instance.schedule(now)
    return schedule.next()


def check_timers(app, db, execute=True):
    now = datetime.now(TZ)
    timers = db.session.query(Timer).filter(Timer.next_time <= now, Timer.active.is_(True))
    for timer in timers:
        if execute:
            logger.info(f"Executing timer: {timer.bot_name} {timer.command}")
            bot = getattr(app, SUPPORTED_BOTS[timer.bot_name])
            bot.do_command(timer.command, bot.name, [], ignore_badges=True)

        cron_next_time = calculate_next_time(timer.cron)
        if not cron_next_time or not timer.repeat:
            # timer's run out, remove it
            db.session.query(Timer).filter(Timer.id == timer.id).delete()
        else:
            timer.next_time = cron_next_time
    db.session.commit()


def add_timer(bot_name, command, cron, repeat=False, save=True):
    if bot_name not in SUPPORTED_BOTS:
        raise ValueError(f"Invalid bot_name: {bot_name}")
    found_timer = db.session.query(Timer).filter_by(bot_name=bot_name, command=command).one_or_none()
    if found_timer:
        found_timer.cron = cron
    else:
        new_timer = Timer(
            bot_name=bot_name,
            command=command,
            cron=cron,
            next_time=calculate_next_time(cron),
            active=True,
            repeat=repeat,
        )
        db.session.add(new_timer)
    if save:
        db.session.commit()
        ping_scheduler()

    return command


def remove_timer(bot_name, command):
    if bot_name not in SUPPORTED_BOTS:
        raise ValueError(f"Invalid bot_name: {bot_name}")
    found_timer = db.session.query(Timer).filter_by(bot_name=bot_name, command=command)
    if found_timer.count():
        found_timer.delete()
        db.session.commit()

        ping_scheduler()
    else:
        raise Exception(f"Timer not found: {bot_name} {command}")
    return command


async def scheduler_in_background(app, scheduler_event):
    """Run in background, check for things to run when interrupted by signal or the earliest timer finishes"""
    logger.info("Running scheduler in background")

    with app.flask_app.app_context():
        while True:
            # Refresh database connection
            db.session.commit()

            # Check if there are any timers to run and execute them
            check_timers(app, db, execute=True)

            if db.session.query(Timer).count():
                # If there are timers, wait until the earliest timer or an interruption
                next_time = db.session.query(Timer.next_time).order_by(Timer.next_time.asc()).first()[0]
                now = datetime.now(TZ)
                time_to_wait = (next_time - now).total_seconds()
                logger.info(f"Waiting for next signal: {time_to_wait}")
            else:
                # If there are no timers, just wait till we get one
                time_to_wait = None
                logger.info("No timers found. Waiting for a timer to be made.")

            # if await event_wait_with_timeout(scheduler_event, time_to_wait):
            if scheduler_event.wait(time_to_wait):
                logger.info("RECEIVED INTERRUPTION")
                # prep for the next cycle which will be the next timer or an interruption
                scheduler_event.clear()
                continue


def ping_scheduler():
    # logger.info('SENDING INTERRUPTION')
    INTERRUPTER.set()


def run_scheduler(app, db):
    # Check for any outdated timers the first time and don't execute them.
    with app.flask_app.app_context():
        check_timers(app, db, execute=False)
    run_async_in_thread(scheduler_in_background, app, INTERRUPTER)
