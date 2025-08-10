import logging
import re
import random
from sqlalchemy import func, null, sql

from custom_stream_api.alerts.models import Alert, Tag, TagAssociation
from custom_stream_api.counts import counts
from custom_stream_api.shared import db, socketio, get_chatbot

logger = logging.getLogger(__name__)

MAX_LIMIT = 100

TAG_CATEGORIES = [
    "reference",  # where is the sound from (star wars, jurassic park, etc.)
    "character",  # who said it (batman, spongebob)
    "content",  # what is it (fight, pain, win, lose, item, love, directions, numbers)
]

VALID_SOUNDS = ["wav", "mp3", "ogg"]
VALID_IMAGES = ["jpg", "png", "tif", "tiff", "gif", "raw", "jpeg", "webp"]
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
            raise ValueError(f"Invalid sound url: {sound}")
        else:
            return matches[0][4]  # using the regex, this'll return the filename sans extension


def validate_effect(effect):
    effect = effect or ""
    if effect in VALID_EFFECTS:
        return effect
    else:
        raise ValueError(f"Invalid effect: {effect}")


def validate_image(image=""):
    if image:
        matches = re.findall(IMAGE_REXEX, image)
        if not matches:
            raise ValueError(f"Invalid image url: {image}")
        else:
            return matches[0][4]  # using the regex, this'll return the filename sans extension


def validate_color_hex(color_hex):
    if color_hex:
        matches = re.findall(HEX_CODE_REGEX, color_hex)
        if not matches:
            raise ValueError(f"Invalid color hex: {color_hex}")
        else:
            return color_hex


def validate_thumbnail(thumbnail):
    if thumbnail:
        if thumbnail[0] == "#":
            validate_color_hex(thumbnail)
        elif thumbnail[:4] == "http":
            validate_image(thumbnail)
        else:
            raise Exception(f"Invalid thumbnail: {thumbnail}")
    return thumbnail


def validate_tag_category(tag_category):
    tag_category = tag_category or ""
    if tag_category in TAG_CATEGORIES:
        return tag_category
    else:
        raise ValueError(f"Invalid tag_category: {tag_category}")


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


# ALERTS
def save_alert(name, text="", sound="", effect="", image="", thumbnail="", tags=None, save=True):
    validate_sound(sound)
    effect = validate_effect(effect)
    validate_image(image)
    thumbnail = validate_thumbnail(thumbnail)

    found_alert = db.session.query(Alert).filter_by(name=name).one_or_none()
    if found_alert:
        found_alert.name = name
        found_alert.text = text
        found_alert.sound = sound
        found_alert.thumbnail = thumbnail
        found_alert.image = image
        found_alert.effect = effect
    else:
        found_alert = Alert(
            name=name,
            text=text,
            sound=sound,
            effect=effect,
            image=image,
            thumbnail=thumbnail,
        )
        db.session.add(found_alert)

    if tags is not None:
        set_tags(alert_name=found_alert.name, tags=tags, save=save)

    if save:
        db.session.commit()
    return found_alert


def set_tags(alert_name, tags, save=True):
    alert = db.session.query(Alert).filter_by(name=alert_name).one_or_none()
    if not alert:
        raise Exception(f"Alert not found: {alert_name}")
    if tags is None:
        raise Exception(f"Tags must be a list: {tags}")

    # Ignore any tags that are already associated with this alert
    existing_tags = (
        db.session.query(Tag.name)
        .join(TagAssociation, TagAssociation.tag_name == Tag.name)
        .filter(TagAssociation.alert_name == alert.name)
        .all()
    )
    existing_tag_names = set([tag[0] for tag in existing_tags])

    # Delete current tags not in the new set
    delete_tags = list(existing_tag_names - set(tags))
    if delete_tags:
        delete_associations = (
            db.session.query(TagAssociation.id)
            .join(Alert, TagAssociation.alert_name == Alert.name)
            .join(Tag, TagAssociation.tag_name == Tag.name)
            .filter(Alert.id == alert.id, Tag.name.in_(delete_tags))
        )
        delete_tags_ids = [result[0] for result in delete_associations]
        logger.info(f"Deleting old tags from {alert.name}: {delete_tags}")
        db.session.query(TagAssociation).filter(TagAssociation.id.in_(delete_tags_ids)).delete()

        # Delete any lingering empty tags
        empty_tags = (
            db.session.query(Tag.id, Tag.name)
            .outerjoin(TagAssociation, TagAssociation.tag_name == Tag.name)
            .filter(TagAssociation.id == null())
            .all()
        )
        empty_tag_names = [result[1] for result in empty_tags]
        logger.info(f"Deleting empty tags: {empty_tag_names}")
        db.session.query(Tag).filter(Tag.name.in_(empty_tag_names)).delete()

    # Set any new tags, *ignoring any tags that don't exist*
    new_tags = set(tags) - existing_tag_names
    if new_tags:
        logger.info(f"Setting new tags to {alert.name}: {new_tags}")
        for tag_name in new_tags:
            tag = db.session.query(Tag).filter_by(name=tag_name).one_or_none()
            if not tag:
                continue
            db.session.add(TagAssociation(alert=alert, tag=tag))

    if save:
        db.session.commit()


def alert(name=None, text="", sound="", effect="", image="", hit_socket=True, chat=False, live=True):
    if name:
        alert_obj = db.session.query(Alert).filter_by(name=name).one_or_none()
        if not alert_obj:
            raise Exception(f"Alert not found: {name}")
        alert_data = alert_obj.as_dict()
        socket_data = {
            "text": alert_data["text"],
            "sound": alert_data["sound"],
            "effect": alert_data["effect"],
            "image": alert_data["image"],
        }
    else:
        validate_sound(sound)
        effect = validate_effect(effect)
        validate_image(image)
        socket_data = {"text": text, "sound": sound, "effect": effect, "image": image}
    logger.info(socket_data)
    if hit_socket:
        namespace = "live" if live else "preview"
        socketio.emit("FromAPI", socket_data, namespace=f"/{namespace}")

    chatbot = get_chatbot()
    if chat and chatbot:
        chatbot.chat(f"/me {socket_data['text']}")
    return socket_data["text"]


def alert_details(name):
    found_alert = db.session.query(Alert).filter_by(name=name).one_or_none()
    if not found_alert:
        raise Exception(f"Alert not found: {name}")
    return found_alert.as_dict()


def remove_alert(name):
    alert = db.session.query(Alert).filter_by(name=name)
    if alert.count():
        alert_name = alert.one_or_none().name

        alert.delete()

        db.session.commit()
        return alert_name
    else:
        raise Exception(f"Alert not found: {name}")


# TAGS
def save_tag(name, thumbnail="", category="content", always_chat=False, chat_message=None, alerts=None, save=True):
    thumbnail = validate_thumbnail(thumbnail)
    category = validate_tag_category(category)

    found_tag = db.session.query(Tag).filter_by(name=name).one_or_none()

    if found_tag:
        found_tag.name = name
        found_tag.thumbnail = thumbnail
        found_tag.always_chat = always_chat
        found_tag.chat_message = chat_message
        found_tag.category = category
    else:
        found_tag = Tag(
            name=name, thumbnail=thumbnail, category=category, always_chat=always_chat, chat_message=chat_message
        )
        db.session.add(found_tag)

    if alerts:
        set_alerts(tag_name=found_tag.name, alerts=alerts, save=save)

    if save:
        db.session.commit()

    return found_tag


def set_alerts(tag_name, alerts, save=True):
    tag = db.session.query(Tag).filter_by(name=tag_name).one_or_none()
    if not tag:
        raise Exception(f"Tag not found: {tag_name}")
    if alerts is None:
        raise Exception(f"Alerts must be a list: {alerts}")

    # Ignore any tags that are already associated with this alert
    existing_alerts = (
        db.session.query(Alert.name)
        .join(TagAssociation, TagAssociation.alert_name == Alert.name)
        .filter(TagAssociation.tag_name == tag.name)
        .all()
    )
    existing_alert_names = set([tag[0] for tag in existing_alerts])

    # Delete current tags not in the new set
    delete_alerts = list(existing_alert_names - set(alerts))
    if delete_alerts:
        delete_associations = (
            db.session.query(TagAssociation.id)
            .join(Alert, TagAssociation.alert_name == Alert.name)
            .join(Tag, TagAssociation.tag_name == Tag.name)
            .filter(Tag.id == tag.id, Alert.name.in_(delete_alerts))
        )
        delete_alerts_ids = [result[0] for result in delete_associations]
        logger.info(f"Deleting old tags from {tag.name}: {delete_alerts}")
        db.session.query(TagAssociation).filter(TagAssociation.id.in_(delete_alerts_ids)).delete()

        # Unlike set_tags, we're *not* deleting any alerts that dont have tags

    # Set any new tags, *ignoring any alerts that don't exist*
    new_alerts = set(alerts) - existing_alert_names
    if new_alerts:
        logger.info(f"Setting new tags to {tag.name}: {new_alerts}")
        for alert_name in new_alerts:
            alert = db.session.query(Alert).filter_by(name=alert_name).one_or_none()
            if not alert:
                continue
            db.session.add(TagAssociation(alert=alert, tag=tag))

    if save:
        db.session.commit()


def tag_alert(name, random_choice=True, hit_socket=True, chat=False, live=True):
    tag = db.session.query(Tag).filter_by(name=name).one_or_none()
    if not tag:
        raise Exception(f"Tag not found: {name}")
    if tag.name != "random":
        alert_names = tag.as_dict()["alerts"]
        if random_choice:
            chosen_alert = random.choice(alert_names)
        else:
            chosen_alert = alert_names[tag.current_index]
            tag.current_index = (tag.current_index + 1) % len(alert_names)
            db.session.commit()
    else:
        all_alerts = db.session.query(Alert.name).all()
        chosen_alert = random.choice([alert[0] for alert in all_alerts])

    # add to counts
    for count in tag.counts:
        counts.add_to_count(count.name)

    alert_message = alert(chosen_alert, hit_socket=hit_socket, chat=False, live=live)

    chatbot = get_chatbot()
    if chatbot and (chat or tag.always_chat):
        message = tag.chat_message if tag.chat_message else f"/me {alert_message}"
        chatbot.chat(message)

    return alert_message


def tag_details(name):
    found_tag = db.session.query(Tag).filter_by(name=name).one_or_none()
    if not found_tag:
        raise Exception(f"Tag not found: {name}")
    return found_tag.as_dict()


def remove_tag(name):
    if name == "random":
        raise Exception("Cannot remove 'random' tag")

    tag = db.session.query(Tag).filter_by(name=name)
    if tag.count():
        tag_name = tag.one_or_none().name

        tag.delete()

        db.session.commit()
        return tag_name
    else:
        raise Exception(f"Tag not found: {name}")


# BROWSE
def apply_filters(list_query, sort_options, search_attr, sort="name", page=1, limit=None, search=None):
    if sort:
        sort_options.update({f"-{sort_option}": sort_value for sort_option, sort_value in sort_options.items()})
        if sort not in sort_options:
            raise ValueError(f"Invalid sort option: {sort}")
        order_by = sort_options[sort].desc() if sort[0] == "-" else sort_options[sort].asc()

    if search and isinstance(search, str):
        list_query = list_query.filter(func.lower(search_attr).contains(search.lower()))
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

    total = list_query.count()
    page_metadata = {"total": total, "page": page or 1, "limit": limit}

    return results, page_metadata


def get_exploded_alerts(search, sort):
    tag_query = (
        db.session.query(Alert.name, Alert.thumbnail, sql.expression.literal_column("'Alert'").label("result_type"))
        .join(TagAssociation, TagAssociation.alert_name == Alert.name)
        .join(Tag, TagAssociation.tag_name == Tag.name)
    )
    sort_options = {"name": Tag.name, "created_at": Tag.created_at}
    exploded_alerts, _ = apply_filters(tag_query, sort_options, TagAssociation.tag_name, sort=sort, search=search)
    return exploded_alerts


def paginate(data, page_number, items_per_page):
    start_index = (page_number - 1) * items_per_page
    end_index = start_index + items_per_page
    return data[start_index:end_index]


def browse(
    sort="name", page=1, limit=MAX_LIMIT, search=None, include_alerts=True, include_tags=True, tag_category=None
):
    # TODO: sort by popularity

    results = []
    if include_alerts:
        tag_results = []
        if include_tags:
            tag_query = db.session.query(
                Tag.name, Tag.thumbnail, sql.expression.literal_column("'Tag'").label("result_type")
            )
            if tag_category:
                tag_category = validate_tag_category(tag_category)
                tag_query = tag_query.filter_by(category=tag_category)
            sort_options = {"name": Tag.name, "created_at": Tag.created_at}
            tag_results, _ = apply_filters(tag_query, sort_options, Tag.name, sort=sort, search=search)

        # same thing minus page + limit
        alert_query = db.session.query(
            Alert.name, Alert.thumbnail, sql.expression.literal_column("'Alert'").label("result_type")
        )
        sort_options = {"name": Alert.name, "created_at": Alert.created_at}
        alert_results, _ = apply_filters(alert_query, sort_options, Alert.name, sort=sort, search=search)
        alert_names = [alert.name for alert in list(alert_results)]

        exploded_alerts = []
        if search:
            exploded_alerts = get_exploded_alerts(search, sort)
            # dedupe, prioritize on matched alerts
            exploded_alerts = [
                exploded_alert for exploded_alert in list(exploded_alerts) if exploded_alert.name not in alert_names
            ]

        # tags > matched alerts > exploded alerts from tags
        results = list(tag_results) + list(alert_results) + exploded_alerts
        results = list(dict.fromkeys(results))
        results = paginate(results, int(page), int(limit))
        page_metadata = {"total": len(results), "limit": limit, "page": page}
    else:
        tag_query = db.session.query(
            Tag.name, Tag.thumbnail, sql.expression.literal_column("'Tag'").label("result_type")
        )
        if tag_category:
            tag_category = validate_tag_category(tag_category)
            tag_query = tag_query.filter_by(category=tag_category)
        sort_options = {"name": Tag.name, "created_at": Tag.created_at}
        results, page_metadata = apply_filters(
            tag_query, sort_options, Tag.name, sort=sort, search=search, page=page, limit=limit
        )

    def dict_results(results):
        return [{"name": result[0], "thumbnail": result[1], "type": result[2]} for result in list(results)]

    return dict_results(results), page_metadata
