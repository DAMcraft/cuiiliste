import os
import requests


def send_webhook(data: dict):
    webhook_url = os.getenv("WEBHOOK_URL")
    if not webhook_url:
        return
    requests.post(webhook_url, json=data)


def blocking_instance_removed(domain: str, isp: str):
    send_webhook({
        # "content": f"<@&{os.getenv('CUII_NOTIF_ROLE_ID')}>",
        "embeds": [
            {
                "title": f"Domain von {isp} entsperrt",
                "description": f"Die Domain {domain} wurde von {isp} entsperrt.",
                "color": 0x57F287
            }
        ],
        "allowed_mentions": {
            "roles": [os.getenv('CUII_NOTIF_ROLE_ID')]
        }
    })


def blocking_instance_added(domain: str, isp: str):
    send_webhook({
        # "content": f"<@&{os.getenv('CUII_NOTIF_ROLE_ID')}>",
        "embeds": [
            {
                "title": "Domain gesperrt",
                "description": f"Die Domain {domain} wurde von {isp} gesperrt.",
                "color": 0xED4245
            }
        ],
        "allowed_mentions": {
            "roles": [os.getenv('CUII_NOTIF_ROLE_ID')]
        }
    })


def domain_unblocked(domain: str):
    send_webhook({
        "content": f"<@&{os.getenv('CUII_NOTIF_ROLE_ID')}>",
        "embeds": [
            {
                "title": "Domain entsperrt",
                "description": f"Die Domain {domain} wurde komplett entsperrt.",
                "color": 0x57F287
            }
        ],
        "allowed_mentions": {
            "roles": [os.getenv('CUII_NOTIF_ROLE_ID')]
        }
    })


def domain_blocked(domain: str):
    send_webhook({
        "content": f"<@&{os.getenv('CUII_NOTIF_ROLE_ID')}>",
        "embeds": [
            {
                "title": "Domain gesperrt",
                "description": f"Die Domain {domain} wurde gesperrt.",
                "color": 0xED4245
            }
        ],
        "allowed_mentions": {
            "roles": [os.getenv('CUII_NOTIF_ROLE_ID')]
        }
    })


def error(message: str):
    send_webhook({
        "content": f"",
        "embeds": [
            {
                "title": "Fehler",
                "description": message,
                "color": 0xED4245
            }
        ]
    })
