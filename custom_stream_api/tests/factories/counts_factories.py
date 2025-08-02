import factory
import datetime as dt

from custom_stream_api.counts import models


class CountFactory(factory.Factory):
    class Meta:
        model = models.Count

    id = factory.Faker("random_number")
    created_at = factory.Faker("date_time", tzinfo=dt.timezone.utc)
    name = factory.Faker("word")
    count = factory.Faker("random_number")
    tag_name = factory.Faker("word")
