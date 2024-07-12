import asyncio
from datetime import datetime
import data_types as t
import database
import dns


def test_domain(domain: str) -> dict[str, str | list[dict[str, str | int]]]:
    resolvers = database.get_dns_resolvers()
    results = asyncio.run(dns.run_full_check(domain, resolvers))
    if results.final_result in (t.FullProbeResponseType.BLOCKED, t.FullProbeResponseType.PARTIALLY_BLOCKED):
        for response in results.responses:
            if response.response == t.SingleProbeResponseType.BLOCKED:
                database.add_blocking_instance(domain, response.resolver)
            database.add_blocked_domain(domain, response.resolver.isp, datetime.now())
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
