import asyncio
from datetime import datetime

import background_tasks
import data_types as t
import database
import dns


def test_domain(domain: str, resolvers: list[t.DNSResolver]) -> dict[str, str | list[dict[str, str | int]]]:
    results = asyncio.run(dns.run_full_check(domain, resolvers))
    if results.final_result in (t.FullProbeResponseType.BLOCKED, t.FullProbeResponseType.PARTIALLY_BLOCKED):
        database.add_blocking_instances([
                t.BlockingInstance(domain, result.resolver.isp, datetime.now())
                for result in results.responses if result.response == t.SingleProbeResponseType.BLOCKED
        ])
        database.add_blocked_domain(t.BlockedDomain(domain, None, datetime.now()))
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
    return {
        "resolvers": [
            {
                "resolver": resolver.resolver.name,
                "health": resolver.health.name,
                "ping": resolver.ping,
                "isp": resolver.resolver.isp,
                "is_blocking": resolver.resolver.is_blocking
            }
            for resolver in resolver_healths
        ]
    }
