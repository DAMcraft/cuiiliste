import asyncio
from datetime import datetime

import background_tasks
import data_types as t
import database
import dns
import notifications


def test_domain(domain: str, resolvers: list[t.DNSResolver]) -> dict[str, str | list[dict[str, str | int]]]:
    results = asyncio.run(dns.run_full_check(domain, resolvers))
    if results.final_result in (t.FullProbeResponseType.BLOCKED, t.FullProbeResponseType.PARTIALLY_BLOCKED):
        database.add_blocking_instances([
                t.BlockingInstance(domain, result.resolver.isp, datetime.now())
                for result in results.responses if result.response == t.SingleProbeResponseType.BLOCKED
        ])
        is_new_block = database.add_blocked_domain(t.BlockedDomain(domain, None, datetime.now()))
        if is_new_block:
            notifications.send_notif(f"Domain {domain} has been blocked")

    return {
        "domain": domain,
        "final_result": results.final_result.name,
        "responses": [
            {
                "resolver": result.resolver.name,
                "response": result.response.name,
                "duration": result.duration,
                "is_blocking": result.resolver.is_blocking,
            }
            for result in results.responses
        ]
    }


def get_resolvers():
    resolver_healths = background_tasks.get_resolver_health()
    return [
            {
                "resolver": resolver.resolver.name,
                "health": resolver.health.name,
                "ping": resolver.ping,
                "isp": resolver.resolver.isp,
                "is_blocking": resolver.resolver.is_blocking
            }
            for resolver in resolver_healths
    ]


def get_blocked_domains():
    blocked_domains = database.get_blocked_domains()
    return [
        {
            "domain": blocked_domain.domain,
            "added_by": blocked_domain.added_by,
            "first_blocked_on": blocked_domain.first_blocked_on.date().isoformat()
        }
        for blocked_domain in blocked_domains
    ]
