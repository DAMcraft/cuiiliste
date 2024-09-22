import asyncio
import datetime
import threading
from collections import defaultdict

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
    blocking_instances = database.get_blocking_instances()  # sowwy
    for domain in domains:
        results = await dns.run_full_check(domain.domain, resolvers)
        blocking_results = [result for result in results.responses if result.resolver.is_blocking]

        associated_blocking_instances = [
            instance for instance in blocking_instances
            if instance.domain == domain.domain
        ]  # get all blocking instances associated with the domain

        # group the results by ISP
        isp_results = defaultdict(list)
        for result in blocking_results:
            isp_results[result.resolver.isp].append(result)

        if results.final_result == t.FullProbeResponseType.NXDOMAIN:
            # If the domain is gone, we can't do any further checks
            database.remove_blocked_domain(domain.domain)
            continue

        skip_isps = []  # ISPs that have already been marked as blocked, so we don't mark them again
        for isp, results_ in isp_results.items():
            if isp in skip_isps:
                continue
            # a domain should be marked as blocked for that ISP if ANY resolver of the ISP return blocked
            if (
                    # If any result is blocking, or the general result is blocking, it must be blocked
                    any(result.response == t.SingleProbeResponseType.BLOCKED for result in results_)
                    or results.final_result == t.FullProbeResponseType.BLOCKED
            ) and (
                    # Ensure that the ISP is not already marked as blocked
                    not any(instance.isp == isp for instance in associated_blocking_instances)
            ):
                notifications.blocking_instance_added(domain.domain, isp)
                database.add_blocking_instance(t.BlockingInstance(domain.domain, isp, datetime.datetime.now()))
                skip_isps.append(isp)
                continue

            # a domain should be unblocked for that ISP if ALL resolvers of the ISP return not blocked
            if (
                    # Check if we track the ISP as blocking the domain
                    any(instance.isp == isp for instance in associated_blocking_instances)
            ) and (
                    # Check if all resolvers of the ISP return not blocked
                    all(result.response == t.SingleProbeResponseType.NOT_BLOCKED for result in results_)
            ):
                notifications.blocking_instance_removed(domain.domain, isp)
                database.remove_blocking_instance(domain.domain, isp)

        # if all ISPs have not blocked the domain, remove the domain from the blocklist
        if results.final_result in (t.FullProbeResponseType.NOT_BLOCKED, t.FullProbeResponseType.NXDOMAIN):
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
