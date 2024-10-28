import asyncio
import traceback
from asyncio import CancelledError

import async_dns.request

import data_types as t
from async_dns import DNSMessage, REQUEST, Record
from async_dns.core import types
import notifications

__all__ = ["is_cuii_blocked_single", "run_full_check"]


async def is_cuii_blocked_single(domain: str, resolver: t.DNSResolver) -> t.SingleProbeResponse:
    resp: t.SingleProbeResponseType = t.SingleProbeResponseType.ERROR  # assume error by default
    start_time = asyncio.get_event_loop().time()
    try:
        req = DNSMessage(qr=REQUEST)
        req.qd = [Record(REQUEST, domain, types.A)]
        res: DNSMessage = await async_dns.request.udp.request(req, resolver.address)

        if len(res.an) == 0:
            # Domain does not exist
            resp = t.SingleProbeResponseType.NXDOMAIN
            return  # noqa, return early and go to finally block

        for answer in res.an:
            if answer.qtype == types.CNAME and answer.data.data == "notice.cuii.info":
                resp = t.SingleProbeResponseType.BLOCKED
                return  # noqa, return early and go to finally block

        resp = t.SingleProbeResponseType.NOT_BLOCKED

    except (CancelledError, asyncio.TimeoutError):
        resp = t.SingleProbeResponseType.TIMEOUT

    except BaseException as e:
        notifications.error(f"Ein DNS Resolver hat einen Fehler {resolver}: {e}")
        print(f"Error with resolver {resolver}: {e}")
        traceback.print_exc()
        resp = t.SingleProbeResponseType.ERROR

    finally:
        end_time = asyncio.get_event_loop().time()
        duration = int((end_time - start_time) * 1000)
        # return the actual response here
        return t.SingleProbeResponse(resp, duration, domain, resolver)


async def run_full_check(domain: str, dns_resolvers: list[t.DNSResolver]) -> t.FullProbeResponse:
    # Run the check on all resolvers concurrently
    tasks = [is_cuii_blocked_single(domain, resolver) for resolver in dns_resolvers]
    results: list[t.SingleProbeResponse] = await asyncio.gather(*tasks)  # noqa
    # Analyze the results
    final_result = analyze_results(results)
    return t.FullProbeResponse(results, final_result)


def analyze_results(results: list[t.SingleProbeResponse]):
    # Group the results by blocking and non-blocking resolvers
    blocking_results, non_blocking_results = [], []
    for result in results:
        if result.resolver.is_blocking:
            # The resolver is a blocking resolver, add it to the blocking results
            blocking_results.append(result)
        else:
            # Not a blocking resolver
            non_blocking_results.append(result)

    # If any non-blocking resolver returns blocked, it's a fake block (someone pretending that a domain is blocked)
    if any(
            result.response == t.SingleProbeResponseType.BLOCKED
            for result in non_blocking_results):
        return t.FullProbeResponseType.FAKE_BLOCKED

    # If any non-blocking resolver could find the domain, it exists
    domain_exists = any(result.response != t.SingleProbeResponseType.NXDOMAIN for result in non_blocking_results)

    # If any CNAME-blocking resolver detects the domain as blocked, it is at least partially blocked
    partially_blocked = False
    for result in blocking_results:
        if result.resolver.blocking_type != t.BlockingType.CNAME:
            # We only care about CNAME resolvers here
            continue
        if result.response == t.SingleProbeResponseType.BLOCKED:
            partially_blocked = True
            break

    # If the domain does not exist, and it's partially blocked,
    # we assume it's fully blocked since we can't analyze it further
    if not domain_exists and partially_blocked:
        return t.FullProbeResponseType.BLOCKED

    # Check if an NXDOMAIN blocking resolver blocks it, meaning the domain might be CUII blocked, but we can't be sure
    potentially_blocked = False
    if not partially_blocked and domain_exists:
        # If an NXDOMAIN resolver returns NXDOMAIN, the domain might be CUII blocked
        for result in non_blocking_results:
            if result.resolver.blocking_type != t.BlockingType.NXDOMAIN:
                # CNAME blocking, not relevant here
                continue
            if result.response == t.SingleProbeResponseType.NXDOMAIN:
                potentially_blocked = True
                break
    # A potential block can't be further analyzed, so we return it here
    if potentially_blocked:
        return t.FullProbeResponseType.POTENTIALLY_BLOCKED

    # If at least one blocking resolver returns blocked and all others return blocked/timeouts, the domain is blocked
    fully_blocked = False
    if partially_blocked:  # the domain needs to be at least partially blocked to be fully blocked
        fully_blocked = True  # assume True, changes below if not
        for result in blocking_results:
            if result.resolver.blocking_type == t.BlockingType.CNAME \
                    and result.response not in (t.SingleProbeResponseType.BLOCKED, t.SingleProbeResponseType.TIMEOUT):
                # A blocking CNAME resolver did not return blocked (or timeout), so the domain is not fully blocked
                fully_blocked = False
                break
            if result.resolver.blocking_type == t.BlockingType.NXDOMAIN \
                    and result.response not in (t.SingleProbeResponseType.NXDOMAIN, t.SingleProbeResponseType.TIMEOUT):
                # A blocking NXDOMAIN resolver did not return NXDOMAIN (or timeout), so the domain is not fully blocked
                fully_blocked = False
                break

    if fully_blocked:
        return t.FullProbeResponseType.BLOCKED
    if partially_blocked:
        return t.FullProbeResponseType.PARTIALLY_BLOCKED

    if not partially_blocked and not domain_exists:
        return t.FullProbeResponseType.NXDOMAIN

    return t.FullProbeResponseType.NOT_BLOCKED
