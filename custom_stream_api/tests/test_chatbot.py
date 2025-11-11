import mock
import pytest

from collections import namedtuple

from custom_stream_api.alerts import alerts
from custom_stream_api.chatbot import aliases
from custom_stream_api.chatbot.chatbot import ChatBot
from custom_stream_api.chatbot.models import Badges, BADGE_NAMES, Timer
from custom_stream_api.lists import lists
from custom_stream_api.shared import get_app

from custom_stream_api.tests.factories.chatbot_factories import AliasFactory
from custom_stream_api.tests.test_alerts import import_tags, import_alerts  # noqa

TEST_ALIAS_DICTS = []

Event = namedtuple(
    "Event",
    [
        "tags",
        "arguments",
    ],
)


@pytest.fixture(scope="function")
def import_aliases(session):
    global TEST_ALIAS_DICTS

    session.query(AliasFactory._meta.model).delete()
    session.commit()

    TEST_ALIASES = [
        AliasFactory(alias="test_alert", badge="chat", command="!alert test_text_1"),
        AliasFactory(alias="chat_test_alias", badge="chat", command="!get_count test_count"),
        AliasFactory(alias="sub_test_alias", badge="subscriber", command="!get_count test_count"),
        AliasFactory(alias="reset_session", badge="broadcaster", command="!reset_count test_count test_count_2"),
        AliasFactory(alias="test_alias_args", badge="vip", command="!set_count test_count"),
        AliasFactory(alias="mod_test_alias", badge="vip", command="!set_count test_count 10"),
        AliasFactory(alias="broadcaster_test_alias", badge="broadcaster", command="!set_count test_count 10"),
    ]

    TEST_ALIAS_DICTS = [test_alias.as_dict() for test_alias in TEST_ALIASES]
    session.add_all(TEST_ALIASES)
    session.commit()

    yield session

    session.query(AliasFactory._meta.model).delete()
    session.commit()


def fake_alert_api(cls, user, badges, text):
    if user in lists.get_list("banned_users"):
        return
    elif not cls._badge_check(badges, Badges.VIP) and cls.spamming(user):
        cls.chat("No spamming {}. Wait another {} seconds.".format(user, cls.timeout))
        return

    text_args = tuple(text.split())
    alert_name = text_args[0]
    display_text = " ".join(text_args[1:]) if len(text_args) > 1 else None

    try:
        alerts.alert(name=alert_name, hit_socket=False, chat=display_text)
    except Exception:
        pass


def fake_tag_alert_api(cls, user, badges, text):
    if user in lists.get_list("banned_users"):
        return
    elif not cls._badge_check(badges, Badges.VIP) and cls.spamming(user):
        cls.chat("No spamming {}. Wait another {} seconds.".format(user, cls.timeout))
        return

    text_args = tuple(text.split())
    tag_name = text_args[0]
    display_text = " ".join(text_args[1:]) if len(text_args) > 1 else None

    try:
        alerts.tag_alert(name=tag_name, hit_socket=False, chat=display_text)
    except Exception:
        pass


@pytest.fixture(scope="function")
def chatbot(session):
    # we don't need it to actually connect and listen to chat
    # just to respond the way we want it to

    def store_chat(cls, message, user=None):
        message = cls._substitute_vars(message, user=user)
        cls.queue.append(message)

    with mock.patch.object(ChatBot, "chat", new=store_chat):
        bot = ChatBot([], timeout=0.1)
        app = get_app()
        app.twitch_chatbot = bot
        yield bot


# MAIN COMMANDS


def test_echo(chatbot):
    chatbot.parse_message("test_user", "!echo test test 1 2 3", [Badges.VIP])
    expected_responses = []
    assert chatbot.queue == expected_responses

    chatbot.parse_message("test_user", "!echo test test 1 2 3", [Badges.BROADCASTER])
    expected_response = "test test 1 2 3"
    assert chatbot.queue[-1] == expected_response

    chatbot.parse_message("test_user", "!echo {user} says hi", [Badges.BROADCASTER])
    expected_response = "test_user says hi"
    assert chatbot.queue[-1] == expected_response


def test_get_commands(chatbot):
    badge_level = []
    chatbot.parse_message("test_user", "!get_commands non-existent-badge", badge_level)
    expected_response = "Format: !get_commands [{}]".format(" | ".join(sorted(BADGE_NAMES)))
    assert chatbot.queue[-1] == expected_response

    badge_level = []
    chatbot.parse_message("test_user", "!get_commands", badge_level)
    expected_response = "Commands include: get_aliases, get_commands, get_count_commands, get_list_commands, help"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.SUBSCRIBER]
    chatbot.parse_message("test_user", "!get_commands", badge_level)
    expected_response = (
        "Commands include: get_aliases, get_commands, get_count_commands, get_list_commands, help, " "spongebob, taco"
    )
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!get_commands", badge_level)
    expected_response = (
        "Commands include: get_alert_commands, get_aliases, get_commands, get_count_commands, "
        "get_list_commands, get_timer_commands, help, random, spongebob, taco"
    )
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.BROADCASTER]
    chatbot.parse_message("test_user", "!get_commands", badge_level)
    expected_response = (
        "Commands include: echo, get_alert_commands, get_aliases, get_commands, "
        "get_count_commands, get_list_commands, get_timer_commands, help, random, "
        "spongebob, taco"
    )
    assert chatbot.queue[-1] == expected_response

    badge_level = []
    chatbot.parse_message("test_user", "!get_commands broadcaster", badge_level)
    expected_response = (
        "Commands include: echo, get_alert_commands, get_aliases, get_commands, "
        "get_count_commands, get_list_commands, get_timer_commands, help, random, "
        "spongebob, taco"
    )
    assert chatbot.queue[-1] == expected_response


def test_random(chatbot):
    chatbot.parse_message("test_user", "!random a b c", [Badges.SUBSCRIBER])
    expected_responses = []
    assert chatbot.queue == expected_responses

    chatbot.parse_message("test_user", "!random a", [Badges.VIP])
    expected_response = "Format: !random option1 option2 [option3 ...]"
    assert chatbot.queue[-1] == expected_response

    chatbot.parse_message("test_user", "!random a b c", [Badges.VIP])
    expected_responses = ["Random choice: a", "Random choice: b", "Random choice: c"]
    assert chatbot.queue[-1] in expected_responses


def test_spongebob(chatbot):
    chatbot.parse_message("test_user", "!spongebob", [Badges.SUBSCRIBER])
    expected_response = "Format: !spongebob message"
    assert chatbot.queue[-1] == expected_response

    chatbot.parse_message("test_user", "!spongebob stop mimicking me", [Badges.SUBSCRIBER])
    expected_response = "sToP MiMiCkInG Me - https://dannypage.github.io/assets/images/mocking-spongebob.jpg"
    assert chatbot.queue[-1] == expected_response

    chatbot.parse_message("test_user", "!spongebob stop mimicking me please", [])
    # unchanged
    assert chatbot.queue[-1] == expected_response


def test_taco(chatbot):
    chatbot.parse_message("test_user", "!taco test_user2", [Badges.CHAT])
    expected_response = []
    assert chatbot.queue == expected_response

    chatbot.parse_message("test_user", "!taco test_user2", [Badges.SUBSCRIBER])
    expected_response = ["/me test_user aggressively hurls a :taco: at test_user2", "test_user2_tacos: 1"]
    assert chatbot.queue == expected_response

    chatbot.parse_message("test_user", "!taco  ", [Badges.SUBSCRIBER])
    expected_response = "Format: !taco [to_user]"
    assert chatbot.queue[-1] == expected_response


# # ALIASES
def test_get_aliases_empty(chatbot):
    badge_level = []
    chatbot.parse_message("test_user", "!get_aliases", badge_level)
    expected_response = "No commands available"
    assert chatbot.queue[-1] == expected_response


def test_import_export_aliases(import_aliases):
    assert aliases.list_aliases() == TEST_ALIAS_DICTS


def test_remove_alias(import_aliases):
    aliases.remove_alias("chat_test_alias")
    all_aliases = [alias["alias"] for alias in aliases.list_aliases()]
    assert "chat_test_alias" not in all_aliases


def test_get_aliases(import_aliases, chatbot):
    badge_level = []
    chatbot.parse_message("test_user", "!get_aliases", badge_level)
    expected_response = "Commands include: chat_test_alias, test_alert"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.SUBSCRIBER]
    chatbot.parse_message("test_user", "!get_aliases", badge_level)
    expected_response = "Commands include: chat_test_alias, sub_test_alias, test_alert"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!get_aliases", badge_level)
    expected_response = "Commands include: chat_test_alias, mod_test_alias, sub_test_alias, test_alert, test_alias_args"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.BROADCASTER]
    chatbot.parse_message("test_user", "!get_aliases", badge_level)
    expected_response = (
        "Commands include: broadcaster_test_alias, chat_test_alias, mod_test_alias, "
        "reset_session, sub_test_alias, test_alert, test_alias_args"
    )
    assert chatbot.queue[-1] == expected_response


@mock.patch.object(ChatBot, "alert_api", new=fake_alert_api)
@mock.patch.object(ChatBot, "tag_alert_api", new=fake_tag_alert_api)
def test_aliases(import_aliases, import_tags, chatbot, app):  # noqa
    badge_level = [Badges.SUBSCRIBER]
    chatbot.parse_message("test_user", "!mod_test_alias", badge_level)
    expected_responses = []
    assert chatbot.queue == expected_responses

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!mod_test_alias", badge_level)
    expected_response = "test_count: 10"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!test_alias_args 14", badge_level)
    expected_response = "test_count: 14"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!test_alias_args blah", badge_level)
    expected_response = "Format: !test_alias_args number"
    assert chatbot.queue[-1] == expected_response

    badge_level = []
    chatbot.parse_message("test_user", "!test_alert", badge_level)
    expected_response = "/me Test Text 1"
    assert chatbot.queue[-1] == expected_response

    # spam test
    badge_level = []
    chatbot.parse_message("test_user", "!test_alert", badge_level)
    expected_response = "No spamming {}. Wait another {} seconds.".format("test_user", chatbot.timeout)
    assert chatbot.queue[-1] == expected_response


# TIMERS
def test_reminder(chatbot, session):
    # Just testing to see if it saved to the database correctly, not actually doing the waiting
    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!reminder test_text_1 30 remember to do the thing", badge_level)

    expected_command = "!alert test_text_1 Reminder: remember to do the thing"
    found_timer = session.query(Timer).filter_by(command=expected_command).one_or_none()
    assert found_timer is not None


# COUNTS
def test_get_count_commands(chatbot):
    badge_level = []
    chatbot.parse_message("test_user", "!get_count_commands", badge_level)
    expected_response = "Commands include: get_count, list_counts"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!get_count_commands", badge_level)
    expected_response = (
        "Commands include: add_count, copy_count, get_count, list_counts, remove_count, reset_count, "
        "set_count, subtract_count"
    )
    assert chatbot.queue[-1] == expected_response


def test_count_commands(chatbot):
    badge_level = [Badges.CHAT]
    chatbot.parse_message("test_user", "!list_counts", badge_level)
    expected_responses = []
    assert chatbot.queue == expected_responses

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!set_count test_count 10", badge_level)
    expected_response = "test_count: 10"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!set_count", badge_level)
    expected_response = "Format: !set_count count_name number"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!set_count test count 10", badge_level)
    expected_response = "Format: !set_count count_name number"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!set_count test_count blah", badge_level)
    expected_response = "Format: !set_count count_name number"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!add_count test_count", badge_level)
    expected_response = "test_count: 11"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!add_count test_count2", badge_level)
    expected_response = "test_count2: 1"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!add_count", badge_level)
    expected_response = "Format: !add_count count_name"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!add_count test_count 30", badge_level)
    expected_response = "Format: !add_count count_name"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!subtract_count test_count", badge_level)
    expected_response = "test_count: 10"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!subtract_count", badge_level)
    expected_response = "Format: !subtract_count count_name"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!subtract_count test_count 30", badge_level)
    expected_response = "Format: !subtract_count count_name"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!reset_count test_count test_count3", badge_level)
    expected_response1 = "test_count: 0"
    expected_response2 = "test_count3: 0"
    assert chatbot.queue[-2] == expected_response1
    assert chatbot.queue[-1] == expected_response2

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!reset_count ", badge_level)
    expected_response = "Format: !reset_count count_name1 count_name2 ..."
    assert chatbot.queue[-1] == expected_response

    badge_level = []
    chatbot.parse_message("test_user", "!get_count test_count", badge_level)
    expected_response = "test_count: 0"
    assert chatbot.queue[-1] == expected_response

    badge_level = []
    chatbot.parse_message("test_user", "!get_count", badge_level)
    expected_response = "Format: !get_count count_name"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!get_count non_existent_count", badge_level)
    # unchanged
    assert chatbot.queue[-1] == expected_response

    badge_level = []
    chatbot.parse_message("test_user", "!get_count count with spaces", badge_level)
    expected_response = "Format: !get_count count_name"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!copy_count test_count test_count5", badge_level)
    expected_response = "test_count5: 0"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!copy_count test_count6 test_count3", badge_level)
    expected_response = "test_count6 doesn't exist."
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.CHAT]
    chatbot.parse_message("test_user", "!list_counts", badge_level)
    expected_response = "Counts: test_count, test_count2, test_count3, test_count5"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.BROADCASTER]
    chatbot.parse_message("test_user", "!echo Custom message {test_count}!{test_count2}", badge_level)
    expected_response = "Custom message 0!1"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!remove_count test_count", badge_level)
    expected_response = "test_count removed"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!remove_count ", badge_level)
    expected_response = "Format: !remove_count count_name"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!remove_count test_count 30", badge_level)
    expected_response = "Format: !remove_count count_name"
    assert chatbot.queue[-1] == expected_response


# LISTS
def test_get_list_commands(chatbot):
    badge_level = []
    chatbot.parse_message("test_user", "!get_list_commands", badge_level)
    expected_response = "Commands include: get_list_item, get_list_size, list_lists"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!get_list_commands", badge_level)
    expected_response = "Commands include: add_list_item, get_list_item, get_list_size, list_lists, remove_list_item"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.BROADCASTER]
    chatbot.parse_message("test_user", "!get_list_commands", badge_level)
    expected_response = (
        "Commands include: add_list_item, get_list_item, get_list_size, list_lists, remove_list, " "remove_list_item"
    )
    assert chatbot.queue[-1] == expected_response


def test_list_commands(chatbot):
    badge_level = []
    chatbot.parse_message("test_user", "!list_lists", badge_level)
    expected_responses = []
    assert chatbot.queue == expected_responses

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!add_list_item test_list item_one", badge_level)
    expected_response = "1. item_one"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!add_list_item test_list item_two", badge_level)
    expected_response = "2. item_two"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!add_list_item", badge_level)
    expected_response = "Format: !add_list_item list_name item to include in list"
    assert chatbot.queue[-1] == expected_response

    badge_level = []
    chatbot.parse_message("test_user", "!get_list_item test_list 2", badge_level)
    expected_response = "2. item_two"
    assert chatbot.queue[-1] == expected_response

    badge_level = []
    chatbot.parse_message("test_user", "!get_list_item test_list 4", badge_level)
    expected_response = "Index too high"
    assert chatbot.queue[-1] == expected_response

    badge_level = []
    chatbot.parse_message("test_user", "!get_list_item non_existent_list 1", badge_level)
    expected_response = "List not found"
    assert chatbot.queue[-1] == expected_response

    badge_level = []
    chatbot.parse_message("test_user", "!get_list_item test_list -1", badge_level)
    expected_response = "2. item_two"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.BROADCASTER]
    chatbot.parse_message("test_user", "!echo 1.{test_list 1} 2.{test_list 2}", badge_level)
    expected_response = "1.item_one 2.item_two"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.BROADCASTER]
    chatbot.parse_message("test_user", "!echo random.{test_list random}", badge_level)
    expected_responses = ["random.item_one", "random.item_two"]
    assert chatbot.queue[-1] in expected_responses

    badge_level = []
    chatbot.parse_message("test_user", "!get_list_item test_list random", badge_level)
    expected_responses = ["1. item_one", "2. item_two"]
    assert chatbot.queue[-1] in expected_responses

    badge_level = []
    chatbot.parse_message("test_user", "!get_list_item", badge_level)
    expected_response = "Format: !get_list_item list_name [index]/next/random"
    assert chatbot.queue[-1] == expected_response

    badge_level = []
    chatbot.parse_message("test_user", "!get_list_item test_list test", badge_level)
    expected_response = "Format: !get_list_item list_name [index]/next/random"
    assert chatbot.queue[-1] == expected_response

    badge_level = []
    chatbot.parse_message("test_user", "!get_list_size test_list", badge_level)
    expected_response = "test_list size: 2"
    assert chatbot.queue[-1] == expected_response

    badge_level = []
    chatbot.parse_message("test_user", "!get_list_size test_list extra", badge_level)
    expected_response = "Format: !get_list_size list_name"
    assert chatbot.queue[-1] == expected_response

    badge_level = []
    chatbot.parse_message("test_user", "!get_list_size", badge_level)
    expected_response = "Format: !get_list_size list_name"
    assert chatbot.queue[-1] == expected_response

    badge_level = []
    chatbot.parse_message("test_user", "!get_list_size non_existent_list", badge_level)
    expected_response = "List not found"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!remove_list_item test_list 1", badge_level)
    expected_response = "Removed 1. item_one"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!remove_list_item test_list 1", badge_level)
    expected_response = "Removed 1. item_two"
    assert chatbot.queue[-1] == expected_response

    badge_level = []
    chatbot.parse_message("test_user", "!get_list_item test_list random", badge_level)
    expected_response = "Empty list"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!remove_list_item non_existent_list 1", badge_level)
    expected_response = "List not found"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!remove_list_item", badge_level)
    expected_response = "Format: !remove_list_item list_name index"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!remove_list_item test_list test", badge_level)
    expected_response = "Format: !remove_list_item list_name index"
    assert chatbot.queue[-1] == expected_response

    badge_level = []
    chatbot.parse_message("test_user", "!list_lists", badge_level)
    expected_response = "Lists: test_list"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.BROADCASTER]
    chatbot.parse_message("test_user", "!remove_list test_list", badge_level)
    expected_response = "Removed list test_list"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.BROADCASTER]
    chatbot.parse_message("test_user", "!remove_list test_list", badge_level)
    expected_response = "Removed list test_list"
    assert chatbot.queue[-1] == expected_response


# ALERTS
def test_get_alert_commands(chatbot):
    badge_level = []
    chatbot.parse_message("test_user", "!get_alert_commands", badge_level)
    expected_responses = []
    assert chatbot.queue == expected_responses

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!get_alert_commands", badge_level)
    expected_response = "Commands include: alert, ban, tag, unban"
    assert chatbot.queue[-1] == expected_response


@mock.patch.object(ChatBot, "alert_api", new=fake_alert_api)
@mock.patch.object(ChatBot, "tag_alert_api", new=fake_tag_alert_api)
def test_alert_commands(chatbot, import_tags):  # noqa
    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!alert test_text_1", badge_level)
    expected_response = "/me Test Text 1"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!alert", badge_level)
    expected_response = "Format: !alert alert_name [display text]"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!alert test_text_1 blah", badge_level)
    expected_response = "/me blah"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!tag first_two", badge_level)
    expected_responses = ["/me Test Text 1", "/me Test Text 2"]
    assert chatbot.queue[-1] in expected_responses

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!tag last_two", badge_level)
    expected_response = "/me last two!"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!tag", badge_level)
    expected_response = "Format: !tag tag_name [display text]"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!tag first_two blah", badge_level)
    expected_response = "/me blah"
    assert chatbot.queue[-1] == expected_response

    # banning

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!ban test_user2", badge_level)
    expected_response = "Banned test_user2"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!ban", badge_level)
    expected_response = "Format: !ban chatter"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user", "!ban test_user2 for real", badge_level)
    expected_response = "Format: !ban chatter"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user2", "!alert test_text_1", badge_level)
    # unchanged
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user2", "!unban test_user2", badge_level)
    expected_response = "Unbanned test_user2"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user2", "!unban", badge_level)
    expected_response = "Format: !unban banned_chatter"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user2", "!unban test_user2 for real", badge_level)
    expected_response = "Format: !unban banned_chatter"
    assert chatbot.queue[-1] == expected_response

    badge_level = [Badges.VIP]
    chatbot.parse_message("test_user2", "!alert test_text_1", badge_level)
    expected_response = "/me Test Text 1"
    assert chatbot.queue[-1] == expected_response


def test_stress(chatbot):
    badge_level = [Badges.BROADCASTER]
    expected_responses = []
    for i in range(0, 1000):
        message = "Message {}".format(i)
        chatbot.parse_message("test_user2", "!echo {}".format(message), badge_level)
        expected_responses.append(message)
    assert chatbot.queue == expected_responses


@pytest.mark.skip
# TODO: mock chat threading
def test_queue_messages(chatbot):
    badge_level = [Badges.BROADCASTER]
    chatbot.parse_message("test_user", "!echo slow message", badge_level)
    chatbot.parse_message("test_user", "!echo fast message", badge_level)
    expected_responses = ["slow message", "fast message"]
    assert chatbot.queue == expected_responses
