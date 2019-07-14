from gevent import monkey
monkey.patch_all()

from flask import Flask
from flask import jsonify
from flask_cors import CORS
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

from custom_stream_api import settings

app = None
socketio = None
db = SQLAlchemy()
migrate = None
g = {}


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
        rv['message'] = self.message
        return rv


def create_app(init_db=True):
    global app, socketio, db, migrate, g

    app = Flask(__name__)
    CORS(app, resources={r'/*': {'origins': '*'}})

    app.config['SECRET_KEY'] = settings.SECRET
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    if init_db:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
        db.init_app(app)
    migrate = Migrate(app, db)
    migrate.directory = 'custom_stream_api/migrations'
    socketio = SocketIO(app)

    from custom_stream_api.alerts.views import alert_endpoints
    from custom_stream_api.lists.views import lists_endpoints
    from custom_stream_api.counts.views import counts_endpoints
    from custom_stream_api.chatbot.views import chatbot_endpoints
    from custom_stream_api.notifier.views import notifier_endpoints
    app.register_blueprint(alert_endpoints, url_prefix='/alerts')
    app.register_blueprint(lists_endpoints, url_prefix='/lists')
    app.register_blueprint(counts_endpoints, url_prefix='/counts')
    app.register_blueprint(chatbot_endpoints, url_prefix='/chatbot')
    app.register_blueprint(notifier_endpoints, url_prefix='/notifier')

    @app.errorhandler(InvalidUsage)
    def handle_invalid_usage(error):
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response

    return app, socketio, db, migrate, g


def get_chatbot():
    if g.get('chatbot') and g['chatbot'].get('object') and g['chatbot']['object'].running():
        return g['chatbot']['object']
