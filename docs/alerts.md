# Alerts

These endpoints are in charge of managing and displaying your alerts.

## Sending an Alert

You can send any alert whatsoever with this endpoint, regardless of it being in the database.

`POST` `/alerts/alert`

Request:
```
{
	"message": "It works!",
	"sound": "https://www.myinstants.com/media/sounds/super-mario-coin-sound.mp3",
	"duration": 1000,
	"effect": ""
}
```

* `name` (string, optional, ''): The name of the alert stored in the database (see below)
* `message` (string, optional, ''): The text you want to be displayed, can be blank
* `sound` (string, optional, ''): The URL of the sound you want to be played along with the message, can be blank
* `duration` (integer, optional, `3000`): Milliseconds you want the text to be displayed, the sound will play entirely
* `effect` (string, optional, ''): How you want the text to appear
    * ``: no effect, just appears and disappears for the duration
    * `fade`: fades in and out for the duration

Response:

```
{
    "message": [message]
}
```

Possible Messages
* `Displaying alert`
* `Alert not found: [name]`
    
## Managing Alerts

You can save alerts in the database and just refer to them when calling the above endpoint.

### Saving Alerts

You can store alerts in the database.

`POST` `/alerts/add_alert`

Request:
```
{
	"message": "It works!",
	"sound": "https://www.myinstants.com/media/sounds/super-mario-coin-sound.mp3"
}
```

* `name` (string, optional, ''): The name of the alert. If not provided, it will be derived from the message. Note, this means for sound bites, you have to name them
* `message` (string, optional, ''): The text you want to be displayed, can be blank
* `sound` (string, optional, ''): The URL of the sound you want to be played along with the message, can be blank

Response:

```
{
    "message": [message]
}
```

Possible Messages
* `Alert in database: [name]` (it won't make the same one twice if it has the same name)


### Listing Available Alerts

All of the alerts.

`GET` `/alerts/`

Response:
```
[
    {
        "image": null,
        "name": "brrrrrrrr",
        "sound": "https://www.myinstants.com/media/sounds/airhorn_1.mp3",
        "text": "BRRRRRRRR"
    },
    {
        "image": null,
        "name": "it_works!",
        "sound": "https://www.myinstants.com/media/sounds/super-mario-coin-sound.mp3",
        "text": "It works!"
    }
]
```

Note: `image` is a work in progress, currently `null`

### Deleting Alerts

Remove an alert from the database.

`POST` `/alerts/remove_alert`

Request:
```
{
	"name": "it_works!",
}
```

* `name` (string, required): The name of the alert to remove.

Response:

```
{
    "message": [message]
}
```
Possible messages:
* `Alert removed: [name]`
* `Alert not found: [name]`