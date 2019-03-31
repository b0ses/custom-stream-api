'''
Initial template from twitchdev/chat-samples
'''

import logging
import sys
import threading
import time
import uuid
import re

import irc.bot
import requests

from custom_stream_api.shared import app, g
from custom_stream_api.chatbot.models import Badges, BADGE_LEVELS
from custom_stream_api.chatbot import aliases
from custom_stream_api.counts import counts
from custom_stream_api.lists import lists
from custom_stream_api.alerts import alerts

logger = logging.getLogger()


class TwitchBot(irc.bot.SingleServerIRCBot):
    def __init__(self, chatbot_id, bot_name, client_id, token, channel, timeout=30):
        self.chatbot_id = chatbot_id
        self.client_id = client_id
        self.token = token
        self.channel = '#' + channel

        self.badge_levels = BADGE_LEVELS

        self.timeout = timeout  # in seconds
        self.timeouts = {}

        self.commands = {}
        self.update_commands()

    def connect(self):
        # Get the channel id, we will need this for v5 API calls
        url = 'https://api.twitch.tv/kraken/users?login=' + self.channel
        headers = {'Client-ID': self.client_id, 'Accept': 'application/vnd.twitchtv.v5+json'}
        r = requests.get(url, headers=headers).json()
        try:
            self.channel_id = r['users'][0]['_id']
        except KeyError:
            raise Exception('Unable to connect with the provided credentials')

        # Create IRC bot connection
        server = 'irc.chat.twitch.tv'
        port = 6667
        logger.info('Connecting to ' + server + ' on port ' + str(port) + '...')
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port, 'oauth:' + self.token)], self.bot_name, self.bot_name)

    def on_welcome(self, connection, event):
        logger.info('Joining ' + self.channel)

        # You must request specific capabilities before you can use them
        connection.cap('REQ', ':twitch.tv/membership')
        connection.cap('REQ', ':twitch.tv/tags')
        connection.cap('REQ', ':twitch.tv/commands')
        connection.join(self.channel)

    def chat(self, message):
        c = self.connection
        c.privmsg(self.channel, message)


    # PARSE MESSAGES

    def on_pubmsg(self, connection, event):
        # If a chat message starts with an exclamation point, try to run it as a command
        tags = {tag['key']: tag['value'] for tag in event.tags}
        user = tags['display-name']
        badges = self.get_user_badges(tags)
        command = event.arguments[0]
        if command[:1] == '!':
            logger.info('{} (badges:{}) commanded: {}'.format(user, badges, command))
            self.do_command(command, user, badges)

    def get_user_badges(self, tags):
        badges = [Badges.CHAT]  # baseline
        user_bages_str = tags['badges'] or ''
        for badge in user_bages_str.split(','):
            badge_string = badge.split('/')[0]
            badge = self.get_badge(badge_string)
            if badge:
                badges.append(badge)
        return badges

    def get_badge(self, badge_string):
        badge_objects = list(filter(lambda badge: badge.value == badge_string, list(Badges)))
        if badge_objects:
            return badge_objects[0]
        else:
            logger.warning('Possible new badge: {}'.format(badge_string))

    def get_min_badge(self, badges):
        min_badge = Badges.CHAT
        if badges:
            min_badge = sorted(badges, key=lambda badge: self.badge_levels.index(badge))[0]
        return min_badge

    def get_max_badge(self, badges):
        max_badge = Badges.CHAT
        if badges:
            max_badge = sorted(badges, key=lambda badge: self.badge_levels.index(badge))[-1]
        return max_badge

    def do_command(self, text, user, badges):
        argv = text.split(' ')
        command_name = argv[0][1:]
        command_text = ' '.join(argv[1:])

        found_command = self.commands.get(command_name, None)
        if not found_command:
            return

        if command_name == 'mod_test_alias':
            print(self.get_max_badge(badges), found_command['badge'])
        if self.badge_levels.index(self.get_max_badge(badges)) < self.badge_levels.index(found_command['badge']):
            self.chat('Nice try {}'.format(user))
            return

        found_command['callback'](command_text, user, badges)


    # COMMANDS

    def update_commands(self):
        # Order is important, just make sure main commands is last
        self.set_count_commands()
        self.commands.update(self.count_commands)
        self.set_list_commands()
        self.commands.update(self.list_commands)
        self.set_alert_commands()
        self.commands.update(self.alert_commands)
        self.set_aliases()
        self.commands.update(self.aliases)
        self.set_main_commands()
        self.commands.update(self.main_commands)

    def set_main_commands(self):
        self.main_commands = {
            'id': {
                'badge': Badges.BROADCASTER,
                'callback': lambda text, user, badges: self.get_chatbot_id()
            },
            'get_commands': {
                'badge': Badges.CHAT,
                'callback': lambda text, user, badges: self.display_commands(self.main_commands, text, badges)
            },
            'get_count_commands': {
                'badge': self.get_min_badge([command['badge'] for command in self.count_commands.values()]),
                'callback': lambda text, user, badges: self.display_commands(self.count_commands, text, badges)
            },
            'get_list_commands': {
                'badge': self.get_min_badge([command['badge'] for command in self.list_commands.values()]),
                'callback': lambda text, user, badges: self.display_commands(self.list_commands, text, badges)
            },
            'get_alert_commands': {
                'badge': self.get_min_badge([command['badge'] for command in self.alert_commands.values()]),
                'callback': lambda text, user, badges: self.display_commands(self.alert_commands, text, badges)
            },
            'get_aliases': {
                'badge': self.get_min_badge([command['badge'] for command in self.aliases.values()]),
                'callback': lambda text, user, badges: self.display_commands(self.aliases, text, badges)
            },
            'spongebob': {
                'badge': Badges.SUBSCRIBER,
                'callback': lambda text, user, badges: self.spongebob(text)
            }
        }

    def display_commands(self, commands, badge_level, user_badges=None):
        if not badge_level:
            badge = self.get_max_badge(user_badges)
        else:
            badge = self.get_badge(badge_level)
        badge_index = self.badge_levels.index(badge) if badge else -1
        filtered_commands = sorted([command for command, command_dict in commands.items()
                                    if badge_index >= self.badge_levels.index(command_dict['badge'])])

        if filtered_commands:
            clean_reactions = str(filtered_commands)[1:-1].replace('\'', '')
            msg = 'Commands include: {}'.format(clean_reactions)
        else:
            msg = 'No commands available'
        self.chat(msg)

    # Chatbot ID

    def get_chatbot_id(self):
        self.chat('Chatbot ID - {}'.format(self.chatbot_id))

    # Alises
    def set_aliases(self):
        self.aliases = {}
        for alias in aliases.list_aliases():
            # Remember to *bind* when looping and making lambdas!
            self.aliases[alias['alias']] = {
                'badge': self.get_badge(alias['badge']),
                'callback': lambda text, user, badges, command=alias['command']: self.do_command(command, user, badges),
            }

    # Counts
    def set_count_commands(self):
        self.count_commands = {
            'get_count': {
                'badge': Badges.CHAT,
                'callback': lambda text, user, badges: self.chat_count_output(text, counts.get_count(text))
            },
            'set_count': {
                'badge': Badges.MODERATOR,
                'callback': lambda text, user, badges: self.chat_count_output(text.split()[0],
                                                                              counts.set_count(text.split()[0],
                                                                                               text.split()[1]))
            },
            'reset_count': {
                'badge': Badges.MODERATOR,
                'callback': lambda text, user, badges: self.chat_count_output(text, counts.reset_count(text))
            },
            'remove_count': {
                'badge': Badges.MODERATOR,
                'callback': lambda text, user, badges: self.remove_count_output(text)
            },
            'add_count': {
                'badge': Badges.MODERATOR,
                'callback': lambda text, user, badges: self.chat_count_output(text, counts.add_to_count(text))
            },
            'subtract_count': {
                'badge': Badges.MODERATOR,
                'callback': lambda text, user, badges: self.chat_count_output(text, counts.subtract_from_count(text))
            }
        }

    def chat_count_output(self, count_name, count):
        self.chat('{}: {}'.format(count_name, count))

    def remove_count_output(self, count_name):
        counts.remove_count(count_name)
        self.chat('{} removed'.format(count_name))


    # Lists
    def set_list_commands(self):
        self.list_commands = {
            'get_list_item': {
                'badge': Badges.CHAT,
                'callback': lambda text, user, badges: self.get_list_item(text.split()[0], text.split()[1])
            },
            'add_list_item': {
                'badge': Badges.MODERATOR,
                'callback': lambda text, user, badges: self.add_list_item(text.split()[0], text.split()[1])
            },
            'remove_list_item': {
                'badge': Badges.MODERATOR,
                'callback': lambda text, user, badges: self.remove_list_item(text.split()[0], text.split()[1])
            }
        }

    def get_list_item(self, list_name, index):
        self.output_list_item(index, lists.get_list_item(list_name, int(index)-1))

    def add_list_item(self, list_name, item):
        index = len(lists.get_list(list_name)) + 1
        lists.add_to_list(list_name, [item])
        self.output_list_item(index, item)

    def remove_list_item(self, list_name, index):
        item = lists.remove_from_list(list_name, int(index)-1)
        self.chat('Removed {}. {}'.format(index, item))

    def output_list_item(self, index, item):
        self.chat('{}. {}'.format(index, item))

    # Alerts
    def set_alert_commands(self):
        self.alert_commands = {
            'alert': {
                'badge': Badges.MODERATOR,
                'callback': lambda text, user, badges: self.alert_api(user, text),
            },
            'group_alert': {
                'badge': Badges.MODERATOR,
                'callback': lambda text, user, badges: self.group_alert_api(user, text)
            },
            'ban': {
                'badge': Badges.MODERATOR,
                'callback': lambda text, user, badges: self.ban(text)
            },
            'unban': {
                'badge': Badges.MODERATOR,
                'callback': lambda text, user, badges: self.unban(text)
            }
        }

    def alert_api(self, user, alert):
        if user in lists.get_list('banned_users'):
            self.chat('Nice try {}'.format(user))
            return
        elif self.spamming(user):
            self.chat('No spamming {}. Wait another {} seconds.'.format(user, self.timeout))
            return

        try:
            message = alerts.alert(name=alert)
            self.chat('/me {}'.format(message))
        except Exception as e:
            pass

    def group_alert_api(self, user, group_alert):
        if user in lists.get_list('banned_users'):
            self.chat('Nice try {}'.format(user))
            return
        elif self.spamming(user):
            self.chat('No spamming {}. Wait another {} seconds.'.format(user, self.timeout))
            return

        try:
            message = alerts.group_alert(group_name=group_alert)
            self.chat('/me {}'.format(message))
        except Exception:
            pass

    def ban(self, ban_user):
        if ban_user:
            lists.add_to_list('banned_users', [ban_user])
            self.chat('Banned {}'.format(ban_user))
            return ban_user

    def unban(self, unban_user):
        if unban_user:
            banned_users = lists.get_list('banned_users')
            lists.set_list('banned_users', [user for user in banned_users if user != unban_user])
            self.chat('Unbanned {}'.format(unban_user))
            return unban_user

    # Extra commands

    def spongebob(self, text):
        spongebob_message = ''.join([k.upper() if index % 2 else k.lower() for index, k in enumerate(text)])
        spongebob_url = 'https://dannypage.github.io/assets/images/mocking-spongebob.jpg'
        self.chat('{} - {}'.format(spongebob_message, spongebob_url))

    # Helper commands

    def spamming(self, user):
        spamming = (user in self.timeouts and ((time.time() - self.timeouts[user]) < self.timeout))
        self.timeouts[user] = time.time()
        return spamming


def start_chatbot_with_app(app, chatbot):
    with app.app_context():
        try:
            chatbot.start()
        except OSError:
            logger.info('Disconnected')


def setup_chatbot(bot_name, client_id, chat_token, channel, timeout=30):
    if 'chatbot' in g:
        raise Exception('Chatbot already setup')
    chatbot_id = uuid.uuid4()
    try:
        chatbot = TwitchBot(chatbot_id=chatbot_id, bot_name=bot_name, client_id=client_id, token=chat_token,
                            channel=channel, timeout=timeout)
        chatbot.connect()
        chatbot_thread = threading.Thread(target=start_chatbot_with_app, args=(app, chatbot,))
        chatbot_thread.start()
    except Exception as e:
        logger.exception(e)
        raise Exception('Unable to start chatbot with the provided settings')

    g['chatbot'] = chatbot
    return chatbot_id


def verify_chatbot_id(chatbot_id):
    chatbot = g.get('chatbot', None)
    if chatbot and chatbot.chatbot_id == uuid.UUID(chatbot_id):
        return chatbot
    else:
        raise Exception('Chatbot ID not found')


def stop_chatbot(chatbot_id):
    chatbot = verify_chatbot_id(chatbot_id)
    chatbot.disconnect()
    del g['chatbot']


def main():
    if len(sys.argv) != 6:
        print("Usage: twitchbot <username> <client id> <token> <channel>")
        sys.exit(1)

    username = sys.argv[1]
    client_id = sys.argv[2]
    token = sys.argv[3]
    channel = sys.argv[4]

    bot = TwitchBot(username, client_id, token, channel)
    bot.connect()
    bot.start()


if __name__ == "__main__":
    main()
