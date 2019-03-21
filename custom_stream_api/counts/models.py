from custom_stream_api.shared import db

class Count(db.Model):
    name = db.Column(db.String(128), primary_key=True, nullable=False)
    count = db.Column(db.Integer, default=0)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
