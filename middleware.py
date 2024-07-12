import asyncio
from datetime import datetime
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
                "duration": result.duration
            }
            for result in results.responses
        ]
    }
