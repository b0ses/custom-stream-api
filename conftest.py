import os
import tempfile
import pytest
from flask_migrate import upgrade

from custom_stream_api.shared import create_app


@pytest.fixture
def test_client():
    app, socketio, db, migrate = create_app(init_db=False)
    db_fd, temp_db_path = tempfile.mkstemp()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///{}'.format(temp_db_path)
    app.config['TESTING'] = True
    client = app.test_client()

    with app.app_context():
        db.init_app(app)
        upgrade(migrate.directory)

    yield client

    os.close(db_fd)
    os.unlink(app.config['DATABASE'])


@pytest.fixture
def test_app():
    app, socketio, db, migrate = create_app(init_db=False)
    db_fd, temp_db_path = tempfile.mkstemp()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///{}'.format(temp_db_path)
    app.config['TESTING'] = True

    with app.app_context():
        db.init_app(app)
        upgrade(migrate.directory)

    yield app

    os.close(db_fd)
    os.unlink(temp_db_path)
