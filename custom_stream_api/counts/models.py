from custom_stream_api.shared import db
from sqlalchemy import ForeignKey


class Count(db.Model):
    name = db.Column(db.String(128), primary_key=True, nullable=False)
    count = db.Column(db.Integer, default=0)
    group_name = db.Column(db.String(128), ForeignKey('group_alert.group_name', name='group_alert_count_fk'))

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
