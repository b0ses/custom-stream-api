import re
import random
from collections import OrderedDict
from sqlalchemy import func

from custom_stream_api.alerts.models import Alert, GroupAlert, GroupAlertAssociation
from custom_stream_api.counts import counts
from custom_stream_api.shared import db, socketio, get_chatbot

VALID_SOUNDS = ["wav", "mp3", "ogg"]
VALID_IMAGES = ["jpg", "png", "tif", "gif", "jpeg"]
URL_REGEX = r"^(http[s]?):\/?\/?([^:\/\s]+)((\/.+)*\/)(.+)\.({})$"
SOUND_REGEX = URL_REGEX.format("|".join(VALID_SOUNDS))
IMAGE_REXEX = URL_REGEX.format("|".join(VALID_IMAGES))
HEX_CODE_REGEX = "^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$"
VALID_EFFECTS = ["", "fade"]


# HELPERS


def validate_sound(sound=""):
    if sound:
        matches = re.findall(SOUND_REGEX, sound)
        if not matches:
            raise Exception("Invalid sound url: {}".format(sound))
        else:
            return matches[0][4]  # using the regex, this'll return the filename sans extension


def validate_effect(effect):
    effect = effect or ""
    if effect in VALID_EFFECTS:
        return effect
    else:
        raise Exception("Invalid effect: {}".format(effect))


def validate_duration(duration):
    if not str(duration).isdigit():
        raise Exception("Invalid duration: {}".format(duration))
    return int(duration)


def validate_image(image=""):
    if image:
        matches = re.findall(IMAGE_REXEX, image)
        if not matches:
            raise Exception("Invalid image url: {}".format(image))
        else:
            return matches[0][4]  # using the regex, this'll return the filename sans extension


def validate_color_hex(color_hex):
    if color_hex:
        matches = re.findall(HEX_CODE_REGEX, color_hex)
        if not matches:
            raise Exception("Invalid color hex: {}".format(color_hex))
        else:
            return color_hex


def validate_thumbnail(thumbnail):
    if thumbnail:
        if thumbnail[0] == "#":
            validate_color_hex(thumbnail)
        elif thumbnail[:4] == "http":
            validate_image(thumbnail)
        else:
            raise Exception("Invalid thumbnail: {}".format(thumbnail))
    return thumbnail


def generate_name(name="", text="", sound="", image=""):
    generated_name = name
    if not generated_name and text:
        generated_name = text
    elif not generated_name and sound:
        generated_name = validate_sound(sound)
    elif not generated_name and image:
        generated_name = validate_image(image)
    elif not generated_name:
        raise Exception("Can't generate blank alert name.")

    return generated_name.strip().lower().replace(" ", "_")


def apply_filters(model, sort_options, search_attr, sort="name", page=1, limit=None, search=None):
    if sort:
        sort_options.update({"-{}".format(sort_option): sort_value for sort_option, sort_value in sort_options.items()})
        if sort not in sort_options:
            raise ValueError("Invalid sort option: {}".format(sort))
        order_by = sort_options[sort].desc() if sort[0] == "-" else sort_options[sort].asc()

    list_query = db.session.query(model)
    if search and isinstance(search, str):
        list_query = list_query.filter(func.lower(getattr(model, search_attr)).contains(search.lower()))
    if sort:
        list_query = list_query.order_by(order_by)
    if page and limit:
        page = int(page)
        index_0_page = page - 1
        limit = int(limit)
        start = index_0_page * limit
        end = start + limit
        results = list_query.slice(start, end)
    elif limit:
        limit = int(limit)
        results = list_query.limit(limit)
    else:
        results = list_query.all()

    total = db.session.query(model).count()
    page_metadata = {"total": total, "page": page or 1, "limit": limit}

    return results, page_metadata


# ALERTS
def add_alert(name="", text="", sound="", duration=0, effect="", image="", thumbnail="", save=True):
    generated_name = generate_name(name, text, sound)
    validate_sound(sound)
    effect = validate_effect(effect)
    duration = validate_duration(duration)
    validate_image(image)
    thumbnail = validate_thumbnail(thumbnail)

    found_alert = db.session.query(Alert).filter_by(name=generated_name).one_or_none()
    if found_alert:
        found_alert.name = generated_name
        found_alert.text = text
        found_alert.sound = sound
        found_alert.duration = duration
        found_alert.thumbnail = thumbnail
        found_alert.image = image
        found_alert.effect = effect
    else:
        new_alert = Alert(
            name=generated_name,
            text=text,
            sound=sound,
            duration=duration,
            effect=effect,
            image=image,
            thumbnail=thumbnail,
        )
        db.session.add(new_alert)
    if save:
        db.session.commit()
    return generated_name


def list_alerts(sort="name", page=1, limit=None, search=None):
    # TODO: sort by age, popularity
    sort_options = {"name": Alert.name, "created_at": Alert.created_at}
    alerts, page_metadata = apply_filters(Alert, sort_options, "name", sort=sort, page=page, limit=limit, search=search)
    return [alert.as_dict() for alert in alerts], page_metadata


def alert(name="", text="", sound="", effect="", duration=0, image="", hit_socket=True, chat=False):
    if name:
        alert_obj = db.session.query(Alert).filter_by(name=name).one_or_none()
        if not alert_obj:
            raise Exception("Alert not found: {}".format(name))
        alert_data = alert_obj.as_dict()
        socket_data = {
            "text": alert_data["text"],
            "sound": alert_data["sound"],
            "effect": alert_data["effect"],
            "image": alert_data["image"],
            "duration": alert_data["duration"],
        }
    else:
        validate_sound(sound)
        effect = validate_effect(effect)
        duration = validate_duration(duration)
        validate_image(image)
        socket_data = {"text": text, "sound": sound, "effect": effect, "image": image, "duration": duration}
    if hit_socket:
        socketio.emit("FromAPI", socket_data)
    chatbot = get_chatbot()
    if chat and chatbot:
        chatbot.chat("/me {}".format(socket_data["text"]))
    return socket_data["text"]


def remove_alert(name):
    alert = db.session.query(Alert).filter_by(name=name)
    if alert.count():
        alert_name = alert.one_or_none().name

        for group in list_groups()[0]:
            if alert_name in group["alerts"]:
                remove_from_group(group["name"], [alert_name])
        alert.delete()

        db.session.commit()
        return alert_name
    else:
        raise Exception("Alert not found: {}".format(name))


# GROUPS
def set_group(group_name, alert_names, thumbnail="", always_chat=False, chat_message=None, save=True):
    thumbnail = validate_thumbnail(thumbnail)
    group_alert = db.session.query(GroupAlert).filter_by(group_name=group_name).one_or_none()
    if group_alert:
        group_alert.thumbnail = thumbnail
        group_alert.always_chat = always_chat
        group_alert.chat_message = chat_message
        for alert in group_alert.alerts:
            db.session.delete(alert)
    else:
        group_alert = GroupAlert(
            group_name=group_name, thumbnail=thumbnail, always_chat=always_chat, chat_message=chat_message
        )
        db.session.add(group_alert)

    if save:
        db.session.commit()

    return add_to_group(group_name, alert_names, save=save)


def add_to_group(group_name, alert_names, save=True):
    new_alerts = []

    group_alert = db.session.query(GroupAlert).filter_by(group_name=group_name).one_or_none()
    if not group_alert:
        group_alert = GroupAlert(group_name=group_name)
        db.session.add(group_alert)

    index = db.session.query(GroupAlertAssociation).filter_by(group_name=group_name).count()
    for alert_name in alert_names:
        alert = db.session.query(Alert).filter_by(name=alert_name)
        if not alert.count():
            raise Exception("Alert not found: {}".format(alert_name))

        if not db.session.query(GroupAlertAssociation).filter_by(group_name=group_name, alert_name=alert_name).count():
            new_alerts.append(alert_name)
            new_association = GroupAlertAssociation(
                group_name=group_alert.group_name, alert_name=alert_name, index=index
            )
            db.session.add(new_association)
            index += 1
    if save:
        db.session.commit()
    return new_alerts


def list_groups(sort="name", page=1, limit=None, search=None):
    groups = OrderedDict()
    # TODO: sort by age, popularity
    sort_options = {"name": GroupAlert.group_name}
    group_alerts, page_metadata = apply_filters(
        GroupAlert, sort_options, "group_name", sort=sort, page=page, limit=limit, search=search
    )

    for group_alert in group_alerts:
        alerts = sorted(group_alert.alerts, key=lambda group_alert: group_alert.index)
        alerts = [alert.alert_name for alert in alerts]
        groups[group_alert.group_name] = {
            "name": group_alert.group_name,
            "alerts": alerts,
            "thumbnail": group_alert.thumbnail,
            "always_chat": group_alert.always_chat,
            "chat_message": group_alert.chat_message,
        }
    listed_groups = list(groups.values())
    return listed_groups, page_metadata


def group_alert(group_name, random_choice=True, hit_socket=True, chat=False):
    group_alert = db.session.query(GroupAlert).filter_by(group_name=group_name).one_or_none()
    if not group_alert:
        raise Exception("Group not found: {}".format(group_name))
    group_alerts = [result.alert_name for result in group_alert.alerts]
    if random_choice:
        chosen_alert = random.choice(group_alerts)
    else:
        chosen_alert = group_alerts[group_alert.current_index]
        group_alert.current_index = (group_alert.current_index + 1) % len(group_alerts)
        db.session.commit()

    # add to counts
    for count in group_alert.counts:
        counts.add_to_count(count.name)

    alert_message = alert(chosen_alert, hit_socket=hit_socket, chat=False)

    chatbot = get_chatbot()
    if chatbot and (chat or group_alert.always_chat):
        message = group_alert.chat_message if group_alert.chat_message else "/me {}".format(alert_message)
        chatbot.chat(message)

    return alert_message


def remove_from_group(group_name, alert_names):
    group_alert = db.session.query(GroupAlert).filter_by(group_name=group_name).one_or_none()
    if not group_alert:
        raise Exception("Group not found: {}".format(group_name))

    for alert_name in alert_names:
        alert = db.session.query(Alert).filter_by(name=alert_name)
        if not alert.count():
            raise Exception("Alert not found: {}".format(alert_name))

    alerts = [alert for alert in group_alert.alerts if alert.alert_name in alert_names]
    removed_alerts = [alert.alert_name for alert in alerts]
    for alert in alerts:
        db.session.delete(alert)

    db.session.commit()
    return removed_alerts


def remove_group(group_name):
    group = db.session.query(GroupAlert).filter_by(group_name=group_name).one_or_none()
    if group:
        for alert in group.alerts:
            db.session.delete(alert)
        db.session.delete(group)
        db.session.commit()
        return group_name
    else:
        raise Exception("Group not found: {}".format(group_name))
