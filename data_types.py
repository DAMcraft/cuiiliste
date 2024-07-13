from datetime import datetime
from enum import Enum

from async_dns import Address


class SingleProbeResponseType(Enum):
    BLOCKED = 1
    NOT_BLOCKED = 2
    ERROR = 3
    TIMEOUT = 4
    NXDOMAIN = 5


class FullProbeResponseType(Enum):
    NOT_BLOCKED = 1
    PARTIALLY_BLOCKED = 2
    BLOCKED = 3
    FAKE_BLOCKED = 4
    ERROR = 5
    NXDOMAIN = 6


class DNSResolver:
    def __init__(self, name: str, address: Address, is_blocking: bool, isp: str):
        self.name = name
        self.address = address
        self.is_blocking = is_blocking
        self.isp = isp

    def __str__(self):
        return (f"{self.name} ({self.address}) - {'blocking' if self.is_blocking else 'non-blocking'}"
                f"{' - ' + self.isp if self.isp else ''}")

    def __eq__(self, other):
        return self.address == other.address


class BlockingInstance:
    def __init__(self, domain: str, isp: str, blocked_on: datetime):
        self.domain = domain
        self.isp = isp
        self.blocked_on = blocked_on

    def __eq__(self, other):
        return self.domain == other.domain and self.isp == other.isp


class BlockedDomain:
    def __init__(self, domain: str, added_by: str | None, first_blocked_on: datetime):
        self.domain = domain
        self.added_by = added_by
        self.first_blocked_on = first_blocked_on


class SingleProbeResponse:
    def __init__(self, response: SingleProbeResponseType, duration: int, domain: str, resolver: DNSResolver):
        self.response = response
        self.duration = duration
        self.domain = domain
        self.resolver = resolver

    def __str__(self):
        return f"{self.domain} - {self.resolver}: {self.response.name} ({self.duration}ms)"


class FullProbeResponse:
    def __init__(self, responses: list[SingleProbeResponse], final_result: FullProbeResponseType):
        self.responses = responses
        self.final_result = final_result


class ResolverHealth(Enum):
    REACHABLE = 1
    UNREACHABLE = 2
    ERROR = 3


class HealthCheckResponse:
    def __init__(self, resolver: DNSResolver, health: ResolverHealth, ping: int):
        self.resolver = resolver
        self.health = health
        self.ping = ping

    def __str__(self):
        return f"{self.resolver} - {self.health.name}"
