import asyncio
import threading

import data_types as t
import database
import dns
import notifications

resolver_healths: list[t.HealthCheckResponse] = []


def get_resolver_health() -> list[t.HealthCheckResponse]:
    return resolver_healths


async def update_resolver_health(resolvers: list[t.DNSResolver]):
    res = await dns.run_full_check("damcraft.de", resolvers)
    resolver_healths.clear()
    for result in res.responses:
        response = result.response
        status = t.ResolverHealth.REACHABLE
        if response == t.SingleProbeResponseType.ERROR:
            status = t.ResolverHealth.ERROR
        elif response == t.SingleProbeResponseType.TIMEOUT:
            status = t.ResolverHealth.UNREACHABLE
        resolver_healths.append(t.HealthCheckResponse(result.resolver, status, result.duration))


async def update_dns_blocklist(resolvers: list[t.DNSResolver]):
    # Update the blocklist database
    domains = database.get_blocked_domains()  # forgive me for calling this blocking function from an async context
    # blocking_instances = database.get_blocking_instances()  # sowwy
    for domain in domains:
        results = await dns.run_full_check(domain.domain, resolvers)

        # if all ISPs have not blocked the domain, remove the domain from the blocklist
        if results.final_result == t.FullProbeResponseType.NOT_BLOCKED:
            notifications.domain_unblocked(domain.domain)
            database.remove_blocked_domain(domain.domain)
            continue


async def background_loop(resolvers: list[t.DNSResolver]):
    while True:
        start_time = asyncio.get_event_loop().time()
        await update_resolver_health(resolvers)
        await update_dns_blocklist(resolvers)

        end_time = asyncio.get_event_loop().time()
        await asyncio.sleep(60 - (end_time - start_time))  # 60 seconds - time taken


def launch(resolvers: list[t.DNSResolver]):
    try:
        asyncio.get_running_loop()
        asyncio.create_task(background_loop(resolvers))
    except RuntimeError:  # No running event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.create_task(background_loop(resolvers))

        def run_loop(loop_):
            loop_.run_forever()

        thread = threading.Thread(target=run_loop, args=(loop,), daemon=True)
        thread.start()
