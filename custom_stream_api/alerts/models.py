from custom_stream_api.shared import db

from custom_stream_api.shared import Base
from sqlalchemy.sql import func

from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint, Boolean, Text
from sqlalchemy.orm import relationship


class Alert(Base):
    __tablename__ = "alert"
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, unique=True, nullable=False)
    text = Column(Text, nullable=False)
    sound = Column(Text)
    image = Column(Text)
    thumbnail = Column(Text)
    effect = Column(Text)

    tags = relationship("TagAssociation", cascade="all,delete", backref="alert")

    def as_dict(self):
        alert_dict = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        tags_query = (
            db.session.query(Tag.name)
            .join(TagAssociation)
            .filter(TagAssociation.alert_name == alert_dict["name"])
            .order_by(Tag.name)
        )
        alert_dict["tags"] = [result[0] for result in tags_query]
        return alert_dict


class Tag(Base):
    __tablename__ = "tag"
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, unique=True, nullable=False)
    display_name = Column(Text, nullable=False)
    thumbnail = Column(Text)
    category = Column(Text)
    current_index = Column(Integer, default=0)
    counts = relationship("Count", backref="tag")
    always_chat = Column(Boolean, default=False, nullable=False, server_default="f")
    chat_message = Column(Text)

    alerts = relationship("TagAssociation", cascade="all,delete", backref="tag")

    def as_dict(self):
        tag_dict = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        alerts_query = (
            db.session.query(Alert.name)
            .join(TagAssociation)
            .filter(TagAssociation.tag_name == tag_dict["name"])
            .order_by(Alert.name)
        )
        tag_dict["alerts"] = [result[0] for result in alerts_query]
        return tag_dict


class TagAssociation(Base):
    __tablename__ = "tag_association"
    id = Column(Integer, primary_key=True, autoincrement=True)
    tag_name = Column(Text, ForeignKey("tag.name", ondelete="CASCADE"), nullable=False)
    alert_name = Column(Text, ForeignKey("alert.name", ondelete="CASCADE"), nullable=False)
    __table_args__ = (UniqueConstraint("tag_name", "alert_name", name="_tag_uc"),)
