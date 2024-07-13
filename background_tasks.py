import asyncio
import threading

import data_types as t
import dns

resolver_healths: list[t.HealthCheckResponse] = []


def get_resolver_health() -> list[t.HealthCheckResponse]:
    return resolver_healths


async def resolver_health_updater(resolvers: list[t.DNSResolver]):
    while True:
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
        await asyncio.sleep(60)


def launch(resolvers: list[t.DNSResolver]):
    try:
        asyncio.get_running_loop()
        asyncio.create_task(resolver_health_updater(resolvers))
    except RuntimeError:  # No running event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.create_task(resolver_health_updater(resolvers))

        def run_loop(loop_):
            loop_.run_forever()

        thread = threading.Thread(target=run_loop, args=(loop,), daemon=True)
        thread.start()
