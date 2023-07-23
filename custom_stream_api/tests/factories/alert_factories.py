import factory
import datetime as dt

from custom_stream_api.alerts import models


class AlertFactory(factory.Factory):
    class Meta:
        model = models.Alert

    created_at = factory.Faker("date_time", tzinfo=dt.timezone.utc)
    name = factory.Faker("word")
    text = factory.Faker("text")
    sound = factory.Faker("url")
    image = factory.Faker("image_url")
    duration = factory.Faker("random_number")
    thumbnail = factory.Faker("image_url")
    effect = factory.Faker("word")


class GroupAlertFactory(factory.Factory):
    class Meta:
        model = models.GroupAlert

    created_at = factory.Faker("date_time", tzinfo=dt.timezone.utc)
    group_name = factory.Faker("word")
    alerts = []
    thumbnail = factory.Faker("image_url")
    current_index = 0
    counts = []
    always_chat = factory.Faker("boolean")
    chat_message = factory.Faker("text")


class GroupAlertAssociationFactory(factory.Factory):
    class Meta:
        model = models.GroupAlertAssociation

    group_name = factory.Faker("word")
    alert_name = factory.Faker("word")
    index = factory.Faker("random_number")
