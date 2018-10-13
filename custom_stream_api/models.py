from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Alert(db.Model):
    name = db.Column(db.String(128), primary_key=True)
    text = db.Column(db.String(128))
    sound = db.Column(db.String(128))
    image = db.Column(db.String(128))

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
