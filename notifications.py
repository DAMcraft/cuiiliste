import os
import requests


def send_notif(message: str, should_ping: bool = True):
    # Send a message to a discord webhook (for now at least)
    # I don't want to use another requirement for this, so I'll just use urllib
    webhook_url = os.getenv("WEBHOOK_URL")
    if not webhook_url:
        return
    message = "@everyone " + message if should_ping else message
    data = {
        "content": message,
        "allowed_mentions": {
            "parse": ["everyone"]
        }
    }
    req = requests.post(webhook_url, json=data)
    print(req.status_code)
