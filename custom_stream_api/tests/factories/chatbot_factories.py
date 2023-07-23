import factory
import datetime as dt

from custom_stream_api.chatbot import models


class AliasFactory(factory.Factory):
    class Meta:
        model = models.Alias

    created_at = factory.Faker("date_time", tzinfo=dt.timezone.utc)
    alias = factory.Faker("word")
    command = factory.Faker("text")
    badge = factory.Faker("random_choices", elements=models.BADGE_NAMES)


class TimerFactory(factory.Factory):
    class Meta:
        model = models.Timer

    created_at = factory.Faker("date_time", tzinfo=dt.timezone.utc)
    command = factory.Faker("text")
    interval = factory.Faker("random_number")
