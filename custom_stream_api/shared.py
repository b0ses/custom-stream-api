from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO

from custom_stream_api import settings

app = None
socketio = None
db = None
migrate = None


def create_app(init_db=True):
    global app, socketio, db, migrate

    app = Flask(__name__)
    CORS(app, resources={r'/*': {'origins': '*'}})

    app.config['SECRET_KEY'] = settings.SECRET
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db = SQLAlchemy()
    if init_db:
        db.init_app(app)
    migrate = Migrate(app, db)
    socketio = SocketIO(app)

    from custom_stream_api.alerts.views import alert_endpoints
    app.register_blueprint(alert_endpoints, url_prefix='/alerts')

    return app, socketio, db, migrate


create_app()
