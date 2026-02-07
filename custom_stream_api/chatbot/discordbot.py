import asyncio
import discord
import logging
import janus

from custom_stream_api.settings import DISCORD_TOKEN, DISCORD_CHANNEL

from custom_stream_api.chatbot.chatbot import ChatBot
from custom_stream_api.shared import run_async_in_thread

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.getLogger("discord.http").setLevel(logging.INFO)

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
chatbot_instance = None
discord_channel = None


@client.event
async def on_ready():
    global discord_channel

    for guild in client.guilds:
        for channel in guild.channels:
            if channel.name == DISCORD_CHANNEL:
                discord_channel = channel
                break

    print(f"We have logged in as {client.user}")
    chatbot_instance.start()


@client.event
async def on_message(message):
    # modify this to however your roles are in your discord
    badge_mapping = {"admin": "admin", "mod": "moderator", "vip": "vip"}
    user_badges = [badge_mapping.get(role.name, "chat") for role in message.author.roles]
    badges = [badge for badge in chatbot_instance.badge_levels if badge.value in user_badges]

    if message.author == client.user:
        return

    chatbot_instance.parse_message(message.author, message.content, badges)


async def run(client, chatbot_queue):
    loop = asyncio.get_running_loop()

    loop.create_task(client.start(DISCORD_TOKEN))

    # check for messages on the queue
    while True:
        message = await chatbot_queue.get()
        await discord_channel.send(message)
        chatbot_queue.task_done()


def run_discordbot_thread():
    global chatbot_instance

    discordbot_queue = janus.Queue()
    chatbot_instance = ChatBot(bot_type="discord", queue=discordbot_queue.sync_q)

    run_async_in_thread(run, client, discordbot_queue.async_q)

    return chatbot_instance
