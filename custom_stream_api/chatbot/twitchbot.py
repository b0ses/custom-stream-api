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

from custom_stream_api.alerts import alerts
from custom_stream_api.shared import app, g


class TwitchBot(irc.bot.SingleServerIRCBot):
    def __init__(self, chatbot_id, bot_name, client_id, token, channel, timeout=30):
        self.chatbot_id = chatbot_id
        self.client_id = client_id
        self.token = token
        self.channel = '#' + channel
        self.timeouts = {}
        self.banned = set()
        self.timeout = timeout  # in seconds
        self.admin_roles = ['mod', 'admin']

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

        self.chat_reactions = {}
        self.chat_commands = {
            'alert': {
                'badges': ['moderator', 'broadcaster'],
                'callback': self.alert_api
            },
            'group_alert': {
                'badges': ['moderator', 'broadcaster'],
                'callback': self.group_alert_api
            },
            'chat_reactions': {
                'badges': [],
                'callback': self.get_chat_reactions
            },
            'ban': {
                'badges': ['moderator', 'broadcaster'],
                'callback': self.ban
            },
            'unban': {
                'badges': ['moderator', 'broadcaster'],
                'callback': self.unban
            },
            'spongebob': {
                'badges': ['moderator', 'broadcaster'],
                'callback': self.spongebob
            },
            'add_chat_reaction': {
                'badges': ['moderator', 'broadcaster'],
                'callback': self.add_chat_reaction
            },
            'remove_chat_reaction': {
                'badges': ['moderator', 'broadcaster'],
                'callback': self.remove_chat_reaction
            },
            'id': {
                'badges': ['moderator', 'broadcaster'],
                'callback': self.chat,
                'input': self.chatbot_id
            },

        }
        for chat_reaction, alert_name in self.chat_reactions.items():
            self.chat_commands[chat_reaction] = {
                'badges': [],
                'callback': self.alert_api,
                'input': alert_name
            }

    def on_welcome(self, c, e):
        print('Joining ' + self.channel)

        # You must request specific capabilities before you can use them
        c.cap('REQ', ':twitch.tv/membership')
        c.cap('REQ', ':twitch.tv/tags')
        c.cap('REQ', ':twitch.tv/commands')
        c.join(self.channel)

    def on_pubmsg(self, c, e):

        # If a chat message starts with an exclamation point, try to run it as a command
        tags = {tag['key']: tag['value'] for tag in e.tags}
        user = tags['display-name']
        badges = [badge.split('/')[0] for badge in tags['badges'].split(',')]
        cmd = e.arguments[0]
        if cmd[:1] == '!':
            print('{} commanded: {}'.format(user, cmd))
            self.do_command(e, cmd, user, badges)
        return

    def do_command(self, e, cmd, user, badges):
        argv = cmd.split(' ')
        command_name = argv[0][1:]
        command_input = ' '.join(argv[1:])

        command = self.chat_commands.get(command_name, None)
        if not command:
            return

        if command['badges'] and not (list(set(badges) & set(command['badges']))):
            self.chat('/me Nice try {}.'.format(user))
            return

        input = command['input'] if command.get('input') else command_input
        command['callback'](user, badges, input)

    def spamming(self, user):
        spamming = (user in self.timeouts and ((time.time() - self.timeouts[user]) < self.timeout))
        self.timeouts[user] = time.time()
        return spamming

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

    def get_chat_reactions(self, user, badges, input):
        if self.chat_reactions:
            clean_chat_reactions = str(list(self.chat_reactions.keys()))[1:-1].replace('\'', '')
            msg = 'Chat reations include: {}'.format(clean_chat_reactions)
        else:
            msg = 'No chat reactions available'
        self.chat(msg)

    def add_chat_reaction(self, user, badges, input):
        chat_reaction_name = input.split()[0]
        chat_reaction_alert = input.split()[1]
        self.chat_reactions[chat_reaction_name] = chat_reaction_alert
        self.chat_commands[chat_reaction_name] = {
            'badges': [],
            'callback': self.alert_api,
            'input': chat_reaction_alert
        }

    def remove_chat_reaction(self, user, badges, input):
        chat_reaction_name = input.split()[0]
        del self.chat_reactions[chat_reaction_name]
        del self.chat_commands[chat_reaction_name]

    def ban(self, user, badges, input):
        self.banned.add(input)
        self.chat('/me Banned {}'.format(input))

    def unban(self, user, badges, input):
        self.banned.discard(input)
        self.chat('/me Unbanned {}'.format(input))

    def spongebob(self, user, badges, input):
        spongebob_message = ''.join([k.upper() if index % 2 else k.lower() for index, k in enumerate(input)])
        spongebob_url = 'https://dannypage.github.io/assets/images/mocking-spongebob.jpg'
        self.chat('/me {} - {}'.format(spongebob_message, spongebob_url))

    def chat(self, message):
        c = self.connection
        c.privmsg(self.channel, message)


def start_chatbot_with_app(app, chatbot):
    with app.app_context():
        try:
            chatbot.start()
        except OSError as e:
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
    except Exception as e:
        print(traceback.print_exc())
        raise Exception('Unable to start chatbot with the provided settings.')

    g['chatbot'] = {
        'bot': chatbot,
        'id': chatbot_id
    }
    return chatbot_id


def stop_chatbot(chatbot_id):
    chatbot = g.get('chatbot', None)
    if chatbot and chatbot['id'] == uuid.UUID(chatbot_id):
        chatbot['bot'].disconnect()
        del g['chatbot']
    else:
        print(traceback.print_exc())
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
    bot.start()


if __name__ == "__main__":
    main()
