from custom_stream_api.shared import db


class Alias(db.Model):
    alias = db.Column(db.String(128), primary_key=True, nullable=False)
    command = db.Column(db.String(128), nullable=False)
    badge = db.Column(db.String(128), nullable=False)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
