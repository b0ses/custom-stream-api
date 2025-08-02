import factory
import datetime as dt

from custom_stream_api.lists import models


class ListFactory(factory.Factory):
    class Meta:
        model = models.List

    id = factory.Faker("random_number")
    created_at = factory.Faker("date_time", tzinfo=dt.timezone.utc)
    name = factory.Faker("word")
    items = []
    current_index = factory.Faker("random_number")


class ListItemFactory(factory.Factory):
    class Meta:
        model = models.ListItem

    id = factory.Faker("random_number")
    list_name = factory.Faker("word")
    index = factory.Faker("random_number")
    item = factory.Faker("text")
