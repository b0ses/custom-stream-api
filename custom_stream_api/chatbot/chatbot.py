"""
Service agnostic chatbot to work with the web app
"""

import logging
import time
import re
import random
from datetime import datetime, timedelta
from functools import partial

from custom_stream_api import settings
from custom_stream_api.shared import get_app
from custom_stream_api.chatbot.models import Badges, BADGE_LEVELS, BADGE_NAMES
from custom_stream_api.chatbot import aliases, timers
from custom_stream_api.counts import counts
from custom_stream_api.lists import lists
from custom_stream_api.alerts import alerts

# from custom_stream_api.lights import lights

logger = logging.getLogger(__name__)


class ChatBot:
    def __init__(self, queue, timeout=15):
        self.app = get_app()
        self.name = settings.BOT_NAME
        # driver reads from the queue for responses
        self.queue = queue

        self.badge_levels = BADGE_LEVELS

        self.timers = []
        self.timeout = timeout  # in seconds
        self.timeouts = {}

        self.commands = {}
        with self.app.flask_app.app_context():
            self.update_commands()

    def start(self):
        self.chat("Hey 👋")

    def _substitute_vars(self, message, user=None):
        # edit message to replace variables in braces {}
        for variable in re.findall("{(.*?)}", message):
            variable = variable.strip()

            # {user} -> username of the person saying it
            if variable == "user" and user:
                message = message.replace(f"{{{variable}}}", user)

            # if it's a count name, return the count
            # {count_name} -> [count number]
            found_count = counts.get_count(variable)
            if found_count is not None:
                message = message.replace(f"{{{variable}}}", str(found_count))
                continue

            # if it's a list, use the index
            # {list_name next} -> [next list entry]
            # {list_name random} -> [random list entry]
            # {list_name 2} -> [specific list entry]
            list_params = variable.split()
            if len(list_params) > 1:
                list_name = list_params[0]
                list_index = list_params[1]
                if list_name not in [list_dict["name"] for list_dict in lists.list_lists()]:
                    logger.info(f"List not found in variable: {list_name}")
                    continue

                found_item, index = lists.get_list_item(list_name=list_name, index=list_index)
                if found_item is not None:
                    message = message.replace(f"{{{variable}}}", found_item.item)
                    continue

        return message

    def chat(self, message, user=None):
        message = self._substitute_vars(message, user=user)
        self.queue.put(message)

    # PARSE MESSAGES
    def parse_message(self, user, message, badges):
        logger.info(f"{user} (badges:{badges}) messaged: {message}")

        if message[:1] == "!":
            try:
                with self.app.flask_app.app_context():
                    self.do_command(message, user, badges)
            except Exception as e:
                logger.exception(e)

    def get_badge(self, badge_string):
        badge_objects = list(filter(lambda badge: badge.value == badge_string, list(Badges)))
        if badge_objects:
            return badge_objects[0]
        else:
            logger.warning(f"Possible new badge: {badge_string}")

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
        argv = strip_text.split(" ")
        command_name = argv[0][1:]
        command_text = " ".join(argv[1:])

        # just check for aliases each time
        # allows for updating aliases on the fly without needing to redeploy
        self.set_aliases()
        self.commands.update(self.aliases)

        found_command = self.commands.get(command_name, None)
        if not found_command:
            self.chat(f"Unknown command: {command_name}")
            return

        if (not ignore_badges) and not self._badge_check(badges, found_command["badge"]):
            return

        if not re.match(found_command["format"], strip_text):
            self.chat(f"Format: {found_command['help']}")
            return

        found_command["callback"](command_text, user, badges)

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
        # self.set_light_commands()
        # self.commands.update(self.light_commands)
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
            "echo": {
                "badge": Badges.BROADCASTER,
                "format": r"^!echo\s+.*$",
                "help": "!echo message",
                "callback": lambda text, user, badges: self.chat(text, user=user),
            },
            "help": {
                "badge": Badges.CHAT,
                "format": r"^!help$",
                "help": "!help",
                "callback": lambda text, user, badges: self.help(badges),
            },
            "random": {
                "badge": Badges.VIP,
                "format": r"^!random(\s+\S+){2,}$",
                "help": "!random option1 option2 [option3 ...]",
                "callback": lambda text, user, badges: self.random(text),
            },
            "spongebob": {
                "badge": Badges.SUBSCRIBER,
                "format": r"^!spongebob\s+.+$",
                "help": "!spongebob message",
                "callback": lambda text, user, badges: self.spongebob(text),
            },
            "taco": {
                "badge": Badges.SUBSCRIBER,
                "format": r"^!taco\s+\S+$",
                "help": "!taco [to_user]",
                "callback": lambda text, user, badges: self.taco(user, text),
            },
        }

    def set_get_commands(self):
        self.get_commands = {
            "get_commands": {
                "badge": Badges.CHAT,
                "format": r"^!get_commands\s*({})?$".format("|".join(BADGE_NAMES)),
                "help": "!get_commands [{}]".format(" | ".join(sorted(BADGE_NAMES))),
                "callback": lambda text, user, badges: self.display_commands(self.main_commands, text, badges),
            },
            "get_count_commands": {
                "badge": self.get_min_badge([command["badge"] for command in self.count_commands.values()]),
                "format": r"^!get_count_commands\s*({})?$".format("|".join(BADGE_NAMES)),
                "help": "!get_count_commands [{}]".format(" | ".join(sorted(BADGE_NAMES))),
                "callback": lambda text, user, badges: self.display_commands(self.count_commands, text, badges),
            },
            "get_list_commands": {
                "badge": self.get_min_badge([command["badge"] for command in self.list_commands.values()]),
                "format": r"^!get_list_commands\s*({})?$".format("|".join(BADGE_NAMES)),
                "help": "!get_list_commands [{}]".format(" | ".join(sorted(BADGE_NAMES))),
                "callback": lambda text, user, badges: self.display_commands(self.list_commands, text, badges),
            },
            "get_alert_commands": {
                "badge": self.get_min_badge([command["badge"] for command in self.alert_commands.values()]),
                "format": r"^!get_alert_commands\s*({})?$".format("|".join(BADGE_NAMES)),
                "help": "!get_alert_commands [{}]".format(" | ".join(sorted(BADGE_NAMES))),
                "callback": lambda text, user, badges: self.display_commands(self.alert_commands, text, badges),
            },
            "get_timer_commands": {
                "badge": self.get_min_badge([command["badge"] for command in self.timer_commands.values()]),
                "format": r"^!get_timer_commands\s*({})?$".format("|".join(BADGE_NAMES)),
                "help": "!get_timer_commands [{}]".format(" | ".join(sorted(BADGE_NAMES))),
                "callback": lambda text, user, badges: self.display_commands(self.timer_commands, text, badges),
            },
            # 'get_light_commands': {
            #     'badge': self.get_min_badge([command['badge'] for command in self.light_commands.values()]),
            #     'format': r'^!get_light_commands\s*({})?$'.format('|'.join(BADGE_NAMES)),
            #     'help': '!get_light_commands [{}]'.format(' | '.join(sorted(BADGE_NAMES))),
            #     'callback': lambda text, user, badges: self.display_commands(self.light_commands, text, badges)
            # },
            "get_aliases": {
                "badge": self.get_min_badge([command["badge"] for command in self.aliases.values()]),
                "format": r"^!get_aliases\s*({})?$".format("|".join(BADGE_NAMES)),
                "help": "!get_aliases [{}]".format(" | ".join(sorted(BADGE_NAMES))),
                "callback": lambda text, user, badges: self.display_commands(self.aliases, text, badges),
            },
        }
        self.main_commands.update(self.get_commands)

    def display_commands(self, commands, badge_level, user_badges=None):
        if not badge_level:
            badge = self.get_max_badge(user_badges)
        else:
            badge = self.get_badge(badge_level)
        badge_index = self.badge_levels.index(badge) if badge else -1
        filtered_commands = sorted(
            [
                command
                for command, command_dict in commands.items()
                if badge_index >= self.badge_levels.index(command_dict["badge"])
            ]
        )

        if filtered_commands:
            clean_reactions = str(filtered_commands)[1:-1].replace("'", "")
            msg = "Commands include: {}".format(clean_reactions)
        else:
            msg = "No commands available"
        self.chat(msg)

    # Alises

    def set_aliases(self):
        self.aliases = {}
        for alias in aliases.list_aliases():
            strip_text = alias["command"].strip()
            argv = strip_text.split(" ")
            command_name = argv[0][1:]
            found_command = self.commands.get(command_name, None)
            if found_command is None:
                logger.info("not adding {}".format(alias["alias"]))
                continue

            alias_format = self._get_alias_format(found_command["format"], alias)
            if not alias_format:
                logger.info("not adding {} due to formatting".format(alias["alias"]))

            self.aliases[alias["alias"]] = {
                "badge": self.get_badge(alias["badge"]),
                "callback": partial(self.alias_redirect, strip_text),
                "format": alias_format,
                "help": self._get_alias_help(found_command["help"], alias),
            }

    def _get_alias_format(self, original_format, alias):
        match = None
        index = 1
        while not match and index < len(original_format):
            try:
                match = re.match("^{}$".format(original_format[1:index]), alias["command"])
            except Exception:
                match = None
            if not match:
                index += 1
        if not match:
            return
        return "^!{}{}$".format(alias["alias"], original_format[index:-1])

    def _get_alias_help(self, original_help, alias):
        num_of_spaces = len(alias["command"].strip().split()) - 1
        num_of_expected_spaces = len(original_help.split()) - 1
        rest_of_help = ""
        if num_of_spaces < num_of_expected_spaces:
            rest_of_help = " " + " ".join(original_help.split()[num_of_spaces + 1 :])
        return "!{}{}".format(alias["alias"], rest_of_help)

    def alias_redirect(self, command, text, user, badges):
        self.do_command(command + " " + text, user, badges, ignore_badges=True)

    # Timers
    def set_timer_commands(self):
        self.timer_commands = {
            "reminder": {
                "badge": Badges.VIP,
                "callback": lambda text, user, badges: self.remind(text),
                "format": r"^!reminder(\s+\S+)?\s+\d+\s+.+$",
                "help": "!reminder [alert_or_tag] minutes message",
            },
        }

    def remind(self, text):
        text_args = text.split()
        if text_args[0].isdigit():
            minutes = text_args[0]
            alert_or_tag = None
            message = " ".join(text_args[1:])
        else:
            alert_or_tag = text_args[0]
            minutes = text_args[1]
            message = " ".join(text_args[2:])

        try:
            alerts.tag_details(alert_or_tag)
            command = f"!tag {alert_or_tag} Reminder: {message}"
        except Exception:
            command = f"!alert {alert_or_tag} Reminder: {message}"

        # the reminders are only a one time deal. repeated reminders you can just set up in the database
        next_time = datetime.now() + timedelta(minutes=int(minutes))
        cron = f"{next_time.minute} {next_time.hour} {next_time.day} {next_time.month} *"
        timers.add_timer("twitch_chatbot", command, cron, repeat=False)

        self.chat('Setup reminder "{}" in {} minutes'.format(message, str(minutes)))

    # Counts

    def set_count_commands(self):
        self.count_commands = {
            "list_counts": {
                "badge": Badges.CHAT,
                "callback": lambda text, user, badges: self.list_counts(),
                "format": r"^!list_counts$",
                "help": "!list_counts",
            },
            "get_count": {
                "badge": Badges.CHAT,
                "callback": lambda text, user, badges: self.chat_count_output(text, counts.get_count(text)),
                "format": r"^!get_count\s+\S+$",
                "help": "!get_count count_name",
            },
            "set_count": {
                "badge": Badges.VIP,
                "callback": lambda text, user, badges: self.chat_count_output(
                    text.split()[0], counts.set_count(text.split()[0], text.split()[1])
                ),
                "format": r"^!set_count\s+\S+\s+\d+$",
                "help": "!set_count count_name number",
            },
            "copy_count": {
                "badge": Badges.VIP,
                "callback": lambda text, user, badges: self.copy_count(text),
                "format": r"^!copy_count\s+\S+\s+\S+$",
                "help": "!copy_count count_from count_to",
            },
            "reset_count": {
                "badge": Badges.VIP,
                "callback": lambda text, user, badges: self.reset_count(text),
                "format": r"^!reset_count(\s+\S+)+$",
                "help": "!reset_count count_name1 count_name2 ...",
            },
            "remove_count": {
                "badge": Badges.VIP,
                "callback": lambda text, user, badges: self.remove_count_output(text),
                "format": r"^!remove_count\s+\S+$",
                "help": "!remove_count count_name",
            },
            "add_count": {
                "badge": Badges.VIP,
                "callback": lambda text, user, badges: self.chat_count_output(text, counts.add_to_count(text)),
                "format": r"^!add_count\s+\S+$",
                "help": "!add_count count_name",
            },
            "subtract_count": {
                "badge": Badges.VIP,
                "callback": lambda text, user, badges: self.chat_count_output(text, counts.subtract_from_count(text)),
                "format": r"^!subtract_count\s+\S+$",
                "help": "!subtract_count count_name",
            },
        }

    def list_counts(self):
        all_counts = ", ".join([count["name"] for count in counts.list_counts()])
        if all_counts:
            self.chat("Counts: {}".format(all_counts))

    def chat_count_output(self, count_name, count):
        if count is not None:
            emoji_mapper = {
                '0': ':zero:',
                '1': ':one:',
                '2': ':two:',
                '3': ':three:',
                '4': ':four:',
                '5': ':five:',
                '6': ':six:',
                '7': ':seven:',
                '8': ':eight:',
                '9': ':nine:',
            }
            emoji_count = ' '.join([emoji_mapper[char] for char in str(count)])
            self.chat("{}: {}".format(count_name, emoji_count))

    def copy_count(self, text):
        count1, count2 = tuple(text.split())
        try:
            self.chat_count_output(count2, counts.copy_count(count1, count2))
        except Exception:
            self.chat("{} doesn't exist.".format(count1))

    def reset_count(self, text):
        for count_name in text.split():
            self.chat_count_output(count_name, counts.reset_count(count_name))

    def remove_count_output(self, count_name):
        counts.remove_count(count_name)
        self.chat("{} removed".format(count_name))

    # Lists

    def set_list_commands(self):
        self.list_commands = {
            "list_lists": {
                "badge": Badges.CHAT,
                "callback": lambda text, user, badges: self.list_lists(),
                "format": r"^!list_lists$",
                "help": "!list_lists",
            },
            "get_list_item": {
                "badge": Badges.CHAT,
                "callback": lambda text, user, badges: self.get_list_item(text),
                "format": r"^!get_list_item\s+\S+(\s+-?\d+|\s+next|\s+random)$",
                "help": "!get_list_item list_name [index]/next/random",
            },
            "get_list_size": {
                "badge": Badges.CHAT,
                "callback": lambda text, user, badges: self.get_list_size(text),
                "format": r"^!get_list_size\s+\S+$",
                "help": "!get_list_size list_name",
            },
            "add_list_item": {
                "badge": Badges.VIP,
                "callback": lambda text, user, badges: self.add_list_item(
                    text[: text.index(" ")], text[text.index(" ") + 1 :]
                ),
                "format": r"^!add_list_item\s+\S+\s+.+$",
                "help": "!add_list_item list_name item to include in list",
            },
            "remove_list_item": {
                "badge": Badges.VIP,
                "callback": lambda text, user, badges: self.remove_list_item(text.split()[0], text.split()[1]),
                "format": r"^!remove_list_item\s+\S+\s+\d+$",
                "help": "!remove_list_item list_name index",
            },
            "remove_list": {
                "badge": Badges.BROADCASTER,
                "callback": lambda text, user, badges: self.remove_list(text),
                "format": r"^!remove_list\s+\S+$",
                "help": "!remove_list list_name",
            },
        }

    def list_lists(self):
        all_lists = ", ".join([count["name"] for count in lists.list_lists()])
        if all_lists:
            self.chat("Lists: {}".format(all_lists))

    def get_list_item(self, text):
        argv = text.split()
        list_name = argv[0]
        index = argv[1]
        try:
            item, index = lists.get_list_item(list_name, index=index)
            self.output_list_item(index, item.item)
        except Exception as e:
            self.chat(str(e))

    def get_list_size(self, list_name):
        try:
            size = lists.get_list_size(list_name)
            self.chat("{} size: {}".format(list_name, size))
        except Exception as e:
            self.chat(str(e))

    def add_list_item(self, list_name, item):
        index = len(lists.get_list(list_name)) + 1
        lists.add_to_list(list_name, [item])
        self.output_list_item(index, item)

    def remove_list_item(self, list_name, index):
        try:
            item, index = lists.remove_from_list(list_name, int(index))
            self.chat("Removed {}. {}".format(index, item))
        except Exception as e:
            self.chat(str(e))

    def remove_list(self, list_name):
        lists.remove_list(list_name)
        self.chat("Removed list {}".format(list_name))

    def output_list_item(self, index, item):
        if item:
            self.chat("{}. {}".format(index, item))

    # Alerts

    def set_alert_commands(self):
        self.alert_commands = {
            "alert": {
                "badge": Badges.VIP,
                "callback": lambda text, user, badges: self.alert_api(user, badges, text),
                "format": r"^!alert\s+\S+.*$",
                "help": "!alert alert_name [display text]",
            },
            "tag": {
                "badge": Badges.VIP,
                "callback": lambda text, user, badges: self.tag_alert_api(user, badges, text),
                "format": r"^!tag\s+\S+.*$",
                "help": "!tag tag_name [display text]",
            },
            "ban": {
                "badge": Badges.VIP,
                "callback": lambda text, user, badges: self.ban(text),
                "format": r"^!ban\s+\S+$",
                "help": "!ban chatter",
            },
            "unban": {
                "badge": Badges.VIP,
                "callback": lambda text, user, badges: self.unban(text),
                "format": r"^!unban\s+\S+$",
                "help": "!unban banned_chatter",
            },
        }

    def alert_api(self, user, badges, text):
        if user in lists.get_list("banned_users"):
            return
        elif not self._badge_check(badges, Badges.VIP) and self.spamming(user):
            self.chat("No spamming {}. Wait another {} seconds.".format(user, self.timeout))
            return

        text_args = tuple(text.split())
        alert_name = text_args[0]
        display_text = " ".join(text_args[1:]) if len(text_args) > 1 else None

        try:
            alerts.alert(name=alert_name, chat=display_text)
        except Exception:
            pass

    def tag_alert_api(self, user, badges, text):
        if user in lists.get_list("banned_users"):
            return
        elif not self._badge_check(badges, Badges.VIP) and self.spamming(user):
            self.chat("No spamming {}. Wait another {} seconds.".format(user, self.timeout))
            return

        text_args = tuple(text.split())
        tag_name = text_args[0]
        display_text = " ".join(text_args[1:]) if len(text_args) > 1 else None

        try:
            alerts.tag_alert(name=tag_name, chat=display_text)
        except Exception:
            pass

    def ban(self, ban_user):
        if ban_user:
            lists.add_to_list("banned_users", [ban_user])
            self.chat("Banned {}".format(ban_user))
            return ban_user

    def unban(self, unban_user):
        if unban_user:
            banned_users = lists.get_list("banned_users")
            lists.set_list("banned_users", [user for user in banned_users if user != unban_user])
            self.chat("Unbanned {}".format(unban_user))
            return unban_user

    # Lights

    # def set_light_commands(self):
    #     self.light_commands = {
    #         'get_lights': {
    #             'badge': Badges.CHAT,
    #             'callback': lambda text, user, badges: self.get_lights(),
    #             'format': r'^!get_lights$',
    #             'help': '!get_lights'
    #         },
    #         'set_lights': {
    #             'badge': Badges.CHAT,
    #             'callback': lambda text, user, badges: self.set_lights(text),
    #             'format': r'^!set_lights\s+\S+(\s+\d+)?$',
    #             'help': '!set_lights color/hex [brightness 0-10]'
    #         },
    #         'lock_lights': {
    #             'badge': Badges.BROADCASTER,
    #             'callback': lambda text, user, badges: self.lock_lights(),
    #             'format': r'^!lock_lights$',
    #             'help': '!lock_lights'
    #         },
    #         'unlock_lights': {
    #             'badge': Badges.BROADCASTER,
    #             'callback': lambda text, user, badges: self.unlock_lights(),
    #             'format': r'^!unlock_lights$',
    #             'help': '!unlock_lights'
    #         }
    #     }
    #
    # def get_lights(self):
    #     self.chat('Light options are: {}'.format(list(lights.BASIC_COLORS.keys())))
    #
    # def set_lights(self, text):
    #     values = text.split()
    #     color = values[0]
    #     brightness = int(values[1]) if len(values) > 1 else None
    #     try:
    #         lights.change_lights_static(color, brightness)
    #         brightness_ind = '' if not brightness else ', brightness: {}'.format(brightness)
    #         self.chat('Lights set to {}{}'.format(color, brightness_ind))
    #     except Exception as e:
    #         self.chat(str(e))
    #
    # def lock_lights(self):
    #     lights.lock()
    #     self.chat('Lights locked')
    #
    # def unlock_lights(self):
    #     lights.unlock()
    #     self.chat('Lights unlocked')

    # Extra commands

    def random(self, text):
        options = text.split()
        choice = random.choice(options)
        self.chat("Random choice: {}".format(choice))

    def spongebob(self, text):
        spongebob_message = "".join([k.upper() if index % 2 else k.lower() for index, k in enumerate(text)])
        spongebob_url = "https://dannypage.github.io/assets/images/mocking-spongebob.jpg"
        self.chat("{} - {}".format(spongebob_message, spongebob_url))

    def help(self, badges):
        lyrics = [
            "Help! I need somebody!",
            "Help! Not just anybody!",
            "Help! You know I need someone!",
            "HEELLPP!",
            "Alright here are your commands",
        ]
        for lyric in lyrics:
            self.chat(lyric)
            time.sleep(3)
        self.display_commands(self.main_commands, None, badges)

    def taco(self, from_user, to_user):
        self.chat(f"/me {from_user} aggressively hurls a :taco: at {to_user}")
        taco_user_count = f"{to_user}_tacos"
        self.chat_count_output(taco_user_count, counts.add_to_count(taco_user_count)),

    # Helper commands

    def spamming(self, user):
        spamming = user in self.timeouts and ((time.time() - self.timeouts[user]) < self.timeout)
        self.timeouts[user] = time.time()
        return spamming
