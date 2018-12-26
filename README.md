## The API

The logic behind everything. Takes in POSTs and does magic.
* Send messages to your Stream Overlay to do stuff
* Hooks up to your chatbot

### Installing
```
    # Install pip3
    > apt-get install python3-pip
    # Work in your virtual environment (however you want that setup)
    > workon custom-stream-api
    # Install dependencies
    > (custom-stream-overlay) pip3 install -r requirements.txt
    # Add this directory to your virtual environment
    add2virtualenv [path to this directory]
```

### Setting up a new DB
```
    # export FLASK_APP=custom_stream_api/server.py
    # flask db upgrade head -d custom_stream_api/migrations
```

### Settings

Fill in your [settings](custom_stream_api/settings.py).

### Running
```
    (custom-stream-overlay) python3 custom_stream_api/server.py
```

### Documentation

* [Sending Alerts](docs/alerts.md)