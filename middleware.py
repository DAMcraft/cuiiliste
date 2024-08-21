import asyncio
import re
from datetime import datetime

import background_tasks
import data_types as t
import database
import dns
import notifications


def test_domain(domain: str, resolvers: list[t.DNSResolver]) -> dict[str, str | list[dict[str, str | int]]]:
    domain = re.sub(r"^(http(s)?://)?", "", domain.strip().lower())  # normalize domain
    results = asyncio.run(dns.run_full_check(domain, resolvers))
    if results.final_result in (t.FullProbeResponseType.BLOCKED, t.FullProbeResponseType.PARTIALLY_BLOCKED):
        database.add_blocking_instances([
                t.BlockingInstance(domain, result.resolver.isp, datetime.now())
                for result in results.responses if result.response == t.SingleProbeResponseType.BLOCKED
        ])
        is_new_block = database.add_blocked_domain(t.BlockedDomain(domain, None, datetime.now(), None))
        if is_new_block:
            notifications.domain_blocked(domain)

    return {
        "domain": domain,
        "final_result": results.final_result.name,
        "responses": [
            {
                "resolver": result.resolver.name,
                "response": result.response.name,
                "duration": result.duration,
                "obeys_cuii": result.resolver.is_blocking,
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
                "obeys_cuii": resolver.resolver.is_blocking
            }
            for resolver in resolver_healths
    ]


def get_blocked_domains():
    blocked_domains = database.get_blocked_domains()
    return [
        {
            "domain": blocked_domain.domain,
            "added_by": blocked_domain.added_by,
            "first_blocked_on": blocked_domain.first_blocked_on.date().isoformat(),
            "site": blocked_domain.site.name if blocked_domain.site else None,
        }
        for blocked_domain in blocked_domains
    ]
