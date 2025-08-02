import logging

from custom_stream_api import settings
from custom_stream_api.shared import create_app

app, socketio, _, _ = create_app()

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    if not settings.SECRET:
        logger.error("Go to settings and fill in the SECRET with something.")
        exit()
    socketio.run(app, host=settings.HOST, port=settings.PORT, debug=settings.DEBUG)
