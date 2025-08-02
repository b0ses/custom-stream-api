import pytest
from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.orm import sessionmaker, close_all_sessions, scoped_session

from custom_stream_api.settings import DB_URI
from custom_stream_api.shared import create_app, run_migrations, db as _db

TEST_DB_NAME = f"test_{DB_URI.split('/')[-1]}"
TEST_DB_URI = "/".join(DB_URI.split("/")[:-1]) + "/" + TEST_DB_NAME

metadata = MetaData()


def create_test_db():
    engine = create_engine(DB_URI)
    with engine.connect() as con:
        con.execute(text("commit;"))
        con.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}"))
        con.execute(text("commit"))
        con.execute(text(f"CREATE DATABASE {TEST_DB_NAME}"))


def teardown_test_db():
    engine = create_engine(DB_URI)
    with engine.connect() as con:
        con.execute(text("commit"))
        con.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}"))
        con.execute(text("commit"))


@pytest.fixture(scope="session")
def app(request):
    """Session-wide test `Flask` application."""
    settings_override = {"TESTING": True, "SQLALCHEMY_DATABASE_URI": TEST_DB_URI}
    app, _, _, _ = create_app(**settings_override)

    # Establish an application context before running the tests.
    ctx = app.app_context()
    ctx.push()

    yield app

    ctx.pop()


@pytest.fixture(scope="module")
def db(app, request):
    """Session-wide test database."""
    create_test_db()

    run_migrations(TEST_DB_URI)
    _db.app = app
    _db.create_all()

    yield _db

    _db.engine.dispose()
    teardown_test_db()


@pytest.fixture(scope="function")
def session(db, request):
    """Creates a new database session for a test."""

    with db.engine.connect() as connection:
        session = scoped_session(sessionmaker(bind=connection, binds={}))
        with connection.begin() as transaction:
            db.session = session

            yield session

            transaction.rollback()

        with connection.begin() as transaction:
            metadata.reflect(db.engine)
            for table in metadata.tables.keys():
                if table == "alembic_version":
                    continue
                connection.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;"))
            transaction.commit()

        db.session.flush()
        db.session.close()

    db.drop_all()
    close_all_sessions()
