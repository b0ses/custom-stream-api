DEBUG = True

# Where you want the server to be hosted, change if you want this to work remotely
# Note: the Stream Overlay and Dashboard need to match this in order for all of this to work!
HOST = '127.0.0.1'
PORT = 5000
DASHBOARD_PORT = 8080
OVERLAY_PORT = None

# Just fill these in with whatever. Adds security to your server.
SECRET = ''

# Twitch Login
LOGIN = False
CLIENT_ID = ''
CLIENT_SECRET = ''
REDIRECT_URI = ''

# Webhooks
WEBHOOK_SECRET = ''
CHAT_FOLLOWS = False
CHAT_STREAM_CHANGES = False

# Chatbot Settings
TIMEOUT = 15  # seconds between spamming sounds
