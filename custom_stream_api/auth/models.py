from sqlalchemy import Column, Integer, Text
from custom_stream_api.shared import Base


class RefreshToken(Base):
    __tablename__ = "refresh_token"

    id = Column(Integer, primary_key=True, autoincrement=True)
    app = Column(Text, unique=True, nullable=False)
    refresh_token = Column(Text, unique=True, nullable=False)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
