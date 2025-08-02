from custom_stream_api.shared import Base
from sqlalchemy.sql import func

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text


class Count(Base):
    __tablename__ = "count"
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    name = Column(Text, unique=True, nullable=False)
    count = Column(Integer, default=0)
    tag_name = Column(Text, ForeignKey("tag.name", name="tag_count_fk"))

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
