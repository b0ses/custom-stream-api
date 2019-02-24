'''
Initial template from twitchdev/chat-samples
'''

import random
import sys
import irc.bot
import requests
import time

from custom_stream_api.alerts import alerts


class TwitchBot(irc.bot.SingleServerIRCBot):
    def __init__(self, username, client_id, token, channel, timeout=30):
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
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port, 'oauth:' + token)], username, username)

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
                'callback': self.chat_reactions
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
            }
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

    def chat_reactions(self, user, badges, input):
        clean_chat_reactions = str(list(self.chat_reactions.keys()))[1:-1].replace('\'', '')
        self.chat('Chat reations include: {}'.format(clean_chat_reactions))

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
        spongebob_message = ' '.join(input)
        spongebob_message = "".join(random.choice([k.upper(), k]) for k in spongebob_message)
        spongebob_url = 'https://dannypage.github.io/assets/images/mocking-spongebob.jpg'
        self.chat('/me {} - {}'.format(spongebob_message, spongebob_url))

    def chat(self, message):
        c = self.connection
        c.privmsg(self.channel, message)


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
