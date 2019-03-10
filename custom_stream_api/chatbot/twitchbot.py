'''
Initial template from twitchdev/chat-samples
'''

import sys
import irc.bot
import requests
import time
import threading
import traceback
import uuid
from enum import Enum

from custom_stream_api.alerts import alerts
from custom_stream_api.shared import app, g, db
from custom_stream_api.chatbot.models import Alias


class Badges(Enum):
    CHAT = 'chat'
    SUBSCRIBER = 'subscriber'
    VIP = 'vip'
    MODERATOR = 'moderator'
    GLOBAL_MOD = 'global_mod'
    BROADCASTER = 'broadcaster'
    STAFF = 'staff'
    ADMIN = 'admin'
    PREMIUM = 'premium'


class TwitchBot(irc.bot.SingleServerIRCBot):
    def __init__(self, chatbot_id, bot_name, client_id, token, channel, timeout=30):
        self.chatbot_id = chatbot_id
        self.client_id = client_id
        self.token = token
        self.channel = '#' + channel

        self.badges = [Badges.CHAT, Badges.PREMIUM, Badges.SUBSCRIBER, Badges.VIP, Badges.MODERATOR, Badges.GLOBAL_MOD,
                       Badges.BROADCASTER, Badges.STAFF, Badges.ADMIN]

        self.timeout = timeout  # in seconds
        self.timeouts = {}
        self.banned = set()

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
        print('Connecting to ' + server + ' on port ' + str(port) + '...')
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port, 'oauth:' + token)], bot_name, bot_name)

        self.update_commands()

    def on_welcome(self, connection, event):
        print('Joining ' + self.channel)

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
        badges = [badge.split('/')[0] for badge in tags['badges'].split(',')]
        command = event.arguments[0]
        if command[:1] == '!':
            print('{} commanded: {}'.format(user, command))
            self.do_command(command, user, badges)

    def get_max_badge(self, badges):
        max_badge = Badges.CHAT
        if badges:
            badge_enums = [self.get_badge(badge) for badge in badges]
            max_badge = sorted(badge_enums, key=lambda badge: self.badges.index(badge))[-1]
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

        input = found_command['input'] if found_command.get('input') else command_input
        found_command['callback'](user, badges, input)

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
        return list(filter(lambda badge: badge.value == badge_string, list(Badges)))[0]

    def get_commands(self, user, badges, input):
        if not input:
            badge = self.get_max_badge(badges)
        else:
            badge = self.get_badge(input)
        badge_index = self.badges.index(badge)
        commands = [command for command, command_dict in self.commands.items()
                    if badge_index >= self.badges.index(command_dict['badge'])]

        if commands:
            clean_reactions = str(commands)[1:-1].replace('\'', '')
            msg = 'Commands include: {}'.format(clean_reactions)
        else:
            msg = 'No commands available'
        self.chat(msg)

    def list_aliases(self):
        return list(db.session.query(Alias).order_by(Alias.command.asc()).all())

    def redirect_alias(self, user, badges, input):
        print('redirect', input, user, badges)
        self.do_command(input, user, badges)

    def import_aliases(self, aliases):
        for alias_dict in aliases:
            self.add_alias(**alias_dict, save=False)
        db.session.commit()

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

    def get_chatbot_id(self, user, badges, input):
        self.chat('Chatbot ID - {}'.format(self.chatbot_id))

    def alert_api(self, user, badges, input):
        if user in self.banned:
            self.chat('/me Nice try {}.'.format(user))
            return
        elif self.spamming(user):
            self.chat('/me No spamming {}. Wait another {} seconds.'.format(user, self.timeout))
            return

        message = alerts.alert(name=input)
        self.chat('/me {}'.format(message))

    def group_alert_api(self, user, badges, input):
        if user in self.banned:
            self.chat('/me Nice try {}.'.format(user))
            return
        elif self.spamming(user):
            self.chat('/me No spamming {}. Wait another {} seconds.'.format(user, self.timeout))
            return

        message = alerts.group_alert(group_name=input)
        self.chat('/me {}'.format(message))

    def ban(self, user, badges, input):
        self.banned.add(input)
        self.chat('/me Banned {}'.format(input))

    def unban(self, user, badges, input):
        self.banned.discard(input)
        self.chat('/me Unbanned {}'.format(input))

    def spamming(self, user):
        spamming = (user in self.timeouts and ((time.time() - self.timeouts[user]) < self.timeout))
        self.timeouts[user] = time.time()
        return spamming

    def spongebob(self, user, badges, input):
        spongebob_message = ''.join([k.upper() if index % 2 else k.lower() for index, k in enumerate(input)])
        spongebob_url = 'https://dannypage.github.io/assets/images/mocking-spongebob.jpg'
        self.chat('/me {} - {}'.format(spongebob_message, spongebob_url))


def start_chatbot_with_app(app, chatbot):
    with app.app_context():
        try:
            chatbot.start()
        except OSError:
            print('Disconnected')


def setup_chatbot(bot_name, client_id, chat_token, channel, timeout=30):
    if 'chatbot' in g:
        raise Exception('Chatbot already setup')
    chatbot_id = uuid.uuid4()
    try:
        chatbot = TwitchBot(chatbot_id=chatbot_id, bot_name=bot_name, client_id=client_id, token=chat_token,
                            channel=channel, timeout=timeout)
        chatbot_thread = threading.Thread(target=start_chatbot_with_app, args=(app, chatbot,))
        chatbot_thread.start()
    except Exception:
        print(traceback.print_exc())
        raise Exception('Unable to start chatbot with the provided settings.')

    g['chatbot'] = chatbot
    return chatbot_id


def verify_chatbot_id(chatbot_id):
    chatbot = g.get('chatbot', None)
    if chatbot and chatbot.chatbot_id == uuid.UUID(chatbot_id):
        return chatbot
    else:
        print(traceback.print_exc())
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
