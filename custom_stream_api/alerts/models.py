from custom_stream_api.shared import db


class Alert(db.Model):
    name = db.Column(db.String(128), primary_key=True, nullable=False)
    text = db.Column(db.String(128))
    sound = db.Column(db.String(128))
    image = db.Column(db.String(128))
    duration = db.Column(db.Integer)
    effect = db.Column(db.String(128))

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
