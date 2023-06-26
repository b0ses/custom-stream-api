## The API

The logic behind everything. Takes in POSTs and does magic.
* Send messages to your Stream Overlay to do stuff
* Hooks up to your chatbot

### Installing
```
    # Setup venv
    # python3 -m venv .venvs/custom_stream_api
    
    # Add this to the activate
    # export PYTHONPATH="[path to the cloned repo, absolute or $HOME]:$PYTHONPATH"
    
    # get on the vnev
    > source .venvs/custom_stream_api/bin/activate
    # Install dependencies
    > (custom_stream_api) pip3 install -r ./requirements/app_requirements.txt
    
```

### Setting up a new DB
```
    cd custom_stream_api
    alembic upgrade head
```

### Settings

Fill in your [settings](custom_stream_api/settings.py).

### Running
```
    (custom_stream_api) python3 custom_stream_api/server.py
```

### Documentation

* [Sending Alerts](docs/alerts.md)