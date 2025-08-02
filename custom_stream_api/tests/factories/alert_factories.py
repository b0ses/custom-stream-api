import factory
import datetime as dt

from custom_stream_api.alerts import models


class AlertFactory(factory.Factory):
    class Meta:
        model = models.Alert

    id = factory.Faker("random_number")
    created_at = factory.Faker("date_time", tzinfo=dt.timezone.utc)
    name = factory.Faker("word")
    text = factory.Faker("text")
    sound = factory.Faker("url")
    image = factory.Faker("image_url")
    thumbnail = factory.Faker("image_url")
    effect = factory.Faker("word")
    tags = []


class TagFactory(factory.Factory):
    class Meta:
        model = models.Tag

    id = factory.Faker("random_number")
    created_at = factory.Faker("date_time", tzinfo=dt.timezone.utc)
    name = factory.Faker("word")
    thumbnail = factory.Faker("image_url")
    current_index = 0
    always_chat = factory.Faker("boolean")
    chat_message = factory.Faker("text")
    alerts = []
    counts = []


class TagAssociationFactory(factory.Factory):
    class Meta:
        model = models.TagAssociation

    tag_name = factory.Faker("text")
    alert_name = factory.Faker("text")
