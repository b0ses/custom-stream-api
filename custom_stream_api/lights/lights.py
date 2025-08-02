"""Wrapper for the Hue Lights API"""

import requests
import logging
import json
import math
import re

from custom_stream_api import settings
from custom_stream_api.shared import g

logger = logging.getLogger(__name__)

BASIC_COLORS = {
    "red": "#FF0000",
    "orange": "#FFA500",
    "yellow": "#FFFF00",
    "green": "#00FF00",
    "blue": "#0000FF",
    "indigo": "#4B0082",
    "violet": "#7F00FF",
    "white": "#FFFFFF",
    "black": "#000000",
    "grey": "#808080",
    "pink": "#FFC0CB",
    "purple": "#800080",
    "brown": "#964B00",
    "turquoise": "#40E0D0",
    "magenta": "#FF00FF",
    "rainbow": "colorloop",
}


def request_light_api(url, method="get", data=None):
    if g.get("lights_locked") is True:
        raise Exception("lights are currently locked")
    if settings.LIGHTS_LOCAL:
        headers = {}
        domain = "http://{}/api".format(settings.LIGHTS_LOCAL_IP)
        user = settings.LIGHTS_LOCAL_USER
    else:
        headers = {"Authorization": "Bearer {}".format(g.get("hue_access_token"))}
        domain = "https://api.meethue.com/bridge"
        user = g["hue_username"]
    return requests.request(method, "{}/{}/{}".format(domain, user, url), headers=headers, json=data)


def change_lights_hue(on=True, saturation=0, brightness=254, hue=0, effect="none", xy=[]):
    """
    TODO
        'alert':
            'lselect' -> blinking for 15s
            'select' -> blink for a second (good for soundboard alerts?)
    """
    data = {"on": on, "sat": saturation, "bri": brightness, "hue": hue, "effect": effect, "xy": xy}
    resp = request_light_api("groups/{}/action".format(settings.HUE_GROUP_NUMBER), method="put", data=data)
    response_dict = json.loads(resp.text)[0]
    if response_dict.get("error"):
        raise Exception(str(response_dict["error"]["description"]))


def change_lights_static(color=None, brightness=None):
    effect = "none"

    if re.search(r"^#(?:[0-9a-fA-F]{3}){1,2}$", color):
        hex = color
    elif color in BASIC_COLORS:
        hex = BASIC_COLORS[color]
        if color == "rainbow":
            effect = hex
            # dummy hex to save on code, will be ignored with the effect
            hex = "#FFFFFF"
    else:
        raise ValueError(
            "Invalid color, must be a hex or simple color ({}): {}".format(list(BASIC_COLORS.keys()), color)
        )

    rgb = calulate_rgb_from_hex(hex)
    if rgb == (0, 0, 0) or brightness == 0:
        on = False
        xy = [0, 0]
        brightness = 0
    else:
        on = True
        xy = calculate_xy_from_rgb(rgb[0], rgb[1], rgb[2])
        # brightness overrides hex brightness
        if brightness is not None:
            if brightness not in range(0, 11):
                raise ValueError("Invalid brightness. Must be 0-10")
            brightness = 255 * brightness // 10
        else:
            brightness = calculate_brightness_from_rgb(rgb[0], rgb[1], rgb[2])

    data = {"on": on, "xy": xy, "bri": brightness, "effect": effect}
    resp = request_light_api("groups/{}/action".format(settings.HUE_GROUP_NUMBER), method="put", data=data)
    response_dict = json.loads(resp.text)[0]
    if response_dict.get("error"):
        raise Exception(str(response_dict["error"]["description"]))


def calulate_rgb_from_hex(hex):
    hex = hex.lstrip("#")
    return tuple(int(hex[i : i + 2], 16) for i in (0, 2, 4))


def calculate_brightness_from_rgb(red, green, blue):
    return int((0.2126 * red) + (0.7152 * green) + (0.0722 * blue))


def calculate_xy_from_rgb(red, green, blue):
    if red > 0.04045:
        red = math.pow((red + 0.055) / (1.0 + 0.055), 2.4)
    else:
        red = red / 12.92

    if green > 0.04045:
        green = math.pow((green + 0.055) / (1.0 + 0.055), 2.4)
    else:
        green = green / 12.92

    if blue > 0.04045:
        blue = math.pow((blue + 0.055) / (1.0 + 0.055), 2.4)
    else:
        blue = blue / 12.92

    big_X = red * 0.664511 + green * 0.154324 + blue * 0.162028
    big_Y = red * 0.283881 + green * 0.668433 + blue * 0.047685
    big_Z = red * 0.000088 + green * 0.072310 + blue * 0.986039

    x = big_X / (big_X + big_Y + big_Z)
    y = big_Y / (big_X + big_Y + big_Z)
    return [x, y]


def lock():
    g["lights_locked"] = True


def unlock():
    g["lights_locked"] = False
