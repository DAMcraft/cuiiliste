import asyncio
import datetime
import threading

import data_types as t
import database
import dns

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
    blocking_instances = database.get_blocking_instances()  # sowwy
    for domain in domains:
        print(f"Checking {domain.domain}")
        results = await dns.run_full_check(domain.domain, resolvers)
        print(f"Results for {domain.domain}: {results.final_result.name}")
        associated_blocking_instances = [
            instance for instance in blocking_instances
            if instance.domain == domain.domain
        ]  # get all blocking instances associated with the domain

        # group the results by ISP
        isp_results = {}
        for result in results.responses:
            if result.resolver.isp not in isp_results:
                isp_results[result.resolver.isp] = []
            isp_results[result.resolver.isp].append(result)

        for isp, results in isp_results.items():
            # a domain should be marked as blocked for that ISP if ANY resolver of the ISP return blocked
            if any(result.response == t.SingleProbeResponseType.BLOCKED for result in results) \
                    and not any(instance.isp == isp for instance in associated_blocking_instances):  # not yet blocked
                print(f"Adding blocking instance for {domain.domain} for ISP {isp}")
                database.add_blocking_instance(t.BlockingInstance(domain.domain, isp, datetime.datetime.now()))

            # a domain should be unblocked for that ISP if ALL resolvers of the ISP return not blocked
            elif all(instance.isp == isp for instance in associated_blocking_instances) \
                    and all(result.response == t.SingleProbeResponseType.NOT_BLOCKED for result in results):
                print(f"Removing blocking instance for {domain.domain} for ISP {isp}")
                database.remove_blocking_instance(domain.domain, isp)


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
