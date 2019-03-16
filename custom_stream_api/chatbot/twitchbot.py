'''
Initial template from twitchdev/chat-samples
'''

import sys
import irc.bot
import requests
import time
import threading
import uuid
import logging
import random
from enum import Enum

from custom_stream_api.alerts import alerts
from custom_stream_api.shared import app, g, db
from custom_stream_api.chatbot.models import Alias, List, ListItem, Count

logger = logging.getLogger()


class Badges(Enum):
    CHAT = 'chat'
    BITS = 'bits'
    BITS_CHARITY = 'bits-charity'
    PREMIUM = 'premium'
    VERIFIED = 'verified'
    BOT = 'bot'
    PARTNER = 'partner'
    FFZ_SUPPORTER = 'ffz_supporter'
    SUBSCRIBER = 'subscriber'
    VIP = 'vip'
    MODERATOR = 'moderator'
    GLOBAL_MOD = 'global_mod'
    BROADCASTER = 'broadcaster'
    STAFF = 'staff'
    ADMIN = 'admin'


class TwitchBot(irc.bot.SingleServerIRCBot):
    def __init__(self, chatbot_id, bot_name, client_id, token, channel, timeout=30):
        self.chatbot_id = chatbot_id
        self.client_id = client_id
        self.token = token
        self.channel = '#' + channel

        self.badges = [Badges.CHAT, Badges.BITS, Badges.BITS_CHARITY, Badges.PREMIUM, Badges.VERIFIED, Badges.BOT,
                       Badges.FFZ_SUPPORTER, Badges.PARTNER, Badges.SUBSCRIBER, Badges.VIP, Badges.MODERATOR,
                       Badges.GLOBAL_MOD, Badges.BROADCASTER, Badges.STAFF, Badges.ADMIN]

        self.timeout = timeout  # in seconds
        self.timeouts = {}

        # Get the channel id, we will need this for v5 API calls
        url = 'https://api.twitch.tv/kraken/users?login=' + channel
        headers = {'Client-ID': client_id, 'Accept': 'application/vnd.twitchtv.v5+json'}
        r = requests.get(url, headers=headers).json()
        try:
            self.channel_id = r['users'][0]['_id']
        except KeyError:
            raise Exception('Unable to connect with the provided credentials.')

        # Create IRC bot connection
        server = 'irc.chat.twitch.tv'
        port = 6667
        logger.info('Connecting to ' + server + ' on port ' + str(port) + '...')
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port, 'oauth:' + token)], bot_name, bot_name)

        self.update_commands()
        self.update_banned()

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

    def on_pubmsg(self, connection, event):
        # If a chat message starts with an exclamation point, try to run it as a command
        tags = {tag['key']: tag['value'] for tag in event.tags}
        user = tags['display-name']
        badges = self.get_user_badges(tags)
        command = event.arguments[0]
        if command[:1] == '!':
            logger.info('{} commanded: {}'.format(user, command))
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

    def get_max_badge(self, badges):
        max_badge = Badges.CHAT
        if badges:
            max_badge = sorted(badges, key=lambda badge: self.badges.index(badge))[-1]
        return max_badge

    def do_command(self, command, user, badges):
        argv = command.split(' ')
        command_name = argv[0][1:]
        command_input = ' '.join(argv[1:])

        found_command = self.commands.get(command_name, None)
        if not found_command:
            return

        if self.badges.index(self.get_max_badge(badges)) < self.badges.index(found_command['badge']):
            self.chat('/me Nice try {}.'.format(user))
            return

        expected_input = found_command['input'] if found_command.get('input') else command_input
        found_command['callback'](user=user, badges=badges, input=expected_input)

    def update_commands(self):
        self.commands = {
            'id': {
                'badge': Badges.MODERATOR,
                'callback': self.get_chatbot_id
            },
            'get_commands': {
                'badge': Badges.CHAT,
                'callback': self.get_commands
            },
            'alert': {
                'badge': Badges.MODERATOR,
                'callback': self.alert_api
            },
            'group_alert': {
                'badge': Badges.MODERATOR,
                'callback': self.group_alert_api
            },
            'get_count': {
                'badge': Badges.MODERATOR,
                'callback': self.set_count
            },
            'set_count': {
                'badge': Badges.MODERATOR,
                'callback': self.set_count
            },
            'add_count': {
                'badge': Badges.MODERATOR,
                'callback': self.add_count
            },
            'substract_count': {
                'badge': Badges.MODERATOR,
                'callback': self.subtract_count
            },
            'add_list_item': {
                'badge': Badges.MODERATOR,
                'callback': self.append_to_list
            },
            'remove_list_item': {
                'badge': Badges.MODERATOR,
                'callback': self.remove_from_list
            },
            'display_list_item': {
                'badge': Badges.MODERATOR,
                'callback': self.display_list_item
            },
            'ban': {
                'badge': Badges.MODERATOR,
                'callback': self.ban
            },
            'unban': {
                'badge': Badges.MODERATOR,
                'callback': self.unban
            },
            'spongebob': {
                'badge': Badges.MODERATOR,
                'callback': self.spongebob
            }
        }
        for alias in self.list_aliases():
            self.commands[alias.alias] = {
                'badge': self.get_badge(alias.badge),
                'callback': self.redirect_alias,
                'input': alias.command
            }

    def get_badge(self, badge_string):
        badge_objects = list(filter(lambda badge: badge.value == badge_string, list(Badges)))
        if badge_objects:
            return badge_objects[0]
        else:
            logger.warning('Possible new badge: {}'.format(badge_string))

    def get_commands(self, user, badges, input):
        if not input:
            badge = self.get_max_badge(badges)
        else:
            badge = self.get_badge(input)
        badge_index = self.badges.index(badge) if badge else -1
        commands = [command for command, command_dict in self.commands.items()
                    if badge_index >= self.badges.index(command_dict['badge'])]

        if commands:
            clean_reactions = str(commands)[1:-1].replace('\'', '')
            msg = 'Commands include: {}'.format(clean_reactions)
        else:
            msg = 'No commands available'
        self.chat(msg)

    # Chatbot ID

    def get_chatbot_id(self, user=None, badges=None, input=None):
        self.chat('Chatbot ID - {}'.format(self.chatbot_id))

    # Alises

    def list_aliases(self):
        return list(db.session.query(Alias).order_by(Alias.command.asc()).all())

    def import_aliases(self, aliases):
        for alias_dict in aliases:
            self.add_alias(**alias_dict, save=False)
        db.session.commit()

    def redirect_alias(self, user, badges, input):
        logger.info('redirect', input, user, badges)
        self.do_command(input, user, badges)

    def add_alias(self, alias, command, badge, save=True):
        found_alias = db.session.query(Alias).filter_by(alias=alias).one_or_none()
        if found_alias:
            found_alias.command = command
            found_alias.badge = badge
        else:
            if badge not in [a_badge.value for a_badge in Badges]:
                raise Exception('Badge \'{}\' not available.'.format(badge))
            new_alias = Alias(alias=alias, command=command, badge=badge)
            db.session.add(new_alias)
        if save:
            db.session.commit()
        self.update_commands()
        return alias

    def remove_alias(self, alias):
        found_alias = db.session.query(Alias).filter_by(alias=alias)
        if found_alias.count():
            found_alias.delete()
            db.session.commit()
            self.update_commands()
            return alias

    # Counts

    def list_counts(self):
        return list(db.session.query(Count).all())

    def import_counts(self, counts):
        for count_dict in counts:
            self.set_count(count_dict['name'], count_dict['count'], save=False)
        db.session.commit()

    def add_count(self, name, user=None, badges=None, input=None):
        count_obj = db.session.query(Count).filter(Count.name == name).one_or_none()
        if not count_obj:
            count_obj = Count(name=name, count=0)
        count_obj.count += 1
        db.session.commit()
        self.chat('/me {}: {}'.format(name, count_obj.count))
        return count_obj.count

    def subtract_count(self, name, user=None, badges=None, input=None):
        count_obj = db.session.query(Count).filter(Count.name == name).one_or_none()
        if not count_obj:
            count_obj = Count(name=name, count=0)
        count_obj.count -= 1
        db.session.commit()
        self.chat('/me {}: {}'.format(name, count_obj.count))
        return count_obj.count

    def get_count(self, name, user=None, badges=None, input=None):
        count_obj = db.session.query(Count).filter(Count.name == name).one_or_none()
        if not count_obj:
            self.chat('/me Count {} doesn\'t exist'.format(name))
            return
        self.chat('/me {}: {}'.format(name, count_obj.count))
        return count_obj.count

    def set_count(self, name, count, save=True, user=None, badges=None, input=None):
        count_obj = db.session.query(Count).filter(Count.name == name).one_or_none()
        if not count_obj:
            count_obj = Count(name=name, count=0)
        count_obj.count = count
        if save:
            db.session.commit()
        self.chat('/me {}: {}'.format(name, count_obj.count))
        return count_obj.count

    # Lists

    def list_lists(self, specific_list=None):
        list_query = db.session.query(List)
        if specific_list:
            list_query.filter(List.list_name == specific_list)
        return list(list_query.order_by(List.list_name.asc()))

    def import_lists(self, lists):
        for list_dict in lists:
            self.set_list(list_dict['list_name'], list_dict['items'], save=False)
        db.session.commit()

    def set_list(self, name, items, save=True):
        found_list = db.session.query(List).filter_by(list_name=name).one_or_none()
        if not found_list:
            found_list = List(name=name, current_index=0)
            db.session.add(found_list)
        else:
            for item in found_list.items:
                db.session.delete(item)
        if save:
            db.session.commit()
        return self.add_to_list(name, items, save=save)

    def add_to_list(self, name, items, save=True):
        new_items = []

        found_list = List.query.filter_by(name=name).one_or_none()
        if not found_list:
            group_alert = List(name=name)
            db.session.add(group_alert)

        index = ListItem.query.filter_by(list_name=name).count()
        for item in items:
            item_obj = db.session.query(ListItem).filter_by(item=item)
            if not item_obj.count():
                raise Exception('List not found: {}'.format(item))

            if not ListItem.query.filter_by(list_name=name, item=item).count():
                new_items.append(item)
                new_item = ListItem(list_name=name, item=item, index=index)
                db.session.add(new_item)
                index += 1
        if save:
            db.session.commit()
        return items

    def display_list_item(self, name, item_index=None):
        found_list = db.session.query(List).filter_by(list_name=name).one_or_none()
        if not found_list:
            self.chat('/me List {} doesn\'t exist'.format(name))
            return
        items = found_list.items
        if not item_index.isdigit():
            self.chat('/me Index {} must be number'.format(item_index))
            return
        elif item_index and item_index > len(items):
            self.chat('/me List {} doesn\'t have {} items'.format(name, item_index))
            return
        elif not item_index:
            item_index = random.choice(items)
        self.chat('{}. {}'.format(item_index, items[item_index].item))

    def remove_from_list(self, name, index):
        found_list_item = db.session.query(ListItem).filter_by(list_name=name, index=index).one_or_none()
        if not found_list_item:
            self.chat('/me List item not found: {}, {}'.format(name, index))

        db.session.delete(found_list_item)
        db.session.commit()

        return found_list_item

    def remove_list(self, list_name):
        found_list = db.session.query(List).filter_by(list_name=list_name)
        if found_list.count():
            found_list.delete()
            db.session.commit()
            return list_name

    # Custom Stream API

    def alert_api(self, user, badges, input):
        if user in self.banned:
            self.chat('/me Nice try {}.'.format(user))
            return
        elif self.spamming(user):
            self.chat('/me No spamming {}. Wait another {} seconds.'.format(user, self.timeout))
            return

        try:
            message = alerts.alert(name=input)
            self.chat('/me {}'.format(message))
        except Exception:
            pass

    def group_alert_api(self, user, badges, input):
        if user in self.banned:
            self.chat('/me Nice try {}.'.format(user))
            return
        elif self.spamming(user):
            self.chat('/me No spamming {}. Wait another {} seconds.'.format(user, self.timeout))
            return

        try:
            message = alerts.group_alert(group_name=input)
            self.chat('/me {}'.format(message))
        except Exception:
            pass

    # Banned Users

    def ban(self, user=None, badges=None, input=None):
        if input:
            banned_user = self.add_to_list('banned_users', input)
            self.chat('/me Banned {}'.format(input))
            return banned_user

    def unban(self, user=None, badges=None, input=None):
        if input:
            banned_users = self.list_lists('banned_users')
            self.set_list('banned_users', [user for user in banned_users if user.item != input])
            self.chat('/me Unbanned {}'.format(input))
            return input

    # Extra commands

    def spongebob(self, user, badges, input):
        spongebob_message = ''.join([k.upper() if index % 2 else k.lower() for index, k in enumerate(input)])
        spongebob_url = 'https://dannypage.github.io/assets/images/mocking-spongebob.jpg'
        self.chat('/me {} - {}'.format(spongebob_message, spongebob_url))

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
        chatbot_thread = threading.Thread(target=start_chatbot_with_app, args=(app, chatbot,))
        chatbot_thread.start()
    except Exception as e:
        logger.exception(e)
        raise Exception('Unable to start chatbot with the provided settings.')

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
    bot.start()


if __name__ == "__main__":
    main()
