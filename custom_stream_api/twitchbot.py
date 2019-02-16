'''
Initial template from twitchdev/chat-samples
'''

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
        # subscriber = tags['subscriber']
        user_type = tags['user-type']
        cmd = e.arguments[0]
        if cmd[:1] == '!':
            print('{} commanded: {}'.format(user, cmd))
            self.do_command(e, cmd, user, user_type)
        return

    def spamming(self, user):
        spamming = (user in self.timeouts and ((time.time() - self.timeouts[user]) < self.timeout))
        self.timeouts[user] = time.time()
        return spamming

    def do_command(self, e, cmd, user, user_type):
        argv = cmd.split(' ')
        action = argv[0][1:]

        if user in self.banned:
            self.chat('/me Nice try {}.'.format(user))
            return
        elif self.spamming(user):
            self.chat('/me No spamming {}. Wait another {} seconds.'.format(user, self.timeout))
            return

        chat_reactions = {}

        if action == 'alert':
            self.alert_api(' '.join(argv[1:]))
        elif action == 'group_alert':
            self.group_alert_api(' '.join((argv[1:])))
        elif action == 'chat_reactions':
            clean_chat_reactions = str(list(chat_reactions.keys()))[1:-1].replace('\'', '')
            self.chat('Chat reations include: {}'.format(clean_chat_reactions))
        elif action in chat_reactions:
            self.alert_api(chat_reactions[action])
        elif action == 'ban':
            self.banned.add(' '.join(argv[1:]))
        elif action == 'unban':
            self.banned.discard(' '.join(argv[1:]))

    def alert_api(self, name):
        message = alerts.alert(name=name)
        self.chat('/me {}'.format(message))

    def group_alert_api(self, name):
        message = alerts.group_alert(group_name=name)
        self.chat('/me {}'.format(message))

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
