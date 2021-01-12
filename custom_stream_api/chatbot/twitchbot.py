'''
Initial template from twitchdev/chat-samples
'''

import logging
import sys
import threading
import time
import uuid
import re
import random
from functools import partial
from collections import deque
import sre_constants

import irc.bot
import requests

from custom_stream_api.shared import app, g
from custom_stream_api.chatbot.models import Badges, BADGE_LEVELS, BADGE_NAMES
from custom_stream_api.chatbot import aliases, timers
from custom_stream_api.counts import counts
from custom_stream_api.lists import lists
from custom_stream_api.alerts import alerts
from custom_stream_api.lights import lights

logger = logging.getLogger()


class TwitchBot(irc.bot.SingleServerIRCBot):
    def __init__(self, chatbot_id, bot_name, client_id, token, channel, timeout=15, app=None):
        self.chatbot_id = chatbot_id
        self.bot_name = bot_name
        self.client_id = client_id
        self.token = token
        self.channel = '#' + channel
        self.app = app

        self.badge_levels = BADGE_LEVELS

        self.timers = []
        self.timeout = timeout  # in seconds
        self.timeouts = {}

        self.queue = deque()
        self.commands = {}
        self.update_commands()

    def connect_to_channel(self):
        # Get the channel id, we will need this for v5 API calls
        url = 'https://api.twitch.tv/kraken/users?login=' + self.channel[1:]
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
        connection.add_global_handler('USERNOTICE', self.on_usernotice, 90)
        connection.join(self.channel)
        while not connection.is_connected():
            time.sleep(0.5)
        self.chat('Hey 👋')
        self.restart_timers()
        self.message_thread = threading.Thread(target=self.process_messages)
        self.message_thread.start()

    def running(self):
        return (hasattr(self, 'connection') and self.connection.is_connected())

    def _substitute_vars(self, message):
        # edit message to replace {count_name} with count number
        for variable in re.findall('{(.*?)}', message):
            variable = variable.strip()

            # if it's a count name, return the count
            found_count = counts.get_count(variable)
            if found_count is not None:
                message = message.replace('{{{}}}'.format(variable), str(found_count))
                continue

            # if it's a list, return a random one or use the index
            list_params = variable.split()
            list_name = list_params[0]
            if list_name not in [list_dict['name'] for list_dict in lists.list_lists()]:
                continue

            index = None
            try:
                # accounting for negative indexes
                pulled_index = int(list_params[1])-1
                if pulled_index < lists.get_list_size(name=list_name):
                    index = pulled_index
            except (ValueError, IndexError):
                pass

            found_item, index = lists.get_list_item(name=list_name, index=index)
            if found_item is not None:
                message = message.replace('{{{}}}'.format(variable), found_item)
                continue

        return message

    def chat(self, message):
        message = self._substitute_vars(message)
        c = self.connection
        c.privmsg(self.channel, message)

    def disconnect(self):
        self.chat('Cya 👋')
        self.stop_timers()
        super().disconnect()
        while self.running():
            time.sleep(1)
        exit()

    # NOTIFICATIONS

    def on_usernotice(self, connection, event):
        logger.warning('USERNOTICE:{}'.format(event))

    # PARSE MESSAGES

    def on_pubmsg(self, connection, event):
        # If a chat message starts with an exclamation point, try to run it as a command
        tags = {tag['key']: tag['value'] for tag in event.tags}
        user = tags['display-name']
        badges = self.get_user_badges(tags)
        command = event.arguments[0]
        if command[:1] == '!':
            logger.info('{} (badges:{}) commanded: {}'.format(user, badges, command))
            try:
                self.queue.appendleft({'command': command, 'user': user, 'badges': badges})
            except Exception as e:
                logger.exception(e)

    def process_messages(self):
        def go():
            while self.running():
                if len(self.queue):
                    message = self.queue.pop()
                    self.do_command(message['command'], message['user'], message['badges'])
                time.sleep(0.5)

        if self.app:
            with self.app.app_context():
                go()
        else:
            go()
        exit()

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

    def _badge_check(self, badges, badge_level):
        max_user_badge = self.badge_levels.index(self.get_max_badge(badges))
        return max_user_badge >= self.badge_levels.index(badge_level)

    def do_command(self, text, user, badges, ignore_badges=False):
        strip_text = text.strip()
        argv = strip_text.split(' ')
        command_name = argv[0][1:]
        command_text = ' '.join(argv[1:])

        found_command = self.commands.get(command_name, None)
        if not found_command:
            return

        if (not ignore_badges) and not self._badge_check(badges, found_command['badge']):
            return

        if not re.match(found_command['format'], strip_text):
            self.chat('Format: {}'.format(found_command['help']))
            return

        found_command['callback'](command_text, user, badges)

    # COMMANDS

    def update_commands(self):
        # Order is important!
        self.set_count_commands()
        self.commands.update(self.count_commands)
        self.set_list_commands()
        self.commands.update(self.list_commands)
        self.set_alert_commands()
        self.commands.update(self.alert_commands)
        self.set_timer_commands()
        self.commands.update(self.timer_commands)
        self.set_light_commands()
        self.commands.update(self.light_commands)
        self.set_main_commands()
        self.commands.update(self.main_commands)
        # has to be second to last
        self.set_aliases()
        self.commands.update(self.aliases)
        # has to be last
        self.set_get_commands()
        self.commands.update(self.main_commands)

    def set_main_commands(self):
        self.main_commands = {
            'id': {
                'badge': Badges.BROADCASTER,
                'format': '^!id$',
                'help': '!id',
                'callback': lambda text, user, badges: self.get_chatbot_id()
            },
            'disconnect': {
                'badge': Badges.BROADCASTER,
                'format': '^!disconnect$',
                'help': '!disconnect',
                'callback': lambda text, user, badges: self.disconnect()
            },
            'echo': {
                'badge': Badges.BROADCASTER,
                'format': '^!echo\s+.*$',
                'help': '!echo message',
                'callback': lambda text, user, badges: self.chat(text)
            },
            'help': {
                'badge': Badges.CHAT,
                'format': '^!help$',
                'help': '!help',
                'callback': lambda text, user, badges: self.help(badges)
            },
            'random': {
                'badge': Badges.VIP,
                'format': '^!random(\s+\S+){2,}$',
                'help': '!random option1 option2 [option3 ...]',
                'callback': lambda text, user, badges: self.random(text)
            },
            'shoutout': {
                'badge': Badges.VIP,
                'format': '^!shoutout\s+\S+$',
                'help': '!shoutout user',
                'callback': lambda text, user, badges: self.shoutout(text)
            },
            'spongebob': {
                'badge': Badges.SUBSCRIBER,
                'format': '^!spongebob\s+.+$',
                'help': '!spongebob message',
                'callback': lambda text, user, badges: self.spongebob(text)
            },
            'taco': {
                'badge': Badges.SUBSCRIBER,
                'format': '^!taco\s+\S+$',
                'help': '!taco [to_user]',
                'callback': lambda text, user, badges: self.taco(user, text)
            }
        }

    def set_get_commands(self):
        self.get_commands = {
            'get_commands': {
                'badge': Badges.CHAT,
                'format': '^!get_commands\s*({})?$'.format('|'.join(BADGE_NAMES)),
                'help': '!get_commands [{}]'.format(' | '.join(sorted(BADGE_NAMES))),
                'callback': lambda text, user, badges: self.display_commands(self.main_commands, text, badges)
            },
            'get_count_commands': {
                'badge': self.get_min_badge([command['badge'] for command in self.count_commands.values()]),
                'format': '^!get_count_commands\s*({})?$'.format('|'.join(BADGE_NAMES)),
                'help': '!get_count_commands [{}]'.format(' | '.join(sorted(BADGE_NAMES))),
                'callback': lambda text, user, badges: self.display_commands(self.count_commands, text, badges)
            },
            'get_list_commands': {
                'badge': self.get_min_badge([command['badge'] for command in self.list_commands.values()]),
                'format': '^!get_list_commands\s*({})?$'.format('|'.join(BADGE_NAMES)),
                'help': '!get_list_commands [{}]'.format(' | '.join(sorted(BADGE_NAMES))),
                'callback': lambda text, user, badges: self.display_commands(self.list_commands, text, badges)
            },
            'get_alert_commands': {
                'badge': self.get_min_badge([command['badge'] for command in self.alert_commands.values()]),
                'format': '^!get_alert_commands\s*({})?$'.format('|'.join(BADGE_NAMES)),
                'help': '!get_alert_commands [{}]'.format(' | '.join(sorted(BADGE_NAMES))),
                'callback': lambda text, user, badges: self.display_commands(self.alert_commands, text, badges)
            },
            'get_timer_commands': {
                'badge': self.get_min_badge([command['badge'] for command in self.timer_commands.values()]),
                'format': '^!get_timer_commands\s*({})?$'.format('|'.join(BADGE_NAMES)),
                'help': '!get_timer_commands [{}]'.format(' | '.join(sorted(BADGE_NAMES))),
                'callback': lambda text, user, badges: self.display_commands(self.timer_commands, text, badges)
            },
            'get_light_commands': {
                'badge': self.get_min_badge([command['badge'] for command in self.light_commands.values()]),
                'format': '^!get_light_commands\s*({})?$'.format('|'.join(BADGE_NAMES)),
                'help': '!get_light_commands [{}]'.format(' | '.join(sorted(BADGE_NAMES))),
                'callback': lambda text, user, badges: self.display_commands(self.light_commands, text, badges)
            },
            'get_aliases': {
                'badge': self.get_min_badge([command['badge'] for command in self.aliases.values()]),
                'format': '^!get_aliases\s*({})?$'.format('|'.join(BADGE_NAMES)),
                'help': '!get_aliases [{}]'.format(' | '.join(sorted(BADGE_NAMES))),
                'callback': lambda text, user, badges: self.display_commands(self.aliases, text, badges)
            }
        }
        self.main_commands.update(self.get_commands)

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
            strip_text = alias['command'].strip()
            argv = strip_text.split(' ')
            command_name = argv[0][1:]
            found_command = self.commands.get(command_name, None)
            if not found_command:
                logger.info('not adding {}'.format(alias['alias']))
                continue

            alias_format = self._get_alias_format(found_command['format'], alias)
            if not alias_format:
                logger.info('not adding {} due to formatting'.format(alias['alias']))

            self.aliases[alias['alias']] = {
                'badge': self.get_badge(alias['badge']),
                'callback': partial(self.alias_redirect, strip_text),
                'format': alias_format,
                'help': self._get_alias_help(found_command['help'], alias)
            }

    def _get_alias_format(self, original_format, alias):
        match = None
        index = 1
        while not match and index < len(original_format):
            try:
                match = re.match('^{}$'.format(original_format[1:index]), alias['command'])
            except sre_constants.error:
                match = False
            if not match:
                index += 1
        if not match:
            return
        return '^!{}{}$'.format(alias['alias'], original_format[index:-1])

    def _get_alias_help(self, original_help, alias):
        num_of_spaces = len(alias['command'].strip().split()) - 1
        num_of_expected_spaces = len(original_help.split()) - 1
        rest_of_help = ''
        if num_of_spaces < num_of_expected_spaces:
            rest_of_help = ' ' + ' '.join(original_help.split()[num_of_spaces + 1:])
        return '!{}{}'.format(alias['alias'], rest_of_help)

    def alias_redirect(self, command, text, user, badges):
        self.do_command(command + ' ' + text, user, badges, ignore_badges=True)

    # Timers
    def set_timer_commands(self):
        self.timer_commands = {
            'restart_timers': {
                'badge': Badges.BROADCASTER,
                'callback': lambda text, user, badges: self.restart_timers(),
                'format': '^!restart_timers$',
                'help': '!restart_timers'
            },
            'stop_timers': {
                'badge': Badges.BROADCASTER,
                'callback': lambda text, user, badges: self.stop_timers(),
                'format': '^!stop_timers$',
                'help': '!stop_timers'
            },
            'reminder': {
                'badge': Badges.VIP,
                'callback': lambda text, user, badges: self.remind(text),
                'format': '^!reminder\s+\S+\s+\d+\s+.+$',
                'help': '!reminder [alert] [minutes] message'
            }
        }

    def stop_timers(self):
        # kill the previous timers
        self.run_timers = False
        for timer_thread in self.timers:
            timer_thread.join()
        self.timers = []

    def restart_timers(self):
        self.stop_timers()

        self.run_timers = True
        for timer_dict in timers.list_timers():
            timer_thread = threading.Thread(target=self.run_timer, args=(timer_dict['command'], timer_dict['interval'],
                                                                         True))
            timer_thread.start()
            self.timers.append(timer_thread)

    def remind(self, text):
        alert, minutes = tuple(text.split(' ')[:2])
        message = text[text.index(minutes)+len(minutes)+1:]
        echo_cmd = '!echo Reminder: {}'.format(message)
        alert_cmd = '!alert {}'.format(alert)
        alert_thread = threading.Thread(target=self.run_timer, args=(alert_cmd, int(minutes)))
        echo_thread = threading.Thread(target=self.run_timer, args=(echo_cmd, int(minutes)))
        alert_thread.start()
        # adding partial sleep to ensure it gets printed in the same order
        time.sleep(0.5)
        echo_thread.start()
        self.chat('Setup reminder \"{}\" in {} minutes'.format(message, str(minutes)))

    def run_timer(self, command, interval=30, loop=False):
        with self.app.app_context():
            counting_seconds = 0
            while self.run_timers:
                if counting_seconds == interval * 60:
                    self.do_command(command, self.bot_name, [], ignore_badges=True)
                    if not loop:
                        break
                    counting_seconds = 0
                time.sleep(1)
                counting_seconds += 1

    # Counts

    def set_count_commands(self):
        self.count_commands = {
            'list_counts': {
                'badge': Badges.CHAT,
                'callback': lambda text, user, badges: self.list_counts(),
                'format': '^!list_counts$',
                'help': '!list_counts'
            },
            'get_count': {
                'badge': Badges.CHAT,
                'callback': lambda text, user, badges: self.chat_count_output(text, counts.get_count(text)),
                'format': '^!get_count\s+\S+$',
                'help': '!get_count count_name'
            },
            'set_count': {
                'badge': Badges.VIP,
                'callback': lambda text, user, badges: self.chat_count_output(text.split()[0],
                                                                              counts.set_count(text.split()[0],
                                                                                               text.split()[1])),
                'format': '^!set_count\s+\S+\s+\d+$',
                'help': '!set_count count_name number'
            },
            'copy_count': {
                'badge': Badges.VIP,
                'callback': lambda text, user, badges: self.copy_count(text),
                'format': '^!copy_count\s+\S+\s+\S+$',
                'help': '!copy_count count_from count_to'
            },
            'reset_count': {
                'badge': Badges.VIP,
                'callback': lambda text, user, badges: self.reset_count(text),
                'format': '^!reset_count(\s+\S+)+$',
                'help': '!reset_count count_name1 count_name2 ...'
            },
            'remove_count': {
                'badge': Badges.VIP,
                'callback': lambda text, user, badges: self.remove_count_output(text),
                'format': '^!remove_count\s+\S+$',
                'help': '!remove_count count_name'
            },
            'add_count': {
                'badge': Badges.VIP,
                'callback': lambda text, user, badges: self.chat_count_output(text, counts.add_to_count(text)),
                'format': '^!add_count\s+\S+$',
                'help': '!add_count count_name'
            },
            'subtract_count': {
                'badge': Badges.VIP,
                'callback': lambda text, user, badges: self.chat_count_output(text, counts.subtract_from_count(text)),
                'format': '^!subtract_count\s+\S+$',
                'help': '!subtract_count count_name'
            }
        }

    def list_counts(self):
        all_counts = ', '.join([count['name'] for count in counts.list_counts()])
        if all_counts:
            self.chat('Counts: {}'.format(all_counts))

    def chat_count_output(self, count_name, count):
        if count is not None:
            self.chat('{}: {}'.format(count_name, count))

    def copy_count(self, text):
        count1, count2 = tuple(text.split())
        try:
            self.chat_count_output(count2, counts.copy_count(count1, count2))
        except Exception:
            self.chat('{} doesn\'t exist.'.format(count1))

    def reset_count(self, text):
        for count_name in text.split():
            self.chat_count_output(count_name, counts.reset_count(count_name))

    def remove_count_output(self, count_name):
        counts.remove_count(count_name)
        self.chat('{} removed'.format(count_name))

    # Lists

    def set_list_commands(self):
        self.list_commands = {
            'list_lists': {
                'badge': Badges.CHAT,
                'callback': lambda text, user, badges: self.list_lists(),
                'format': '^!list_lists$',
                'help': '!list_lists'
            },
            'get_list_item': {
                'badge': Badges.CHAT,
                'callback': lambda text, user, badges: self.get_list_item(text),
                'format': '^!get_list_item\s+\S+(\s+\d+)?$',
                'help': '!get_list_item list_name [index]'
            },
            'get_list_size': {
                'badge': Badges.CHAT,
                'callback': lambda text, user, badges: self.get_list_size(text),
                'format': '^!get_list_size\s+\S+$',
                'help': '!get_list_size list_name'
            },
            'add_list_item': {
                'badge': Badges.VIP,
                'callback': lambda text, user, badges: self.add_list_item(text[:text.index(' ')],
                                                                          text[text.index(' ')+1:]),
                'format': '^!add_list_item\s+\S+\s+.+$',
                'help': '!add_list_item list_name item to include in list'
            },
            'remove_list_item': {
                'badge': Badges.VIP,
                'callback': lambda text, user, badges: self.remove_list_item(text.split()[0], text.split()[1]),
                'format': '^!remove_list_item\s+\S+\s+\d+$',
                'help': '!remove_list_item list_name index'
            },
            'remove_list': {
                'badge': Badges.BROADCASTER,
                'callback': lambda text, user, badges: self.remove_list(text),
                'format': '^!remove_list\s+\S+$',
                'help': '!remove_list list_name'
            }
        }

    def list_lists(self):
        all_lists = ', '.join([count['name'] for count in lists.list_lists()])
        if all_lists:
            self.chat('Lists: {}'.format(all_lists))

    def get_list_item(self, text):
        argv = text.split()
        list_name = argv[0]
        index = int(argv[1])-1 if len(argv) > 1 else None
        item, item_index = lists.get_list_item(list_name, index=index)
        if item:
            self.output_list_item(item_index+1, item)

    def get_list_size(self, list_name):
        size = lists.get_list_size(list_name)
        if size is not None:
            self.chat('{} size: {}'.format(list_name, size))

    def add_list_item(self, list_name, item):
        index = len(lists.get_list(list_name)) + 1
        lists.add_to_list(list_name, [item])
        self.output_list_item(index, item)

    def remove_list_item(self, list_name, index):
        item = lists.remove_from_list(list_name, int(index)-1)
        if item:
            self.chat('Removed {}. {}'.format(index, item))

    def remove_list(self, list_name):
        lists.remove_list(list_name)
        self.chat('Removed list {}'.format(list_name))

    def output_list_item(self, index, item):
        if item:
            self.chat('{}. {}'.format(index, item))

    # Alerts

    def set_alert_commands(self):
        self.alert_commands = {
            'alert': {
                'badge': Badges.VIP,
                'callback': lambda text, user, badges: self.alert_api(user, badges, text),
                'format': '^!alert\s+\S+$',
                'help': '!alert alert_name'
            },
            'group_alert': {
                'badge': Badges.VIP,
                'callback': lambda text, user, badges: self.group_alert_api(user, badges, text),
                'format': '^!group_alert\s+\S+$',
                'help': '!group_alert group_alert_name'
            },
            'ban': {
                'badge': Badges.VIP,
                'callback': lambda text, user, badges: self.ban(text),
                'format': '^!ban\s+\S+$',
                'help': '!ban chatter'
            },
            'unban': {
                'badge': Badges.VIP,
                'callback': lambda text, user, badges: self.unban(text),
                'format': '^!unban\s+\S+$',
                'help': '!unban banned_chatter'
            }
        }

    def alert_api(self, user, badges, alert):
        if user in lists.get_list('banned_users'):
            return
        elif not self._badge_check(badges, Badges.VIP) and self.spamming(user):
            self.chat('No spamming {}. Wait another {} seconds.'.format(user, self.timeout))
            return

        try:
            alerts.alert(name=alert, chat=True)
        except Exception as e:
            pass

    def group_alert_api(self, user, badges, group_alert):
        if user in lists.get_list('banned_users'):
            return
        elif not self._badge_check(badges, Badges.VIP) and self.spamming(user):
            self.chat('No spamming {}. Wait another {} seconds.'.format(user, self.timeout))
            return

        try:
            alerts.group_alert(group_name=group_alert, chat=True)
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

    # Lights

    def set_light_commands(self):
        self.light_commands = {
            'get_lights': {
                'badge': Badges.CHAT,
                'callback': lambda text, user, badges: self.get_lights(),
                'format': '^!get_lights$',
                'help': '!get_lights'
            },
            'set_lights': {
                'badge': Badges.CHAT,
                'callback': lambda text, user, badges: self.set_lights(text),
                'format': '^!set_lights\s+\S+(\s+\d+)?$',
                'help': '!set_lights color/hex [brightness 0-10]'
            },
            'lock_lights': {
                'badge': Badges.ADMINISTRATOR,
                'callback': lambda text, user, badges: self.lock_lights(),
                'format': '^!lock_lights$',
                'help': '!lock_lights'
            },
            'unlock_lights': {
                'badge': Badges.ADMINISTRATOR,
                'callback': lambda text, user, badges: self.unlock_lights(),
                'format': '^!unlock_lights$',
                'help': '!unlock_lights'
            }
        }

    def get_lights(self):
        self.chat('Light options are: {}'.format(list(lights.BASIC_COLORS.keys())))

    def set_lights(self, text):
        values = text.split()
        color = values[0]
        brightness = values[2] if len(values) > 1 else None
        lights.change_lights_static(color, brightness)
        brightness_ind = '' if not brightness else ' (brightness: {})'.format(brightness)
        resp = 'Lights set to {}{}'.format(color, brightness_ind)
        self.chat(resp)

    def lock_lights(self):
        lights.lock()
        self.chat('Lights locked')

    def unlock_lights(self):
        lights.unlock()
        self.chat('Lights unlocked')

    # Extra commands

    def random(self, text):
        options = text.split()
        choice = random.choice(options)
        self.chat('Random choice: {}'.format(choice))

    def spongebob(self, text):
        spongebob_message = ''.join([k.upper() if index % 2 else k.lower() for index, k in enumerate(text)])
        spongebob_url = 'https://dannypage.github.io/assets/images/mocking-spongebob.jpg'
        self.chat('{} - {}'.format(spongebob_message, spongebob_url))

    def help(self, badges):
        lyrics = [
            'Help! I need somebody!',
            'Help! Not just anybody!',
            'Help! You know I need someone!',
            'HEELLPP!',
            'Alright here are your commands'
        ]
        for lyric in lyrics:
            time.sleep(3)
            self.chat(lyric)
        self.display_commands(self.main_commands, None, badges)

    def taco(self, from_user, to_user):
        self.chat('/me {} aggressively hurls a :taco: at {}'.format(from_user, to_user))
        taco_user_count = '{}_tacos'.format(to_user)
        self.chat_count_output(taco_user_count, counts.add_to_count(taco_user_count)),

    def shoutout(self, text):
        self.chat('Hey I know {}! You should check\'em out and drop a follow '
                  '- https://www.twitch.tv/{}'.format(text, text))

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
            exit()


def setup_chatbot(bot_name, client_id, chat_token, channel, timeout=15):
    if 'chatbot' in g:
        chatbot = g['chatbot']['object']
        if chatbot.running():
            raise Exception('Chatbot already setup')
        else:
            g['chatbot']['thread'].join()
            del g['chatbot']

    chatbot_id = uuid.uuid4()
    try:
        chatbot = TwitchBot(chatbot_id=chatbot_id, bot_name=bot_name, client_id=client_id, token=chat_token,
                            channel=channel, timeout=timeout, app=app)
        chatbot.connect_to_channel()
        chatbot_thread = threading.Thread(target=start_chatbot_with_app, args=(app, chatbot,))
        chatbot_thread.start()
    except Exception as e:
        logger.exception(e)
        raise Exception('Unable to start chatbot with the provided settings')

    g['chatbot'] = {
        'object': chatbot,
        'thread': chatbot_thread
    }
    return chatbot_id


def verify_chatbot_id(chatbot_id):
    chatbot = g.get('chatbot', None)
    try:
        chatbot_id = uuid.UUID(chatbot_id)
        if chatbot and chatbot['object'].chatbot_id == chatbot_id:
            return chatbot['object']
    except Exception:
        pass
    raise Exception('Chatbot ID not found')


def main():
    if len(sys.argv) != 6:
        print("Usage: twitchbot <username> <client id> <token> <channel>")
        sys.exit(1)

    username = sys.argv[1]
    client_id = sys.argv[2]
    token = sys.argv[3]
    channel = sys.argv[4]

    bot = TwitchBot(username, client_id, token, channel)
    bot.connect_to_channel()
    bot.start()


if __name__ == "__main__":
    main()
