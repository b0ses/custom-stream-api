import pytest
import mock
import time

from custom_stream_api.chatbot import aliases, twitchbot, models
from custom_stream_api.alerts import alerts
from custom_stream_api.lists import lists
from tests.test_alerts import IMPORT_GROUP_ALERTS, IMPORT_ALERTS
from collections import namedtuple

Event = namedtuple('Event', ['tags', 'arguments', ])

IMPORT_ALIASES = [
    {
        "alias": "chat_alert",
        "badge": "chat",
        "command": "!alert test_text_1"
    },
    {
        "alias": "chat_test_alias",
        "badge": "chat",
        "command": "!get_count test_count"
    },
    {
        "alias": "sub_test_alias",
        "badge": "subscriber",
        "command": "!get_count test_count"
    },
    {
        "alias": "mod_test_alias",
        "badge": "moderator",
        "command": "!set_count test_count 10"
    },
    {
        "alias": "broadcaster_test_alias",
        "badge": "broadcaster",
        "command": "!set_count test_count 10"
    }
]


@pytest.fixture
def import_aliases(app):
    aliases.import_aliases(IMPORT_ALIASES)


@pytest.fixture
def import_alerts(app):
    alerts.import_alerts(IMPORT_ALERTS)


@pytest.fixture
def import_groups(import_alerts):
    alerts.import_groups(IMPORT_GROUP_ALERTS)


def fake_alert_api(cls, user, badges, alert):
    if user in lists.get_list('banned_users'):
        cls.chat('Nice try {}'.format(user))
        return
    elif not cls._badge_check(badges, models.Badges.MODERATOR) and cls.spamming(user):
        cls.chat('No spamming {}. Wait another {} seconds.'.format(user, cls.timeout))
        return

    try:
        message = alerts.alert(name=alert, hit_socket=False)
        cls.chat('/me {}'.format(message))
    except Exception as e:
        pass


def fake_group_alert_api(cls, user, badges, group_alert):
    if user in lists.get_list('banned_users'):
        cls.chat('Nice try {}'.format(user))
        return
    elif not cls._badge_check(badges, models.Badges.MODERATOR) and cls.spamming(user):
        cls.chat('No spamming {}. Wait another {} seconds.'.format(user, cls.timeout))
        return

    try:
        message = alerts.group_alert(group_name=group_alert, hit_socket=False)
        cls.chat('/me {}'.format(message))
    except Exception as e:
        pass


@pytest.fixture
def chatbot(app):
    # we don't need it to actually connect and listen to chat
    # just to respond the way we want it to

    def store_chat(cls, message):
        cls.response = message

    with mock.patch.object(twitchbot.TwitchBot, 'chat', new=store_chat):
        yield twitchbot.TwitchBot('test_id', 'test_botname', 'test_client_id', 'test_token', 'test_channel',
                                  timeout=0.1)


def simulate_chat(bot, user_name, message, badges):
    tags = {
        'display-name': user_name,
        'badges': ','.join([badge.value for badge in badges])
    }
    kv_tags = [{'key': key, 'value': value} for key, value in tags.items()]
    bot.on_pubmsg(None, Event(tags=kv_tags, arguments=[message]))


# MAIN COMMANDS
def test_id(chatbot):
    simulate_chat(chatbot, 'test_user', '!id', [models.Badges.GLOBAL_MODERATOR])
    expected_response = 'Nice try test_user'
    assert chatbot.response == expected_response

    simulate_chat(chatbot, 'test_user', '!id', [models.Badges.BROADCASTER])
    expected_response = 'Chatbot ID - test_id'
    assert chatbot.response == expected_response


def test_echo(chatbot):
    simulate_chat(chatbot, 'test_user', '!echo test test 1 2 3', [models.Badges.MODERATOR])
    expected_response = 'Nice try test_user'
    assert chatbot.response == expected_response

    simulate_chat(chatbot, 'test_user', '!echo test test 1 2 3', [models.Badges.BROADCASTER])
    expected_response = 'test test 1 2 3'
    assert chatbot.response == expected_response


def test_get_commands(chatbot):
    # FAIL
    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_commands non-existent-badge', badge_level)
    expected_response = 'Format: !get_commands [{}]'.format(' | '.join(sorted(models.BADGE_NAMES)))
    assert chatbot.response == expected_response

    # SUCCESS
    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_commands', badge_level)
    expected_response = 'Commands include: get_aliases, get_commands, get_count_commands, get_list_commands'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.SUBSCRIBER]
    simulate_chat(chatbot, 'test_user', '!get_commands', badge_level)
    expected_response = 'Commands include: get_aliases, get_commands, get_count_commands, get_list_commands, spongebob'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!get_commands', badge_level)
    expected_response = 'Commands include: get_alert_commands, get_aliases, get_commands, get_count_commands, ' \
                        'get_list_commands, spongebob'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.BROADCASTER]
    simulate_chat(chatbot, 'test_user', '!get_commands', badge_level)
    expected_response = 'Commands include: echo, get_alert_commands, get_aliases, get_commands, get_count_commands, ' \
                        'get_list_commands, id, spongebob'
    assert chatbot.response == expected_response

    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_commands broadcaster', badge_level)
    expected_response = 'Commands include: echo, get_alert_commands, get_aliases, get_commands, get_count_commands, ' \
                        'get_list_commands, id, spongebob'
    assert chatbot.response == expected_response


def test_spongebob(chatbot):
    # FAIL
    simulate_chat(chatbot, 'test_user', '!spongebob', [models.Badges.SUBSCRIBER])
    expected_response = 'Format: !spongebob message'
    assert chatbot.response == expected_response

    # SUCCESS
    simulate_chat(chatbot, 'test_user', '!spongebob stop mimicking me', [models.Badges.SUBSCRIBER])
    expected_response = 'sToP MiMiCkInG Me - https://dannypage.github.io/assets/images/mocking-spongebob.jpg'
    assert chatbot.response == expected_response

    simulate_chat(chatbot, 'test_user', '!spongebob stop mimicking me', [])
    expected_response = 'Nice try test_user'
    assert chatbot.response == expected_response


# ALIASES
def test_get_aliases_empty(chatbot):
    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_aliases', badge_level)
    expected_response = 'No commands available'
    assert chatbot.response == expected_response


def test_import_export_aliases(import_aliases):
    assert aliases.list_aliases() == IMPORT_ALIASES


def test_remove_alert(import_aliases):
    aliases.remove_alias('chat_test_alias')
    all_aliases = [alias['alias'] for alias in aliases.list_aliases()]
    assert 'chat_test_alias' not in all_aliases


def test_get_aliases(import_aliases, chatbot):
    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_aliases', badge_level)
    expected_response = 'Commands include: chat_alert, chat_test_alias'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.SUBSCRIBER]
    simulate_chat(chatbot, 'test_user', '!get_aliases', badge_level)
    expected_response = 'Commands include: chat_alert, chat_test_alias, sub_test_alias'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!get_aliases', badge_level)
    expected_response = 'Commands include: chat_alert, chat_test_alias, mod_test_alias, sub_test_alias'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.BROADCASTER]
    simulate_chat(chatbot, 'test_user', '!get_aliases', badge_level)
    expected_response = 'Commands include: broadcaster_test_alias, chat_alert, chat_test_alias, mod_test_alias, sub_test_alias'
    assert chatbot.response == expected_response


@mock.patch.object(twitchbot.TwitchBot, 'alert_api', new=fake_alert_api)
@mock.patch.object(twitchbot.TwitchBot, 'group_alert_api', new=fake_group_alert_api)
def test_aliases(import_aliases, import_groups, chatbot):
    badge_level = [models.Badges.SUBSCRIBER]
    simulate_chat(chatbot, 'test_user', '!mod_test_alias', badge_level)
    expected_response = 'Nice try test_user'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!mod_test_alias', badge_level)
    expected_response = 'test_count: 10'
    assert chatbot.response == expected_response

    badge_level = []
    simulate_chat(chatbot, 'test_user', '!chat_alert', badge_level)
    expected_response = '/me Test Text 1'
    assert chatbot.response == expected_response

    # spam test
    badge_level = []
    simulate_chat(chatbot, 'test_user', '!chat_alert', badge_level)
    expected_response = 'No spamming {}. Wait another {} seconds.'.format('test_user', chatbot.timeout)
    assert chatbot.response == expected_response


# COUNTS
def test_get_count_commands(chatbot):
    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_count_commands', badge_level)
    expected_response = 'Commands include: get_count, list_counts'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!get_count_commands', badge_level)
    expected_response = 'Commands include: add_count, get_count, list_counts, remove_count, reset_count, set_count, ' \
                        'subtract_count'
    assert chatbot.response == expected_response


def test_count_commands(chatbot):
    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!set_count test_count 10', badge_level)
    expected_response = 'test_count: 10'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!set_count', badge_level)
    expected_response = 'Format: !set_count count_name number'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!set_count test count 10', badge_level)
    expected_response = 'Format: !set_count count_name number'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!set_count test_count blah', badge_level)
    expected_response = 'Format: !set_count count_name number'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!add_count test_count', badge_level)
    expected_response = 'test_count: 11'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!add_count', badge_level)
    expected_response = 'Format: !add_count count_name'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!add_count test_count 30', badge_level)
    expected_response = 'Format: !add_count count_name'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!subtract_count test_count', badge_level)
    expected_response = 'test_count: 10'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!subtract_count', badge_level)
    expected_response = 'Format: !subtract_count count_name'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!subtract_count test_count 30', badge_level)
    expected_response = 'Format: !subtract_count count_name'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!reset_count test_count', badge_level)
    expected_response = 'test_count: 0'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!reset_count ', badge_level)
    expected_response = 'Format: !reset_count count_name'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!reset_count test_count 30', badge_level)
    expected_response = 'Format: !reset_count count_name'
    assert chatbot.response == expected_response

    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_count test_count', badge_level)
    expected_response = 'test_count: 0'
    assert chatbot.response == expected_response

    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_count', badge_level)
    expected_response = 'Format: !get_count count_name'
    assert chatbot.response == expected_response

    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_count count with spaces', badge_level)
    expected_response = 'Format: !get_count count_name'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.CHAT]
    simulate_chat(chatbot, 'test_user', '!list_counts', badge_level)
    expected_response = 'Counts: test_count'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!remove_count test_count', badge_level)
    expected_response = 'test_count removed'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!remove_count ', badge_level)
    expected_response = 'Format: !remove_count count_name'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!remove_count test_count 30', badge_level)
    expected_response = 'Format: !remove_count count_name'
    assert chatbot.response == expected_response


# LISTS
def test_get_list_commands(chatbot):
    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_list_commands', badge_level)
    expected_response = 'Commands include: get_list_item, list_lists'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!get_list_commands', badge_level)
    expected_response = 'Commands include: add_list_item, get_list_item, list_lists, remove_list_item'
    assert chatbot.response == expected_response


def test_list_commands(chatbot):
    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!add_list_item test_list item_one', badge_level)
    expected_response = '1. item_one'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!add_list_item test_list item_two', badge_level)
    expected_response = '2. item_two'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!add_list_item', badge_level)
    expected_response = 'Format: !add_list_item list_name item to include in list'
    assert chatbot.response == expected_response

    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_list_item test_list 2', badge_level)
    expected_response = '2. item_two'
    assert chatbot.response == expected_response

    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_list_item test_list', badge_level)
    expected_responses = ['1. item_one', '2. item_two']
    assert chatbot.response in expected_responses

    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_list_item', badge_level)
    expected_response = 'Format: !get_list_item list_name [index]'
    assert chatbot.response == expected_response

    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_list_item test_list test', badge_level)
    expected_response = 'Format: !get_list_item list_name [index]'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!remove_list_item test_list 1', badge_level)
    expected_response = 'Removed 1. item_one'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!remove_list_item', badge_level)
    expected_response = 'Format: !remove_list_item list_name index'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!remove_list_item test)list test', badge_level)
    expected_response = 'Format: !remove_list_item list_name index'
    assert chatbot.response == expected_response

    badge_level = []
    simulate_chat(chatbot, 'test_user', '!list_lists', badge_level)
    expected_response = 'Lists: test_list'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.BROADCASTER]
    simulate_chat(chatbot, 'test_user', '!remove_list test_list', badge_level)
    expected_response = 'Removed list test_list'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.BROADCASTER]
    simulate_chat(chatbot, 'test_user', '!remove_list test_list', badge_level)
    expected_response = 'Removed list test_list'
    assert chatbot.response == expected_response

# ALERTS

def test_get_alert_commands(chatbot):
    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_alert_commands', badge_level)
    expected_response = 'Nice try test_user'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!get_alert_commands', badge_level)
    expected_response = 'Commands include: alert, ban, group_alert, unban'
    assert chatbot.response == expected_response


@mock.patch.object(twitchbot.TwitchBot, 'alert_api', new=fake_alert_api)
@mock.patch.object(twitchbot.TwitchBot, 'group_alert_api', new=fake_group_alert_api)
def test_alert_commands(chatbot, import_groups):
    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!alert test_text_1', badge_level)
    expected_response = '/me Test Text 1'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!alert', badge_level)
    expected_response = 'Format: !alert alert_name'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!alert test_text_1 blah', badge_level)
    expected_response = 'Format: !alert alert_name'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!group_alert first_two', badge_level)
    expected_response = ['/me Test Text 1', '/me Test Text 2']
    assert chatbot.response in expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!group_alert', badge_level)
    expected_response = 'Format: !group_alert group_alert_name'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!group_alert first_two blah', badge_level)
    expected_response = 'Format: !group_alert group_alert_name'
    assert chatbot.response == expected_response

    # banning

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!ban test_user2', badge_level)
    expected_response = 'Banned test_user2'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!ban', badge_level)
    expected_response = 'Format: !ban chatter'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user', '!ban test_user2 for real', badge_level)
    expected_response = 'Format: !ban chatter'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user2', '!alert test_text_1', badge_level)
    expected_response = 'Nice try test_user2'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user2', '!unban test_user2', badge_level)
    expected_response = 'Unbanned test_user2'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user2', '!unban', badge_level)
    expected_response = 'Format: !unban banned_chatter'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user2', '!unban test_user2 for real', badge_level)
    expected_response = 'Format: !unban banned_chatter'
    assert chatbot.response == expected_response

    badge_level = [models.Badges.MODERATOR]
    simulate_chat(chatbot, 'test_user2', '!alert test_text_1', badge_level)
    expected_response = '/me Test Text 1'
    assert chatbot.response == expected_response
