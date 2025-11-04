import asyncio
import janus
import logging
import logging.config
import os
import socketio
import threading

from alembic.config import Config
from alembic import command
from flask import Flask
from flask import jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import declarative_base
from asgiref.wsgi import WsgiToAsgi

from custom_stream_api import settings

app = None
db = SQLAlchemy()
Base = declarative_base()
APP_DIR = os.path.dirname(os.path.abspath(__file__))


class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv["message"] = self.message
        return rv


def run_migrations(dsn: str) -> None:
    alembic_cfg = Config(os.path.join(APP_DIR, "alembic.ini"))
    alembic_cfg.set_main_option("script_location", os.path.join(APP_DIR, "migrations"))
    alembic_cfg.set_main_option("test_db_url", dsn)
    command.upgrade(alembic_cfg, "head")


# Reasonable defaults to avoid clutter in our config files
DEFAULT_CONFIG = {
    "version": 1,
    "level": logging.INFO,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {"format": "%(asctime)s %(levelname)s:%(name)s:%(message)s"},
    },
    "handlers": {"console": {"formatter": "default", "class": "logging.StreamHandler"}},
    "loggers": {
        # i.e. "all modules"
        "": {"handlers": ["console"], "level": "INFO", "propagate": True},
        "../custom_stream_api": {"handlers": ["console"], "level": "DEBUG", "propagate": True},
        "__main__": {"level": "DEBUG", "propagate": True},
    },
}

# MAGICAL SYNC -> SYNC


def start_background_task_thread(task, *args, **kwargs):
    """Starts the asyncio event loop for the background task."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(task(*args, **kwargs))


def run_async_in_thread(task, *args, **kwargs):
    thread = threading.Thread(target=start_background_task_thread, args=(task,) + args, kwargs=kwargs, daemon=True)
    thread.start()


# MAGICAL SYNC -> SYNC


async def socket_io_emitter(sio, socketio_queue):
    while True:
        queue_message = await socketio_queue.get()
        await sio.emit("FromAPI", queue_message["data"], namespace=f"/{queue_message['namespace']}")
        socketio_queue.task_done()


def run_socket_io_thread(app, sio):
    app.socketio_queue = janus.Queue()
    run_async_in_thread(socket_io_emitter, sio, app.socketio_queue.async_q)


# In async land, it seems like accessing the global constants among modules isn't available
# So we're including some basic accessors here
def get_app():
    return app


def get_db():
    return db


def create_app(**settings_override):
    global app, db  # noqa: F824

    flask_app = Flask(__name__)

    for setting, value in settings_override.items():
        flask_app.config[setting] = value

    hosts = ["localhost", "127.0.0.1", settings.HOST]
    ports = ["80", settings.DASHBOARD_PORT, settings.OVERLAY_PORT, settings.PREVIEW_PORT]
    protocols = ["http", "https"]

    origins = []
    for protocol in protocols:
        for host in hosts:
            origins.append("{}://{}".format(protocol, host))
            for port in [port for port in ports if port]:
                origins.append("{}://{}:{}".format(protocol, host, port))

    # TODO: Use the commented lines below if flask_socketio supports regex origins
    # origins = ['https?:\/\/{}.*'.format(host) for host in hosts]
    CORS(flask_app, origins=origins, supports_credentials=True)

    flask_app.config["SECRET_KEY"] = settings.SECRET
    flask_app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if not flask_app.config.get("SQLALCHEMY_DATABASE_URI", ""):
        flask_app.config["SQLALCHEMY_DATABASE_URI"] = settings.DB_URI
    db.init_app(flask_app)
    sio = socketio.AsyncServer(
        cors_allowed_origins=origins, cors_credentials=True, engineio_logger=False, logger=False, async_mode="asgi"
    )

    # # DO NOT REMOVE. Flask-SocketIO needs the namespaces to have handlers on them to emit from them. It's silly.
    @sio.on("FromAPI", namespace="/live")
    def live():
        pass

    @sio.on("FromAPI", namespace="/preview")
    def preview():
        pass

    DEFAULT_CONFIG["handlers"]["file"] = {
        "formatter": "default",
        "class": "logging.FileHandler",
        "filename": os.path.join(APP_DIR, "app.log"),
        "mode": "w",
    }
    logging.config.dictConfig(DEFAULT_CONFIG)

    from custom_stream_api.alerts.views import alert_endpoints
    from custom_stream_api.lists.views import lists_endpoints
    from custom_stream_api.counts.views import counts_endpoints
    from custom_stream_api.chatbot.views import chatbot_endpoints
    from custom_stream_api.auth.views import auth_endpoints

    # from custom_stream_api.lights.views import lights_endpoints
    flask_app.register_blueprint(alert_endpoints, url_prefix="/alerts")
    flask_app.register_blueprint(lists_endpoints, url_prefix="/lists")
    flask_app.register_blueprint(counts_endpoints, url_prefix="/counts")
    flask_app.register_blueprint(chatbot_endpoints, url_prefix="/chatbot")
    flask_app.register_blueprint(auth_endpoints, url_prefix="/auth")
    # app.register_blueprint(lights_endpoints, url_prefix='/lights')

    @flask_app.errorhandler(InvalidUsage)
    def handle_invalid_usage(error):
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response

    app = socketio.ASGIApp(
        socketio_server=sio,
        other_asgi_app=WsgiToAsgi(flask_app),
    )
    app.flask_app = flask_app

    return app, sio, db
