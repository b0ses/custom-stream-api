import logging
import uvicorn

from custom_stream_api import settings
from custom_stream_api.shared import create_app, run_socket_io_thread

from custom_stream_api.chatbot.twitchbot import run_twitchbot_thread
from custom_stream_api.chatbot.timers import run_scheduler

app, sio, db = create_app()

logger = logging.getLogger(__name__)

if sio:
    run_socket_io_thread(app, sio)

if settings.TWITCH_CLIENT_SECRET:
    app.twitch_chatbot = run_twitchbot_thread(app, db)

run_scheduler(app, db)

if __name__ == "__main__":
    if not settings.SECRET:
        logger.error("Go to settings and fill in the SECRET with something.")
        exit()

    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
