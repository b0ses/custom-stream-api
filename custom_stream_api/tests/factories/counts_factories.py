import factory
import datetime as dt

from custom_stream_api.counts import models


class CountFactory(factory.Factory):
    class Meta:
        model = models.Count

    created_at = factory.Faker("date_time", tzinfo=dt.timezone.utc)
    name = factory.Faker("word")
    count = factory.Faker("random_number")
    group_name = factory.Faker("word")
