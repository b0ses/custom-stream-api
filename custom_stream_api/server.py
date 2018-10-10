import logging
from flask import Flask, request
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_migrate import Migrate

from custom_stream_api.models import db
from custom_stream_api import settings

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
logger = logging.getLogger()

app.config['SECRET_KEY'] = settings.SECRET
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
socketio = SocketIO(app)
db.init_app(app)
migrate = Migrate(app, db)


@app.route('/alert', methods=['POST'])
def alert():
    if request.method == 'POST':
        data = request.get_json()
        socket_data = {
            'message': data.get('message'),
            'sound': data.get('sound'),
            'effect': data.get('effect'),
            'duration': data.get('duration')
        }
        socketio.emit('FromAPI', socket_data, namespace='/', broadcast=True)
        return "Message Received"


if __name__ == '__main__':
    if not settings.SECRET:
        logger.error('Go to settings and fill in the SECRET with something.')
        exit()
    socketio.run(app, host=settings.HOST, port=settings.PORT)
