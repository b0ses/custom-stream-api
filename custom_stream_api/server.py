from gevent import monkey
monkey.patch_all()

import logging

from custom_stream_api import settings
from custom_stream_api.shared import create_app

app, socketio, _, _, _ = create_app()

logger = logging.getLogger()

if __name__ == '__main__':
    if not settings.SECRET:
        logger.error('Go to settings and fill in the SECRET with something.')
        exit()
    socketio.run(app, host=settings.HOST, port=settings.PORT, debug=settings.DEBUG)
