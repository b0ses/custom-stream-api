import janus
import logging

from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.type import AuthScope, ChatEvent
from twitchAPI.chat import Chat, EventData, ChatMessage

from custom_stream_api import settings
from custom_stream_api.auth.models import RefreshToken
from custom_stream_api.auth.twitch_auth import TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET

from custom_stream_api.chatbot.chatbot import ChatBot
from custom_stream_api.shared import run_async_in_thread

USER_SCOPE = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT]

chatter = None
chatbot_instance = None

logger = logging.getLogger(__name__)


# this will be called when the event READY is triggered, which will be on bot start
async def on_ready(ready_event: EventData):
    await ready_event.chat.join_room(settings.CHANNEL)

    chatbot_instance.start()


# this will be called whenever a message in a channel was send by either the bot OR another user
async def on_message(msg: ChatMessage):
    badges = [badge for badge in chatbot_instance.badge_levels if badge.value in msg.user.badges.keys()]

    chatbot_instance.parse_message(msg.user.name, msg.text, badges)


# this is where we set up the bot
async def run(app, db, chatbot_queue):
    twitch = await Twitch(TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET)
    auth = UserAuthenticator(twitch, USER_SCOPE)

    # check if there's a refresh token still around we can use
    with app.flask_app.app_context():
        refresh_token = db.session.query(RefreshToken).filter_by(app="twitchbot").one_or_none()
        if not refresh_token:
            # set up twitch api instance and add user authentication with some scopes
            token, refresh_token = await auth.authenticate()
            db.session.add(RefreshToken(app="twitchbot", refresh_token=refresh_token))
            db.session.commit()

            await twitch.set_user_authentication(token, USER_SCOPE, refresh_token)
        else:
            # we're relying on the refresh token to reset everything
            token = ""
            await twitch.set_user_authentication(token, USER_SCOPE, refresh_token.refresh_token)
            refresh_token.refresh_token = twitch._user_auth_refresh_token
            db.session.commit()

    # create chat instance
    chatter = await Chat(twitch, initial_channel=[settings.CHANNEL])

    # register the handlers for the events you want
    chatter.register_event(ChatEvent.READY, on_ready)
    chatter.register_event(ChatEvent.MESSAGE, on_message)

    # we are done with our setup, lets start this bot up!
    chatter.start()

    # lets run till we press enter in the console
    try:
        # check for messages on the queue
        while True:
            message = await chatbot_queue.get()
            await chatter.send_message(room=settings.CHANNEL, text=message)
            chatbot_queue.task_done()
    finally:
        # now we can close the chat bot and the twitch api client
        chatter.stop()
        await twitch.close()


def run_twitchbot_thread(app, db):
    global chatbot_instance

    twitchbot_queue = janus.Queue()
    chatbot_instance = ChatBot(queue=twitchbot_queue.sync_q)

    run_async_in_thread(run, app, db, twitchbot_queue.async_q)

    return chatbot_instance
