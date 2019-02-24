import logging

from custom_stream_api import settings
from custom_stream_api.shared import create_app, setup_chatbot

app, socketio, _, _, g = create_app()

logger = logging.getLogger()

if __name__ == '__main__':
    if not settings.SECRET:
        logger.error('Go to settings and fill in the SECRET with something.')
        exit()
    setup_chatbot(app, g)
    socketio.run(app, host=settings.HOST, port=settings.PORT, debug=settings.DEBUG)
