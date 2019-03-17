from custom_stream_api.shared import db


class Alias(db.Model):
    alias = db.Column(db.String(128), primary_key=True, nullable=False)
    command = db.Column(db.String(128), nullable=False)
    badge = db.Column(db.String(128), nullable=False)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class List(db.Model):
    name = db.Column(db.String(128), primary_key=True, nullable=False)
    items = db.relationship('ListItem', cascade='all,delete', backref='group_alert')
    current_index = db.Column(db.Integer, default=0)

    def as_dict(self):
        name = getattr(self, 'name')
        items_query = db.session.query(ListItem.item).filter_by(list_name=name).order_by(ListItem.index)
        items = [result[0] for result in items_query]
        return {'name': name, 'items': items}

class ListItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    list_name = db.Column(db.String(128), db.ForeignKey('list.name'), nullable=False)
    index = db.Column(db.Integer, nullable=False)
    item = db.Column(db.String(128), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('list_name', 'index', name='_lists_uc'),
    )

class Count(db.Model):
    name = db.Column(db.String(128), primary_key=True, nullable=False)
    count = db.Column(db.Integer, default=0)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
