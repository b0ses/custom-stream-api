import threading
import traceback

from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask import jsonify

from custom_stream_api import settings

app = None
socketio = None
db = None
migrate = None
g = {
    'chatbot': None
}


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


def start_chatbot_with_app(app, chatbot):
    with app.app_context():
        chatbot.start()


def create_app(init_db=True):
    global app, socketio, db, migrate, g

    app = Flask(__name__)
    CORS(app, resources={r'/*': {'origins': '*'}})

    app.config['SECRET_KEY'] = settings.SECRET
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db = SQLAlchemy()
    if init_db:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
        db.init_app(app)
    migrate = Migrate(app, db)
    migrate.directory = 'custom_stream_api/migrations'
    socketio = SocketIO(app)

    from custom_stream_api.alerts.views import alert_endpoints
    app.register_blueprint(alert_endpoints, url_prefix='/alerts')

    from custom_stream_api import twitchbot
    chatbot_settings = {
        'username': settings.USERNAME,
        'client_id': settings.CLIENT_ID,
        'token': settings.TOKEN,
        'channel': settings.CHANNEL,
        'timeout': settings.TIMEOUT
    }
    try:
        g['chatbot'] = twitchbot.TwitchBot(**chatbot_settings)
        chatbot_t = threading.Thread(target=start_chatbot_with_app, args=(app, g['chatbot'],))
        chatbot_t.start()
    except Exception as e:
        print(traceback.print_exc())
        print('Unable to start chatbot. Please update your chatbot settings.')

    @app.errorhandler(InvalidUsage)
    def handle_invalid_usage(error):
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response

    return app, socketio, db, migrate


create_app()
