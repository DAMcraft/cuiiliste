import asyncio
import traceback
from asyncio import CancelledError

import data_types as t
from async_dns import DNSMessage
from async_dns.core import types
from async_dns.resolver import DNSClient
import notifications


__all__ = ["is_cuii_blocked_single", "run_full_check"]


async def is_cuii_blocked_single(domain: str, resolver: t.DNSResolver) -> t.SingleProbeResponse:
    resp: t.SingleProbeResponseType = t.SingleProbeResponseType.ERROR  # assume error by default
    start_time = asyncio.get_event_loop().time()
    try:
        client = DNSClient()
        res: DNSMessage = await client.query(domain, types.A, resolver.address)

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
        notifications.send_notif(f"Ein DNS Resolver hat einen Fehler {resolver}: {e}", should_ping=False)
        print(f"Error with resolver {resolver}: {e}")
        traceback.print_exc()
        resp = t.SingleProbeResponseType.ERROR

    finally:
        end_time = asyncio.get_event_loop().time()
        duration = int((end_time - start_time) * 1000)
        # return the actual response here
        return t.SingleProbeResponse(resp, duration, domain, resolver)


async def run_full_check(
        domain: str,
        dns_resolvers: list[t.DNSResolver]
) -> t.FullProbeResponse:
    tasks = [is_cuii_blocked_single(domain, resolver) for resolver in dns_resolvers]

    results: list[t.SingleProbeResponse] = await asyncio.gather(*tasks)  # noqa
    blocking_results     = [result for result in results if     result.resolver.is_blocking]  # noqa
    non_blocking_results = [result for result in results if not result.resolver.is_blocking]

    # Determine the final result
    final_result: t.FullProbeResponseType
    # If any non-blocking resolver returns blocked, it's a fake block
    if any(
            result.response == t.SingleProbeResponseType.BLOCKED
            for result in non_blocking_results):
        final_result = t.FullProbeResponseType.FAKE_BLOCKED

    # If at least one blocking resolver returns blocked and all others return blocked/timeouts, the domain is blocked
    elif (
            any(
                result.response == t.SingleProbeResponseType.BLOCKED for result in blocking_results
            ) and all(
                result.response in (t.SingleProbeResponseType.BLOCKED, t.SingleProbeResponseType.TIMEOUT)
                for result in blocking_results
            )):
        final_result = t.FullProbeResponseType.BLOCKED

    # If any blocking resolver returns blocked, the domain is partially blocked
    elif any(
            result.response == t.SingleProbeResponseType.BLOCKED
            for result in blocking_results):
        final_result = t.FullProbeResponseType.PARTIALLY_BLOCKED

    # All blocking resolvers returned an error (not good)
    elif all(
            result.response == t.SingleProbeResponseType.ERROR
            for result in blocking_results):
        final_result = t.FullProbeResponseType.ERROR

    # One resolver didn't find the domain, all other neither/timeout -> The domain does not exist
    elif (
            any(
                result.response == t.SingleProbeResponseType.NXDOMAIN for result in results
            ) and all(
                result.response in (t.SingleProbeResponseType.NXDOMAIN, t.SingleProbeResponseType.TIMEOUT)
                for result in results
            )):
        final_result = t.FullProbeResponseType.NXDOMAIN

    else:
        final_result = t.FullProbeResponseType.NOT_BLOCKED

    return t.FullProbeResponse(results, final_result)
