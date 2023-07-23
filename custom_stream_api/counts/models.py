from custom_stream_api.shared import Base
from sqlalchemy.sql import func

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text


class Count(Base):
    __tablename__ = "count"
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    name = Column(Text, primary_key=True, nullable=False)
    count = Column(Integer, default=0)
    group_name = Column(Text, ForeignKey("group_alert.group_name", name="group_alert_count_fk"))

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
