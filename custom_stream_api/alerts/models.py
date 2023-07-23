from custom_stream_api.shared import db

from custom_stream_api.shared import Base
from sqlalchemy.sql import func

from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint, Boolean, Text
from sqlalchemy.orm import relationship


class Alert(Base):
    __tablename__ = "alert"
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    name = Column(Text, primary_key=True, nullable=False)
    text = Column(Text)
    sound = Column(Text)
    image = Column(Text)
    duration = Column(Integer, default=500)
    thumbnail = Column(Text)
    effect = Column(Text)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class GroupAlert(Base):
    __tablename__ = "group_alert"
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    group_name = Column(Text, primary_key=True, nullable=False)
    alerts = relationship("GroupAlertAssociation", cascade="all,delete", backref="group_alert")
    thumbnail = Column(Text)
    current_index = Column(Integer, default=0)
    counts = relationship("Count", backref="group_alert")
    always_chat = Column(Boolean, default=False, nullable=False, server_default="f")
    chat_message = Column(Text)

    def as_dict(self):
        name = getattr(self, "group_name")
        alerts_query = (
            db.session.query(GroupAlertAssociation.alert_name)
            .filter_by(group_name=name)
            .order_by(GroupAlertAssociation.index)
        )
        alerts = [result[0] for result in alerts_query]
        thumbnail = getattr(self, "thumbnail")
        always_chat = getattr(self, "always_chat")
        chat_message = getattr(self, "chat_message")
        return {
            "name": name,
            "alerts": alerts,
            "thumbnail": thumbnail,
            "always_chat": always_chat,
            "chat_message": chat_message,
        }


class GroupAlertAssociation(Base):
    __tablename__ = "group_alert_association"
    id = Column(Integer, primary_key=True)
    group_name = Column(Text, ForeignKey("group_alert.group_name"), nullable=False)
    alert_name = Column(Text, ForeignKey("alert.name"), nullable=False)
    index = Column(Integer)
    __table_args__ = (UniqueConstraint("group_name", "alert_name", name="_group_alert_uc"),)
