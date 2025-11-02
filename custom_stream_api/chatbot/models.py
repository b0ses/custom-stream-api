from enum import Enum
from sqlalchemy.sql import func
from sqlalchemy import Column, DateTime, Integer, Text, Boolean
from custom_stream_api.shared import Base


class Badges(Enum):
    CHAT = "chat"
    BITS = "bits"
    BITS_CHARITY = "bits-charity"
    PREMIUM = "premium"
    VERIFIED = "verified"
    BOT = "bot"
    PARTNER = "partner"
    FFZ_SUPPORTER = "ffz_supporter"
    SUBSCRIBER = "subscriber"
    VIP = "vip"
    MODERATOR = "moderator"
    GLOBAL_MODERATOR = "global_mod"
    BROADCASTER = "broadcaster"
    STAFF = "staff"
    ADMINISTRATOR = "admin"


BADGE_LEVELS = [
    Badges.CHAT,
    Badges.BITS,
    Badges.BITS_CHARITY,
    Badges.PREMIUM,
    Badges.VERIFIED,
    Badges.BOT,
    Badges.FFZ_SUPPORTER,
    Badges.PARTNER,
    Badges.SUBSCRIBER,
    Badges.VIP,
    Badges.MODERATOR,
    Badges.GLOBAL_MODERATOR,
    Badges.BROADCASTER,
    Badges.STAFF,
    Badges.ADMINISTRATOR,
]
BADGE_NAMES = [badge.value for badge in BADGE_LEVELS]


class Alias(Base):
    __tablename__ = "alias"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    alias = Column(Text, unique=True, nullable=False)
    command = Column(Text, nullable=False)
    badge = Column(Text, nullable=False)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Timer(Base):
    __tablename__ = "timer"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    bot_name = Column(Text, unique=True, nullable=False)
    command = Column(Text, unique=True, nullable=False)
    cron = Column(Text, nullable=False)
    next_time = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    repeat = Column(Boolean, default=True, nullable=False)
    active = Column(Boolean, default=True, nullable=False)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
