import logging
import logging.config
import os
from alembic.config import Config
from alembic import command
from flask import Flask
from flask import jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import declarative_base

from custom_stream_api import settings

app = None
socketio = None
db = SQLAlchemy()
g = {}
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
    "handlers": {
        "console": {"formatter": "default", "class": "logging.StreamHandler"}
    },
    "loggers": {
        # i.e. "all modules"
        "": {"handlers": ["console"], "level": "INFO", "propagate": True},
        "../custom_stream_api": {"handlers": ["console"], "level": "DEBUG", "propagate": True},
        "__main__": {"level": "DEBUG", "propagate": True},
    },
}


def create_app(**settings_override):
    global app, socketio, db, g  # noqa: F824

    app = Flask(__name__)

    for setting, value in settings_override.items():
        app.config[setting] = value

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
    CORS(app, origins=origins, supports_credentials=True)

    app.config["SECRET_KEY"] = settings.SECRET
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if not app.config.get("SQLALCHEMY_DATABASE_URI", ""):
        app.config["SQLALCHEMY_DATABASE_URI"] = settings.DB_URI
    db.init_app(app)
    socketio = SocketIO(app, cors_allowed_origins=origins, cors_credentials=True, engineio_logger=False, logger=False)
    # DO NOT REMOVE. Flask-SocketIO needs the namespaces to have handlers on them to emit from them. It's silly.
    socketio.on_event("FromAPI", lambda data: None, namespace="/live")
    socketio.on_event("FromAPI", lambda data: None, namespace="/preview")

    # write to app.log if local
    if settings.HOST == '127.0.0.1':
        DEFAULT_CONFIG['handlers']['file'] = {
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
    from custom_stream_api.notifier.views import notifier_endpoints
    from custom_stream_api.auth.views import auth_endpoints

    # from custom_stream_api.lights.views import lights_endpoints
    app.register_blueprint(alert_endpoints, url_prefix="/alerts")
    app.register_blueprint(lists_endpoints, url_prefix="/lists")
    app.register_blueprint(counts_endpoints, url_prefix="/counts")
    app.register_blueprint(chatbot_endpoints, url_prefix="/chatbot")
    app.register_blueprint(notifier_endpoints, url_prefix="/notifier")
    app.register_blueprint(auth_endpoints, url_prefix="/auth")
    # app.register_blueprint(lights_endpoints, url_prefix='/lights')

    @app.errorhandler(InvalidUsage)
    def handle_invalid_usage(error):
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response

    return app, socketio, db, g


def get_chatbot():
    if g.get("chatbot") and g["chatbot"].get("object") and g["chatbot"]["object"].running():
        return g["chatbot"]["object"]
