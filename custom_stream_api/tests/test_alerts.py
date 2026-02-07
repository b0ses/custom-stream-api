import pytest

from custom_stream_api.alerts import alerts
from custom_stream_api.alerts.models import Alert, Tag
from custom_stream_api.counts import counts
from custom_stream_api.shared import db

from custom_stream_api.tests.factories.alert_factories import (
    AlertFactory,
    TagFactory,
    TagAssociationFactory,
)
from custom_stream_api.tests.factories.counts_factories import CountFactory

TEST_ALERTS = []
TEST_TAGS = []


@pytest.fixture(scope="function")
def import_alerts(session):
    global TEST_ALERTS

    session.query(AlertFactory._meta.model).delete()
    session.commit()

    TEST_ALERTS = [
        AlertFactory(
            name="test_text_1",
            text="Test Text 1",
            sound="http://www.test.com/test_sound_1.mp3",
            image="",
            thumbnail="",
            effect="",
        ),
        AlertFactory(
            name="test_text_2",
            text="Test Text 2",
            sound="http://www.test.com/test_sound_2.mp3",
            image="",
            thumbnail="",
            effect="",
        ),
        AlertFactory(
            name="test_text_3",
            text="Test Text 3",
            sound="http://www.test.com/test_sound_3.mp3",
            image="",
            thumbnail="",
            effect="",
        ),
    ]
    TEST_ALERTS = [test_alert for test_alert in TEST_ALERTS]

    session.add_all(TEST_ALERTS)
    session.commit()

    yield session

    session.query(AlertFactory._meta.model).delete()
    session.commit()


@pytest.fixture(scope="function")
def import_tags(import_alerts, session):
    global TEST_TAGS, TEST_ALERTS  # noqa

    session.query(TagAssociationFactory._meta.model).delete()
    session.query(TagFactory._meta.model).delete()
    session.commit()

    TEST_TAGS = [
        TagFactory(name="first_two", display_name="first two", thumbnail=None, chat_message=None, always_chat=False),
        TagFactory(
            name="last_two", display_name="last two", thumbnail=None, chat_message="last two!", always_chat=True
        ),
        TagFactory(name="random", display_name="random", thumbnail=None, chat_message=None, always_chat=False),
    ]

    TEST_TAG_ASSOCIATIONS = [
        TagAssociationFactory(tag_name=TEST_TAGS[0].name, alert_name=TEST_ALERTS[0].name),
        TagAssociationFactory(tag_name=TEST_TAGS[0].name, alert_name=TEST_ALERTS[1].name),
        TagAssociationFactory(tag_name=TEST_TAGS[1].name, alert_name=TEST_ALERTS[1].name),
        TagAssociationFactory(tag_name=TEST_TAGS[1].name, alert_name=TEST_ALERTS[2].name),
    ]

    session.add_all(TEST_TAG_ASSOCIATIONS)
    session.add_all(TEST_TAGS)
    session.commit()

    TEST_TAGS = [test_tag for test_tag in TEST_TAGS]

    yield session

    session.query(TagAssociationFactory._meta.model).delete()
    session.query(TagFactory._meta.model).delete()
    session.commit()


@pytest.fixture(scope="function")
def import_counts(import_tags, session):
    session.query(CountFactory._meta.model).delete()
    session.commit()

    TEST_COUNTS = [
        CountFactory(
            name="count1",
            count=37,
            tag_name=TEST_TAGS[0].name,
        ),
        CountFactory(
            name="count2",
            count=2,
            tag_name=TEST_TAGS[0].name,
        ),
    ]
    session.add_all(TEST_COUNTS)
    session.commit()

    yield session

    session.query(CountFactory._meta.model).delete()
    session.commit()


def test_validate_sound():
    # Allow blank sounds
    assert alerts.validate_sound() is None
    assert alerts.validate_sound("") is None

    # Success tests
    test_mp3 = "http://www.test.com/test_mp3.mp3"
    test_wav = "http://www.test.com/some/random/dir/test_wav.wav"
    assert alerts.validate_sound(test_mp3) == "test_mp3"
    assert alerts.validate_sound(test_wav) == "test_wav"

    # Fail tests
    wrong_extension_1 = "http://www.test.com/test_mp3.blah"
    wrong_extension_2 = "http://www.test.com/test_mp3.mp3s"
    wrong_url_1 = "htp://www.test.com/test_mp3.mp3"
    wrong_url_2 = "htp://test_mp3.mp3"
    wrong_url_3 = "htp://www./test_mp3.mp3"
    for fail_test_sound in [wrong_extension_1, wrong_extension_2, wrong_url_1, wrong_url_2, wrong_url_3]:
        validated_sound = None
        try:
            validated_sound = alerts.validate_sound(fail_test_sound)
        except Exception:
            assert True
        assert validated_sound is None


def test_validate_effect():
    # Allow blank effects
    assert alerts.validate_effect("") == ""

    # Success tests
    for effect in alerts.VALID_EFFECTS:
        assert alerts.validate_effect(effect) == effect

    # Fail tests
    non_existent_effect = "blahhhhh"
    validated_effect = None
    try:
        validated_effect = alerts.validate_effect(non_existent_effect)
    except Exception:
        assert True
    assert validated_effect is None


def test_validate_image():
    # Allow blank sounds
    assert alerts.validate_image() is None
    assert alerts.validate_image("") is None

    # Success tests
    test_gif = "http://www.test.com/test_gif.gif"
    test_png = "http://www.test.com/some/random/dir/test_png.png"
    assert alerts.validate_image(test_gif) == "test_gif"
    assert alerts.validate_image(test_png) == "test_png"

    # Fail tests
    wrong_extension_1 = "http://www.test.com/test_gif.blah"
    wrong_extension_2 = "http://www.test.com/test_gif.gifs"
    wrong_url_1 = "htp://www.test.com/test_gif.gif"
    wrong_url_2 = "htp://test_gif.gif"
    wrong_url_3 = "htp://www./test_gif.gif"
    for fail_test_image in [wrong_extension_1, wrong_extension_2, wrong_url_1, wrong_url_2, wrong_url_3]:
        validated_image = None
        try:
            validated_image = alerts.validate_image(fail_test_image)
        except Exception:
            assert True
        assert validated_image is None


def test_validate_hex_color():
    # Valid cases
    assert alerts.validate_color_hex("#DDD") == "#DDD"
    assert alerts.validate_color_hex("#111111") == "#111111"

    # Invalid cases
    invalid_cases = ["DDD", "#", "#1", "#11", "#1111", "#11111", "#GGGGGG"]
    for case in invalid_cases:
        hex = None
        try:
            hex = alerts.validate_color_hex(case)
        except Exception:
            assert True
        assert hex is None


def test_standardize_name():
    # catchall case
    assert alerts.standardize_name("$A( )b-1!") == "a_b_1"

    # lower and keep numbers
    assert alerts.standardize_name("ABC123") == "abc123"

    # dashes + spaces => underscores
    assert alerts.standardize_name("- _") == "___"

    # special chars be gone
    assert alerts.standardize_name("!@#$%^&*()=+[]{}:;'\",.<>/?") == ""


# ALERTS
def test_save_alert(import_alerts):
    # Adding new alert
    test_text_4_dict = {
        "name": "test_text_4",
        "text": "Test Text 4",
        "sound": "http://www.test.com/test_sound.mp3",
        "image": "http://www.test.com/test_image.png",
        "thumbnail": "http://www.test.com/test_thumbnail.png",
        "effect": "fade",
        "tags": [],
    }
    alerts.save_alert(**test_text_4_dict)
    test_text_4_alert = db.session.query(Alert).filter_by(name="test_text_4").one()
    expected = test_text_4_alert.as_dict()
    del expected["created_at"]
    del expected["id"]
    assert expected == test_text_4_dict

    # Modifying an existing one
    test_text_4_dict = {
        "name": "test_text_4",
        "text": "Test Text 4",
        "sound": "",
        "image": "",
        "thumbnail": "",
        "effect": "",
        "tags": [],
    }
    alerts.save_alert(**test_text_4_dict)
    test_text_4_alert = db.session.query(Alert).filter_by(name="test_text_4").one()
    expected = test_text_4_alert.as_dict()
    del expected["created_at"]
    del expected["id"]
    assert expected == test_text_4_dict


def test_set_tags(import_tags):
    alerts.set_tags(TEST_ALERTS[2].name, ["first_two"])
    first_two_tags = db.session.query(Tag).filter_by(name="first_two").one()
    last_two_tags = db.session.query(Tag).filter_by(name="last_two").one()
    assert TEST_ALERTS[2].name in first_two_tags.as_dict()["alerts"]
    assert TEST_ALERTS[2].name not in last_two_tags.as_dict()["alerts"]

    alerts.set_tags(TEST_ALERTS[2].name, ["last_two"])
    first_two_tags = db.session.query(Tag).filter_by(name="first_two").one()
    last_two_tags = db.session.query(Tag).filter_by(name="last_two").one()
    assert TEST_ALERTS[2].name not in first_two_tags.as_dict()["alerts"]
    assert TEST_ALERTS[2].name in last_two_tags.as_dict()["alerts"]

    # Ignore tags that don't exist
    alerts.set_tags(TEST_ALERTS[2].name, ["last_two", "ignore this tag"])
    ignore_tag = db.session.query(Tag).filter_by(name="ignore this tag").one_or_none()
    assert ignore_tag is None

    # Test removing empty tags
    alerts.set_tags(TEST_ALERTS[2].name, [])
    alerts.set_tags(TEST_ALERTS[1].name, ["first_two"])

    first_two_tags = db.session.query(Tag).filter_by(name="first_two").one()
    assert TEST_ALERTS[1].name in first_two_tags.as_dict()["alerts"]
    assert TEST_ALERTS[2].name not in first_two_tags.as_dict()["alerts"]

    last_two_tags = db.session.query(Tag).filter_by(name="last_two").one_or_none()
    assert last_two_tags is None


def test_alert(import_alerts):
    expected = "Test Text 1"
    assert alerts.alert(TEST_ALERTS[0].name, hit_socket=False)["text"] == expected


def test_alert_details(import_alerts):
    assert alerts.alert_details(TEST_ALERTS[0].name) == TEST_ALERTS[0].as_dict()


def test_remove_alert(import_tags):
    alerts.remove_alert(TEST_ALERTS[1].name)
    all_alerts = [alert["name"] for alert in alerts.browse(include_tags=False)[0]]
    assert "test_text_2" not in all_alerts

    first_two_tags = db.session.query(Tag).filter_by(name="first_two").one()
    assert TEST_ALERTS[1].name not in first_two_tags.alerts


# TAGS
def test_save_tag(import_tags):
    # Adding new alert
    all_tag_dict = {
        "name": "all_alerts",
        "display_name": "All Alerts",
        "thumbnail": "http://www.test.com/test_thumbnail.png",
        "category": "reference",
        "always_chat": True,
        "chat_message": "",
        "alerts": [],
    }
    alerts.save_tag(**all_tag_dict)
    all_tag = db.session.query(Tag).filter_by(name="all_alerts").one()
    expected = all_tag.as_dict()
    del expected["created_at"]
    del expected["id"]
    del expected["current_index"]
    assert expected == all_tag_dict

    # Modifying an existing one
    all_tag_dict = {
        "name": "all_alerts",
        "display_name": "All Alerts",
        "thumbnail": "",
        "category": "reference",
        "always_chat": False,
        "chat_message": "",
        "alerts": [],
    }
    alerts.save_tag(**all_tag_dict)
    all_tag = db.session.query(Tag).filter_by(name="all_alerts").one()
    expected = all_tag.as_dict()
    del expected["created_at"]
    del expected["id"]
    del expected["current_index"]
    assert expected == all_tag_dict


def test_set_alerts(import_tags):
    alerts.set_alerts(TEST_TAGS[0].name, ["test_text_3"])
    text_text_3_alert = db.session.query(Alert).filter_by(name="test_text_3").one()
    assert TEST_TAGS[0].name in text_text_3_alert.as_dict()["tags"]
    assert TEST_TAGS[0].as_dict()["alerts"] == ["test_text_3"]

    # Ignore tags that don't exist
    alerts.set_alerts(TEST_TAGS[0].name, ["test_text_3", "ignore this alert"])
    ignore_alert = db.session.query(Alert).filter_by(name="ignore this alert").one_or_none()
    assert ignore_alert is None


def test_tag_alert(import_counts):
    expected = ["Test Text 2", "Test Text 3"]
    assert alerts.tag_alert(TEST_TAGS[1].name, hit_socket=False)["text"] in expected

    expected = ["Test Text 1", "Test Text 2"]
    assert alerts.tag_alert(TEST_TAGS[0].name, hit_socket=False)["text"] in expected

    expected = ["Test Text 1", "Test Text 2"]
    assert alerts.tag_alert(TEST_TAGS[0].name, hit_socket=False)["text"] in expected

    expected = ["Test Text 1", "Test Text 2", "Test Text 3"]
    assert alerts.tag_alert("random", hit_socket=False)["text"] in expected

    count = counts.get_count("count1")
    assert count == 39

    count = counts.get_count("count2")
    assert count == 4


def test_tag_details(import_tags):
    assert alerts.tag_details(TEST_TAGS[0].name) == TEST_TAGS[0].as_dict()


def test_remove_tag(import_tags):
    alerts.remove_tag(TEST_TAGS[1].name)
    all_tags = [tag["name"] for tag in alerts.browse(include_tags=True, include_alerts=False)[0]]
    assert TEST_TAGS[1].name not in all_tags

    test_text_3 = db.session.query(Alert).filter_by(name="test_text_3").one()
    assert TEST_TAGS[1].name not in test_text_3.tags


# BROWSE
def test_browse(import_tags):
    def dict_alert(alert, tag=False):
        return {
            "name": alert.name,
            "thumbnail": alert.thumbnail,
            "type": "Tag" if tag else "Alert",
            "display_name": alert.text if not tag else alert.display_name,
        }

    # Dropping the random tag as it messes with the expected ordering
    db.session.query(Tag).filter_by(name="random").delete()

    # without tags
    assert alerts.browse(limit=1, include_tags=False)[0][0] == dict_alert(TEST_ALERTS[0])
    assert alerts.browse(limit=1, page=2, include_tags=False)[0][0] == dict_alert(TEST_ALERTS[1])
    assert alerts.browse(limit=2, page=2, include_tags=False)[0][0] == dict_alert(TEST_ALERTS[2])
    assert alerts.browse(sort="-name", include_tags=False)[0][0] == dict_alert(TEST_ALERTS[2])
    assert alerts.browse(search="tExT_2", include_tags=False)[0][0] == dict_alert(TEST_ALERTS[1])

    # with tags
    assert alerts.browse(limit=1, include_tags=True)[0][0] == dict_alert(TEST_TAGS[0], tag=True)
    assert alerts.browse(limit=1, page=2, include_tags=True)[0][0] == dict_alert(TEST_TAGS[1], tag=True)
    assert alerts.browse(limit=2, page=2, include_tags=True)[0][0] == dict_alert(TEST_ALERTS[0], tag=False)
    assert alerts.browse(sort="-name", include_tags=True)[0][0] == dict_alert(TEST_TAGS[1], tag=True)
    assert alerts.browse(search="tExT_2")[0][0] == dict_alert(TEST_ALERTS[1], tag=False)

    # check to see the only difference between with/without tags is tags at the beginning
    sans_tags, _ = alerts.browse(limit=10, include_tags=False)
    with_tags, _ = alerts.browse(limit=10, include_tags=True)
    assert sans_tags == with_tags[2:]

    # when searching and a tag matches, include all the alerts associated with each matched tag
    results, _ = alerts.browse(search="first two", include_tags=True)
    assert results == [
        dict_alert(TEST_TAGS[0], tag=True),
        dict_alert(TEST_ALERTS[0], tag=False),
        dict_alert(TEST_ALERTS[1], tag=False),
    ]
