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
    resp: t.SingleProbeResponseType = t.SingleProbeResponseType.NOT_BLOCKED  # default to not blocked
    start_time = asyncio.get_event_loop().time()
    dispatcher = async_dns.request.udp.Dispatcher(resolver.address.ip_type)
    try:
        req = DNSMessage(qr=REQUEST)
        req.qd = [Record(REQUEST, domain, types.SOA)]
        data = await dispatcher.send(req, resolver.address, 3.0)
        res = DNSMessage.parse(data)

        end_time = asyncio.get_event_loop().time()
        duration = int((end_time - start_time) * 1000)

        if resolver.blocking_type == t.BlockingType.SERVFAIL:
            if res.r == 2:
                # SERVFAIL
                resp = t.SingleProbeResponseType.BLOCKED

        elif resolver.blocking_type == t.BlockingType.NO_SOA:
            if res.r == 3 and len(res.ns) == 0:
                resp = t.SingleProbeResponseType.BLOCKED

        return t.SingleProbeResponse(resp, duration, domain, resolver)

    except (CancelledError, asyncio.TimeoutError):
        resp = t.SingleProbeResponseType.TIMEOUT
        return t.SingleProbeResponse(resp, 3000, domain, resolver)
    except BaseException as e:
        notifications.error(f"Ein DNS Resolver hat einen Fehler {resolver}: {e}")
        print(f"Error with resolver {resolver}: {e}")
        traceback.print_exc()
    finally:
        try:
            dispatcher.destroy()
        except Exception as e:
            print(f"Error destroying dispatcher: {e}")


async def run_full_check(domain: str, dns_resolvers: list[t.DNSResolver]) -> t.FullProbeResponse:
    # Run the check on all resolvers concurrently
    tasks = [is_cuii_blocked_single(domain, resolver) for resolver in dns_resolvers]
    results: list[t.SingleProbeResponse] = await asyncio.gather(*tasks)  # noqa
    # Analyze the results
    final_result = analyze_results(results)
    return t.FullProbeResponse(results, final_result)


def analyze_results(results: list[t.SingleProbeResponse]):
    # Group the results by blocking and non-blocking resolvers
    # blocking_results, non_blocking_results = [], []
    # for result in results:
    #     if result.resolver.is_blocking:
    #         # The resolver is a blocking resolver, add it to the blocking results
    #         blocking_results.append(result)
    #     else:
    #         # Not a blocking resolver
    #         non_blocking_results.append(result)

    # all not blocked
    not_blocked = all(result.response == t.SingleProbeResponseType.NOT_BLOCKED for result in results)
    if not_blocked:
        return t.FullProbeResponseType.NOT_BLOCKED

    # all blocked
    fully_blocked = all(result.response == t.SingleProbeResponseType.BLOCKED for result in results)
    if fully_blocked:
        return t.FullProbeResponseType.BLOCKED

    partially_blocked = any(result.response == t.SingleProbeResponseType.BLOCKED for result in results)
    if partially_blocked:
        return t.FullProbeResponseType.PARTIALLY_BLOCKED

    all_errors = all(
        result.response in (t.SingleProbeResponseType.ERROR, t.SingleProbeResponseType.TIMEOUT)
        for result in results
    )
    if all_errors:
        return t.FullProbeResponseType.ERROR


def tes(domain):
    resolver = t.DNSResolver(
        "test",
        t.Address.parse("94.135.170.54"),
        True,
        "test",
        t.BlockingType.NO_SOA
    )
    print(asyncio.run(is_cuii_blocked_single(domain, resolver)).response)


if __name__ == '__main__':
    tes("michgibtesniaacht.com")
    tes("kinox.to")
    tes("google.com")
