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
TWITCH_CLIENT_ID = ''
TWITCH_CLIENT_SECRET = ''
TWITCH_REDIRECT_URI = ''

# Chatbot Settings
TIMEOUT = 15  # seconds between spamming sounds

# Hue Lights Settings
LIGHTS_LOCAL = True
LIGHTS_LOCAL_IP = ''
LIGHTS_LOCAL_USER = ''

HUE_APP_NAME = ''
HUE_CLIENT_ID = ''
HUE_CLIENT_SECRET = ''
HUE_REDIRECT_URI = ''
HUE_GROUP_NUMBER = 1
