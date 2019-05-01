import pytest
import mock
import time
import re

from custom_stream_api.chatbot import aliases, twitchbot, models, timers
from custom_stream_api.alerts import alerts
from custom_stream_api.lists import lists
from custom_stream_api.counts import counts
from custom_stream_api.shared import g
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
        "alias": "test_alias_args",
        "badge": "vip",
        "command": "!set_count test_count"
    },
    {
        "alias": "mod_test_alias",
        "badge": "vip",
        "command": "!set_count test_count 10"
    },
    {
        "alias": "broadcaster_test_alias",
        "badge": "broadcaster",
        "command": "!set_count test_count 10"
    }
]

IMPORT_TIMERS = [
    {
        "command": "!echo test command",
        "interval": 2
    },
    {
        "command": "!echo test command 2",
        "interval": 3
    }
]


@pytest.fixture
def import_aliases(app):
    aliases.import_aliases(IMPORT_ALIASES)


@pytest.fixture
def import_timers(app):
    timers.import_timers(IMPORT_TIMERS)


@pytest.fixture
def import_alerts(app):
    alerts.import_alerts(IMPORT_ALERTS)


@pytest.fixture
def import_groups(import_alerts):
    alerts.import_groups(IMPORT_GROUP_ALERTS)


def fake_alert_api(cls, user, badges, alert):
    if user in lists.get_list('banned_users'):
        return
    elif not cls._badge_check(badges, models.Badges.VIP) and cls.spamming(user):
        cls.chat('No spamming {}. Wait another {} seconds.'.format(user, cls.timeout))
        return

    try:
        alerts.alert(name=alert, hit_socket=False, chat=True)
    except Exception as e:
        pass


def fake_group_alert_api(cls, user, badges, group_alert):
    if user in lists.get_list('banned_users'):
        return
    elif not cls._badge_check(badges, models.Badges.VIP) and cls.spamming(user):
        cls.chat('No spamming {}. Wait another {} seconds.'.format(user, cls.timeout))
        return

    try:
        alerts.group_alert(group_name=group_alert, hit_socket=False, chat=True)
    except Exception as e:
        pass


def fake_run_timer(cls, command, interval):
    while cls.run_timers:
        time.sleep(interval*0.5)
        cls.do_command(command, cls.bot_name, [], ignore_badges=True)


@pytest.fixture
def chatbot(app):
    # we don't need it to actually connect and listen to chat
    # just to respond the way we want it to

    def store_chat(cls, message):
        message = cls._substitute_vars(message)
        cls.responses.append(message)

    def fake_on_pubmsg(cls, connection, event):
        # If a chat message starts with an exclamation point, try to run it as a command
        tags = {tag['key']: tag['value'] for tag in event.tags}
        user = tags['display-name']
        badges = cls.get_user_badges(tags)
        command = event.arguments[0]
        if command[:1] == '!':
            try:
                cls.do_command(command, user, badges)
            except Exception as e:
                pass

    def fake_running(cls):
        return True

    with mock.patch.object(twitchbot.TwitchBot, 'chat', new=store_chat):
        with mock.patch.object(twitchbot.TwitchBot, 'on_pubmsg', new=fake_on_pubmsg):
            with mock.patch.object(twitchbot.TwitchBot, 'running', new=fake_running):
                bot = twitchbot.TwitchBot('test_id', 'test_botname', 'test_client_id', 'test_token', 'test_channel',
                                          timeout=0.1)
                bot.responses = []
                g['chatbot'] = {'object': bot}
                yield bot


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
    expected_responses = []
    assert chatbot.responses == expected_responses

    simulate_chat(chatbot, 'test_user', '!id', [models.Badges.BROADCASTER])
    expected_response = 'Chatbot ID - test_id'
    assert chatbot.responses[-1] == expected_response


def test_echo(chatbot):
    simulate_chat(chatbot, 'test_user', '!echo test test 1 2 3', [models.Badges.VIP])
    expected_responses = []
    assert chatbot.responses == expected_responses

    simulate_chat(chatbot, 'test_user', '!echo test test 1 2 3', [models.Badges.BROADCASTER])
    expected_response = 'test test 1 2 3'
    assert chatbot.responses[-1] == expected_response

def test_chatbot(chatbot):
    simulate_chat(chatbot, 'test_user', '!shoutout test_user', [models.Badges.SUBSCRIBER])
    expected_responses = []
    assert chatbot.responses == expected_responses

    simulate_chat(chatbot, 'test_user', '!shoutout test_user', [models.Badges.VIP])
    expected_response = 'Hey I know test_user! You should check\'em out and drop a follow ' \
                        '- https://www.twitch.tv/test_user'
    assert chatbot.responses[-1] == expected_response


def test_get_commands(chatbot):
    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_commands non-existent-badge', badge_level)
    expected_response = 'Format: !get_commands [{}]'.format(' | '.join(sorted(models.BADGE_NAMES)))
    assert chatbot.responses[-1] == expected_response

    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_commands', badge_level)
    expected_response = 'Commands include: get_aliases, get_commands, get_count_commands, get_list_commands, help'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.SUBSCRIBER]
    simulate_chat(chatbot, 'test_user', '!get_commands', badge_level)
    expected_response = 'Commands include: get_aliases, get_commands, get_count_commands, get_list_commands, help, '\
                        'spongebob'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!get_commands', badge_level)
    expected_response = 'Commands include: get_alert_commands, get_aliases, get_commands, get_count_commands, '\
                        'get_list_commands, help, random, shoutout, spongebob'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.BROADCASTER]
    simulate_chat(chatbot, 'test_user', '!get_commands', badge_level)
    expected_response = 'Commands include: disconnect, echo, get_alert_commands, get_aliases, get_commands, '\
                        'get_count_commands, get_list_commands, get_timer_commands, help, id, random, shoutout, ' \
                        'spongebob'
    assert chatbot.responses[-1] == expected_response

    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_commands broadcaster', badge_level)
    expected_response = 'Commands include: disconnect, echo, get_alert_commands, get_aliases, get_commands, '\
                        'get_count_commands, get_list_commands, get_timer_commands, help, id, random, shoutout, ' \
                        'spongebob'
    assert chatbot.responses[-1] == expected_response


def test_random(chatbot):
    simulate_chat(chatbot, 'test_user', '!random a b c', [models.Badges.SUBSCRIBER])
    expected_responses = []
    assert chatbot.responses == expected_responses

    simulate_chat(chatbot, 'test_user', '!random a', [models.Badges.VIP])
    expected_response = 'Format: !random option1 option2 [option3 ...]'
    assert chatbot.responses[-1] == expected_response

    simulate_chat(chatbot, 'test_user', '!random a b c', [models.Badges.VIP])
    expected_responses = ['Random choice: a', 'Random choice: b', 'Random choice: c']
    assert chatbot.responses[-1] in expected_responses


def test_spongebob(chatbot):
    simulate_chat(chatbot, 'test_user', '!spongebob', [models.Badges.SUBSCRIBER])
    expected_response = 'Format: !spongebob message'
    assert chatbot.responses[-1] == expected_response

    simulate_chat(chatbot, 'test_user', '!spongebob stop mimicking me', [models.Badges.SUBSCRIBER])
    expected_response = 'sToP MiMiCkInG Me - https://dannypage.github.io/assets/images/mocking-spongebob.jpg'
    assert chatbot.responses[-1] == expected_response

    simulate_chat(chatbot, 'test_user', '!spongebob stop mimicking me please', [])
    # unchanged
    assert chatbot.responses[-1] == expected_response


# ALIASES
def test_get_aliases_empty(chatbot):
    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_aliases', badge_level)
    expected_response = 'No commands available'
    assert chatbot.responses[-1] == expected_response


def test_import_export_aliases(import_aliases):
    assert aliases.list_aliases() == IMPORT_ALIASES


def test_remove_alias(import_aliases):
    aliases.remove_alias('chat_test_alias')
    all_aliases = [alias['alias'] for alias in aliases.list_aliases()]
    assert 'chat_test_alias' not in all_aliases


def test_get_aliases(import_aliases, chatbot):
    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_aliases', badge_level)
    expected_response = 'Commands include: chat_alert, chat_test_alias'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.SUBSCRIBER]
    simulate_chat(chatbot, 'test_user', '!get_aliases', badge_level)
    expected_response = 'Commands include: chat_alert, chat_test_alias, sub_test_alias'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!get_aliases', badge_level)
    expected_response = 'Commands include: chat_alert, chat_test_alias, mod_test_alias, sub_test_alias, test_alias_args'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.BROADCASTER]
    simulate_chat(chatbot, 'test_user', '!get_aliases', badge_level)
    expected_response = 'Commands include: broadcaster_test_alias, chat_alert, chat_test_alias, mod_test_alias, '\
                        'sub_test_alias, test_alias_args'
    assert chatbot.responses[-1] == expected_response


@mock.patch.object(twitchbot.TwitchBot, 'alert_api', new=fake_alert_api)
@mock.patch.object(twitchbot.TwitchBot, 'group_alert_api', new=fake_group_alert_api)
def test_aliases(import_aliases, import_groups, chatbot):
    badge_level = [models.Badges.SUBSCRIBER]
    simulate_chat(chatbot, 'test_user', '!mod_test_alias', badge_level)
    expected_responses = []
    assert chatbot.responses == expected_responses

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!mod_test_alias', badge_level)
    expected_response = 'test_count: 10'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!test_alias_args 14', badge_level)
    expected_response = 'test_count: 14'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!test_alias_args blah', badge_level)
    expected_response = 'Format: !test_alias_args number'
    assert chatbot.responses[-1] == expected_response

    badge_level = []
    simulate_chat(chatbot, 'test_user', '!chat_alert', badge_level)
    expected_response = '/me Test Text 1'
    assert chatbot.responses[-1] == expected_response

    # spam test
    badge_level = []
    simulate_chat(chatbot, 'test_user', '!chat_alert', badge_level)
    expected_response = 'No spamming {}. Wait another {} seconds.'.format('test_user', chatbot.timeout)
    assert chatbot.responses[-1] == expected_response


# TIMERS
def test_import_export_timers(import_timers):
    assert timers.list_timers() == IMPORT_TIMERS


def test_remove_timer(import_aliases):
    timers.remove_timer('!echo test command')
    all_timers = [timer['command'] for timer in timers.list_timers()]
    assert '!echo test command' not in all_timers


# TODO: Figure out passing the mock chat function to lower threads...
@pytest.mark.skip
@mock.patch.object(twitchbot.TwitchBot, 'run_timer', new=fake_run_timer)
def test_timers(import_timers, chatbot):
    chatbot.restart_timers()
    expected_response = 'test command'
    time.sleep(1)
    assert chatbot.responses[-1] == expected_response
    expected_response = 'test command 2'
    time.sleep(3)
    assert chatbot.responses[-1] == expected_response


# COUNTS
def test_get_count_commands(chatbot):
    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_count_commands', badge_level)
    expected_response = 'Commands include: get_count, list_counts'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!get_count_commands', badge_level)
    expected_response = 'Commands include: add_count, get_count, list_counts, remove_count, reset_count, set_count, '\
                        'subtract_count'
    assert chatbot.responses[-1] == expected_response


def test_count_commands(chatbot):
    badge_level = [models.Badges.CHAT]
    simulate_chat(chatbot, 'test_user', '!list_counts', badge_level)
    expected_responses = []
    assert chatbot.responses == expected_responses

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!set_count test_count 10', badge_level)
    expected_response = 'test_count: 10'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!set_count', badge_level)
    expected_response = 'Format: !set_count count_name number'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!set_count test count 10', badge_level)
    expected_response = 'Format: !set_count count_name number'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!set_count test_count blah', badge_level)
    expected_response = 'Format: !set_count count_name number'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!add_count test_count', badge_level)
    expected_response = 'test_count: 11'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!add_count test_count2', badge_level)
    expected_response = 'test_count2: 1'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!add_count', badge_level)
    expected_response = 'Format: !add_count count_name'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!add_count test_count 30', badge_level)
    expected_response = 'Format: !add_count count_name'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!subtract_count test_count', badge_level)
    expected_response = 'test_count: 10'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!subtract_count', badge_level)
    expected_response = 'Format: !subtract_count count_name'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!subtract_count test_count 30', badge_level)
    expected_response = 'Format: !subtract_count count_name'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!reset_count test_count', badge_level)
    expected_response = 'test_count: 0'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!reset_count test_count3', badge_level)
    expected_response = 'test_count3: 0'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!reset_count ', badge_level)
    expected_response = 'Format: !reset_count count_name'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!reset_count test_count 30', badge_level)
    expected_response = 'Format: !reset_count count_name'
    assert chatbot.responses[-1] == expected_response

    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_count test_count', badge_level)
    expected_response = 'test_count: 0'
    assert chatbot.responses[-1] == expected_response

    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_count', badge_level)
    expected_response = 'Format: !get_count count_name'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!get_count non_existent_count', badge_level)
    # unchanged
    assert chatbot.responses[-1] == expected_response

    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_count count with spaces', badge_level)
    expected_response = 'Format: !get_count count_name'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.CHAT]
    simulate_chat(chatbot, 'test_user', '!list_counts', badge_level)
    expected_response = 'Counts: test_count, test_count2, test_count3'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.BROADCASTER]
    simulate_chat(chatbot, 'test_user', '!echo Custom message {test_count}!{test_count2}', badge_level)
    expected_response = 'Custom message 0!1'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!remove_count test_count', badge_level)
    expected_response = 'test_count removed'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!remove_count ', badge_level)
    expected_response = 'Format: !remove_count count_name'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!remove_count test_count 30', badge_level)
    expected_response = 'Format: !remove_count count_name'
    assert chatbot.responses[-1] == expected_response


# LISTS
def test_get_list_commands(chatbot):
    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_list_commands', badge_level)
    expected_response = 'Commands include: get_list_item, get_list_size, list_lists'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!get_list_commands', badge_level)
    expected_response = 'Commands include: add_list_item, get_list_item, get_list_size, list_lists, remove_list_item'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.BROADCASTER]
    simulate_chat(chatbot, 'test_user', '!get_list_commands', badge_level)
    expected_response = 'Commands include: add_list_item, get_list_item, get_list_size, list_lists, remove_list, '\
                        'remove_list_item'
    assert chatbot.responses[-1] == expected_response


def test_list_commands(chatbot):
    badge_level = []
    simulate_chat(chatbot, 'test_user', '!list_lists', badge_level)
    expected_responses = []
    assert chatbot.responses == expected_responses

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!add_list_item test_list item_one', badge_level)
    expected_response = '1. item_one'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!add_list_item test_list item_two', badge_level)
    expected_response = '2. item_two'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!add_list_item', badge_level)
    expected_response = 'Format: !add_list_item list_name item to include in list'
    assert chatbot.responses[-1] == expected_response

    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_list_item test_list 2', badge_level)
    expected_response = '2. item_two'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.BROADCASTER]
    simulate_chat(chatbot, 'test_user', '!echo 1.{test_list 1} 2.{test_list 2}', badge_level)
    expected_response = '1.item_one 2.item_two'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.BROADCASTER]
    simulate_chat(chatbot, 'test_user', '!echo random.{test_list}', badge_level)
    expected_responses = ['random.item_one', 'random.item_two']
    assert chatbot.responses[-1] in expected_responses

    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_list_item test_list', badge_level)
    expected_responses = ['1. item_one', '2. item_two']
    assert chatbot.responses[-1] in expected_responses

    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_list_item non_existent_list 1', badge_level)
    # unchanged
    assert chatbot.responses[-1] in expected_responses

    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_list_item test_list 1000', badge_level)
    # unchanged
    assert chatbot.responses[-1] in expected_responses

    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_list_item', badge_level)
    expected_response = 'Format: !get_list_item list_name [index]'
    assert chatbot.responses[-1] == expected_response

    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_list_item test_list test', badge_level)
    expected_response = 'Format: !get_list_item list_name [index]'
    assert chatbot.responses[-1] == expected_response

    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_list_size test_list', badge_level)
    expected_response = 'test_list size: 2'
    assert chatbot.responses[-1] == expected_response

    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_list_size test_list extra', badge_level)
    expected_response = 'Format: !get_list_size list_name'
    assert chatbot.responses[-1] == expected_response

    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_list_size', badge_level)
    expected_response = 'Format: !get_list_size list_name'
    assert chatbot.responses[-1] == expected_response

    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_list_size non_existent_list', badge_level)
    # unchanged
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!remove_list_item test_list 1', badge_level)
    expected_response = 'Removed 1. item_one'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!remove_list_item test_list 1', badge_level)
    expected_response = 'Removed 1. item_two'
    assert chatbot.responses[-1] == expected_response

    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_list_item test_list', badge_level)
    # unchanged
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!remove_list_item non_existent_list 1', badge_level)
    # unchanged
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!remove_list_item', badge_level)
    expected_response = 'Format: !remove_list_item list_name index'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!remove_list_item test_list test', badge_level)
    expected_response = 'Format: !remove_list_item list_name index'
    assert chatbot.responses[-1] == expected_response

    badge_level = []
    simulate_chat(chatbot, 'test_user', '!list_lists', badge_level)
    expected_response = 'Lists: test_list'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.BROADCASTER]
    simulate_chat(chatbot, 'test_user', '!remove_list test_list', badge_level)
    expected_response = 'Removed list test_list'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.BROADCASTER]
    simulate_chat(chatbot, 'test_user', '!remove_list test_list', badge_level)
    expected_response = 'Removed list test_list'
    assert chatbot.responses[-1] == expected_response


# ALERTS
def test_get_alert_commands(chatbot):
    badge_level = []
    simulate_chat(chatbot, 'test_user', '!get_alert_commands', badge_level)
    expected_responses = []
    assert chatbot.responses == expected_responses

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!get_alert_commands', badge_level)
    expected_response = 'Commands include: alert, ban, group_alert, unban'
    assert chatbot.responses[-1] == expected_response


@mock.patch.object(twitchbot.TwitchBot, 'alert_api', new=fake_alert_api)
@mock.patch.object(twitchbot.TwitchBot, 'group_alert_api', new=fake_group_alert_api)
def test_alert_commands(chatbot, import_groups):
    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!alert test_text_1', badge_level)
    expected_response = '/me Test Text 1'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!alert', badge_level)
    expected_response = 'Format: !alert alert_name'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!alert test_text_1 blah', badge_level)
    expected_response = 'Format: !alert alert_name'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!group_alert first_two', badge_level)
    expected_responses = ['/me Test Text 1', '/me Test Text 2']
    assert chatbot.responses[-1] in expected_responses

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!group_alert last_two', badge_level)
    expected_response = 'last two!'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!group_alert', badge_level)
    expected_response = 'Format: !group_alert group_alert_name'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!group_alert first_two blah', badge_level)
    expected_response = 'Format: !group_alert group_alert_name'
    assert chatbot.responses[-1] == expected_response

    # banning

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!ban test_user2', badge_level)
    expected_response = 'Banned test_user2'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!ban', badge_level)
    expected_response = 'Format: !ban chatter'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user', '!ban test_user2 for real', badge_level)
    expected_response = 'Format: !ban chatter'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user2', '!alert test_text_1', badge_level)
    # unchanged
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user2', '!unban test_user2', badge_level)
    expected_response = 'Unbanned test_user2'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user2', '!unban', badge_level)
    expected_response = 'Format: !unban banned_chatter'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user2', '!unban test_user2 for real', badge_level)
    expected_response = 'Format: !unban banned_chatter'
    assert chatbot.responses[-1] == expected_response

    badge_level = [models.Badges.VIP]
    simulate_chat(chatbot, 'test_user2', '!alert test_text_1', badge_level)
    expected_response = '/me Test Text 1'
    assert chatbot.responses[-1] == expected_response


def test_stress(chatbot):
    badge_level = [models.Badges.BROADCASTER]
    expected_responses = []
    for i in range(0, 1000):
        message = 'Message {}'.format(i)
        simulate_chat(chatbot, 'test_user2', '!echo {}'.format(message), badge_level)
        expected_responses.append(message)
    assert chatbot.responses == expected_responses


@pytest.mark.skip
# TODO: mock chat threading
def test_queue_messages(chatbot):
    badge_level = [models.Badges.BROADCASTER]
    simulate_chat(chatbot, 'test_user', '!echo slow message', badge_level)
    simulate_chat(chatbot, 'test_user', '!echo fast message', badge_level)
    expected_responses = [
        'slow message',
        'fast message'
    ]
    assert chatbot.responses == expected_responses
