from custom_stream_api.shared import db


class Alert(db.Model):
    name = db.Column(db.String(128), primary_key=True, nullable=False)
    text = db.Column(db.String(128))
    sound = db.Column(db.String(128))
    image = db.Column(db.String(128))
    duration = db.Column(db.Integer)
    thumbnail = db.Column(db.String(128))
    effect = db.Column(db.String(128))

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class GroupAlert(db.Model):
    group_name = db.Column(db.String(128), primary_key=True, nullable=False)
    alerts = db.relationship('GroupAlertAssociation', cascade='all,delete', backref='group_alert')
    thumbnail = db.Column(db.String(128))

    def as_dict(self):
        name = getattr(self, 'group_name')
        alerts_query = db.session.query(GroupAlertAssociation.alert_name).filter_by(group_name=name)\
            .order_by(GroupAlertAssociation.index)
        alerts = [result[0] for result in alerts_query]
        thumbnail = getattr(self, 'thumbnail')
        return {'name': name, 'alerts': alerts, 'thumbnail': thumbnail}


class GroupAlertAssociation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_name = db.Column(db.String(128), db.ForeignKey('group_alert.group_name'), nullable=False)
    alert_name = db.Column(db.String(128), db.ForeignKey('alert.name'), nullable=False)
    index = db.Column(db.Integer)
    __table_args__ = (
        db.UniqueConstraint('group_name', 'alert_name', name='_group_alert_uc'),
    )
