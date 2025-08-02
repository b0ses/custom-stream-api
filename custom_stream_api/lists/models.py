from custom_stream_api.shared import db
from sqlalchemy.sql import func

from custom_stream_api.shared import Base

from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint, Text
from sqlalchemy.orm import relationship


class List(Base):
    __tablename__ = "list"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    name = Column(Text, unique=True, nullable=False)
    items = relationship("ListItem", cascade="all,delete", backref="tag_alert")
    current_index = Column(Integer, default=0)

    def as_dict(self):
        name = getattr(self, "name")
        items_query = db.session.query(ListItem.item).filter_by(list_name=name).order_by(ListItem.index)
        items = [result[0] for result in items_query]
        return {"name": name, "items": items}


class ListItem(Base):
    __tablename__ = "list_item"

    id = Column(Integer, primary_key=True, autoincrement=True)
    list_name = Column(Text, ForeignKey("list.name"), nullable=False)
    index = Column(Integer, nullable=False)
    item = Column(Text, nullable=False)

    __table_args__ = (UniqueConstraint("list_name", "index", name="_lists_uc"),)
