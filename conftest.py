import os
import tempfile
import pytest
from flask_migrate import upgrade

from custom_stream_api.shared import create_app


@pytest.fixture(scope='session')
def app(request):
    db_fd, temp_db_path = tempfile.mkstemp()
    settings_override = {
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///{}'.format(temp_db_path),
        'TESTING': True
    }
    app, socketio, db, migrate, _ = create_app(init_db=False)
    for setting in settings_override:
        app.config[setting] = settings_override[setting]

    ctx = app.app_context()
    ctx.push()
    db.init_app(app)
    upgrade(migrate.directory)

    def teardown():
        db.drop_all()
        ctx.pop()
        os.close(db_fd)
        os.remove(temp_db_path)

    request.addfinalizer(teardown)
