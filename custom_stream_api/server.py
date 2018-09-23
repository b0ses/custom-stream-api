import logging
from flask import Flask, request
from flask_cors import CORS
from flask_socketio import SocketIO

from custom_stream_api import settings

app = Flask(__name__)
logger = logging.getLogger()

app.config['SECRET_KEY'] = settings.SECRET
socketio = SocketIO(app)


@app.route('/alert', methods=['POST'])
@cross_origin()
def alert():
    if request.method == 'POST':
        data = request.get_json()
        message = data.get('message')
        socketio.emit('FromAPI', {"message": message}, namespace='/', broadcast=True)
        return "Message Received"


if __name__ == '__main__':
    if not settings.SECRET:
        logger.error('Go to settings and fill in the SECRET with something.')
        exit()
    socketio.run(app, host=settings.HOST, port=settings.PORT)
