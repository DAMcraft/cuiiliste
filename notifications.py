import os
import requests


def send_webhook(data: dict):
    webhook_url = os.getenv("WEBHOOK_URL")
    if not webhook_url:
        return
    requests.post(webhook_url, json=data)


# def blocking_instance_removed(domain: str, isp: str):
#     send_webhook({
#         # "content": f"<@&{os.getenv('CUII_NOTIF_ROLE_ID')}>",
#         "embeds": [
#             {
#                 "title": f"Domain unblocked by {isp}",
#                 "description": f'The domain "`{domain}`" has been  unblocked by {isp}.',
#                 "color": 0x57F287
#             }
#         ],
#         "allowed_mentions": {
#             "roles": [os.getenv('CUII_NOTIF_ROLE_ID')]
#         }
#     })
#
#
# def blocking_instance_added(domain: str, isp: str):
#     send_webhook({
#         # "content": f"<@&{os.getenv('CUII_NOTIF_ROLE_ID')}>",
#         "embeds": [
#             {
#                 "title": "Domain blocked",
#                 "description": f'The domain "`{domain}`" has been blocked by {isp}.',
#                 "color": 0xED4245
#             }
#         ],
#         "allowed_mentions": {
#             "roles": [os.getenv('CUII_NOTIF_ROLE_ID')]
#         }
#     })


def domain_unblocked(domain: str):
    send_webhook({
        "content": f"<@&{os.getenv('CUII_NOTIF_ROLE_ID')}>",
        "embeds": [
            {
                "title": "Domain unblocked",
                "description": f'The domain "`{domain}`" has been fully unblocked.',
                "color": 0x57F287
            }
        ],
        "allowed_mentions": {
            "roles": [os.getenv('CUII_NOTIF_ROLE_ID')]
        }
    })


def domain_potentially_blocked(domain: str):
    send_webhook({
        "content": f"",
        "embeds": [
            {
                "title": "Domain potentially blocked",
                "description": f'The domain "`{domain}`" is potentially blocked.',
                "color": 0xED4245
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
                "title": "Domain blocked",
                "description": f'The domain "`{domain}`" has been blocked.',
                "color": 0xED4245
            }
        ],
        "allowed_mentions": {
            "roles": [os.getenv('CUII_NOTIF_ROLE_ID')]
        }
    })


def error(message: str):
    return  # disable
    # send_webhook({
    #     "content": f"",
    #     "embeds": [
    #         {
    #             "title": "Fehler",
    #             "description": message,
    #             "color": 0xED4245
    #         }
    #     ]
    # })
