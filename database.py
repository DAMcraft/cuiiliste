"""
Please note that you need to populate the ISP and DNS resolvers tables manually.

The database schema is as follows:

create database cuii;
use cuii;

CREATE TABLE `dns_resolvers` (
  `ip` varchar(30) NOT NULL,
  `name` varchar(255) NOT NULL,
  `is_blocking` tinyint(1) NOT NULL COMMENT 'Weather the DNS resolver is following cuii blocks or not',
  `isp` varchar(255) DEFAULT NULL,
  `protocol` varchar(5) DEFAULT 'udp',
  `blocking_type` enum('CNAME','NXDOMAIN') DEFAULT NULL,
  PRIMARY KEY (`ip`),
  KEY `dns_resolvers_isp_name_fk` (`isp`),
  CONSTRAINT `dns_resolvers_isp_name_fk` FOREIGN KEY (`isp`) REFERENCES `isp` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci

CREATE TABLE `blocking_instances` (
  `domain` varchar(255) NOT NULL,
  `blocker` varchar(255) NOT NULL COMMENT 'the company blocking the domain',
  `blocked_on` timestamp NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`domain`,`blocker`),
  KEY `blocking_instance_fk` (`blocker`),
  CONSTRAINT `blocked_by_fk` FOREIGN KEY (`domain`) REFERENCES `blocked_domains` (`domain`),
  CONSTRAINT `blocking_instance_fk` FOREIGN KEY (`blocker`) REFERENCES `isp` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci

CREATE TABLE `blocked_domains` (
  `domain` varchar(255) NOT NULL,
  `first_blocked_on` timestamp NULL DEFAULT current_timestamp(),
  `added_by` varchar(255) DEFAULT NULL,
  `site_reference` varchar(30) DEFAULT NULL,
  PRIMARY KEY (`domain`),
  KEY `blocked_domains_blocked_sites_name_fk` (`site_reference`),
  CONSTRAINT `blocked_domains_blocked_sites_name_fk` FOREIGN KEY (`site_reference`) REFERENCES `blocked_sites` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci

CREATE TABLE `isp` (
  `name` varchar(255) NOT NULL,
  PRIMARY KEY (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci

CREATE TABLE `blocked_sites` (
  `name` varchar(30) NOT NULL,
  `recommendation_url` text NOT NULL,
  `sitzungsdatum` date NOT NULL,
  PRIMARY KEY (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
"""  # noinspection

from threading import Lock
import os

from mysql.connector.pooling import PooledMySQLConnection

import data_types as t
from mysql.connector import pooling

__all__ = [
    "get_connection",
    "get_dns_resolvers",
    "get_blocked_domains",
#    "get_blocking_instances",
    "add_blocked_domain",
    # "add_blocking_instance",
    # "add_blocking_instances",
    # "remove_blocking_instance",
    "remove_blocked_domain"
]


# Singleton class to manage database connection
class DatabaseConnection:
    _instance = None
    _lock = Lock()

    @staticmethod
    def get_instance():
        if DatabaseConnection._instance is None:
            with DatabaseConnection._lock:  # Ensure only one instance is created and not two in a race condition
                if DatabaseConnection._instance is None:
                    DatabaseConnection._instance = DatabaseConnection()
        return DatabaseConnection._instance

    def __init__(self):
        if DatabaseConnection._instance is not None:
            raise Exception("This class is a singleton!")  # Prevent creating a new instance
        else:
            self._pool = pooling.MySQLConnectionPool(
                pool_size=10,
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASS"),
                host=os.getenv("DB_HOST"),
                database=os.getenv("DB_NAME")
            )

    def get_connection(self) -> PooledMySQLConnection:
        return self._pool.get_connection()


def get_connection() -> PooledMySQLConnection:
    return DatabaseConnection.get_instance().get_connection()


def get_dns_resolvers() -> list[t.DNSResolver]:
    # table: dns_resolvers
    # columns: name, ip, is_blocking, isp
    resolvers = []
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT name, ip, is_blocking, isp, protocol, blocking_type FROM dns_resolvers WHERE is_blocking = 1")
        results = cursor.fetchall()
    for name, ip, is_blocking, isp, protocol, blocking_type_str in results:
        blocking_type = None
        if is_blocking:
            if blocking_type_str == "NO_SOA":
                blocking_type = t.BlockingType.NO_SOA
            elif blocking_type_str == "SERVFAIL":
                blocking_type = t.BlockingType.SERVFAIL
            elif blocking_type_str == "CNAME":
                blocking_type = t.BlockingType.CNAME

        resolvers.append(
            t.DNSResolver(
                name,
                t.Address.parse(ip, default_protocol=protocol, allow_domain=True),
                bool(is_blocking),
                isp,
                blocking_type
            )
        )
    return resolvers


def get_blocked_domains() -> list[t.BlockedDomain]:
    # table: blocked_domains
    # columns: domain, added_by, first_blocked_on, site_reference
    # table: blocked_sites
    # columns: name, recommendation_url
    # blocked_domains.site_reference -> blocked_sites.name
    blocked_domains = []
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT 
                dom.domain, 
                dom.added_by, 
                dom.first_blocked_on, 
                dom.site_reference, 
                site.recommendation_url, 
                site.sitzungsdatum
            FROM blocked_domains dom 
            LEFT JOIN blocked_sites site ON dom.site_reference = site.name
        """)
        results: list[tuple[str, str, t.datetime, str, str, t.date]] = cursor.fetchall()
    for domain, added_by, first_blocked_on, site_reference, recommendation_url, sitzungsdatum in results:
        site = None
        if site_reference:
            site = t.BlockedSite(site_reference, recommendation_url, sitzungsdatum)
        blocked_domains.append(t.BlockedDomain(domain, added_by, first_blocked_on, site))
    return blocked_domains


# def get_blocking_instances() -> list[t.BlockingInstance]:
#     # table: blocking_instances
#     # columns: domain, blocker, blocked_on
#     blocking_instances = []
#     with get_connection() as connection:
#         cursor = connection.cursor()
#         cursor.execute("SELECT domain, blocker, blocked_on FROM blocking_instances")
#         for domain, isp, blocked_on in cursor.fetchall():
#             blocking_instances.append(t.BlockingInstance(domain, isp, blocked_on))
#     return blocking_instances


def add_blocked_domain(blocked_domain: t.BlockedDomain) -> bool:
    # returns True if the domain was added, False if it already exists
    with get_connection() as connection:
        cursor = connection.cursor()
        if blocked_domain.site:
            cursor.execute(
                """
                    INSERT IGNORE INTO blocked_sites (name, recommendation_url, sitzungsdatum)
                    VALUES (%s, %s, %s)
                    """,
                (blocked_domain.site.name, blocked_domain.site.recommendation_url, blocked_domain.site.sitzungsdatum)
            )

        cursor.execute(
            """            
                    INSERT IGNORE INTO blocked_domains (domain, added_by, first_blocked_on, site_reference)
                    VALUES (%s, %s, %s, %s)
                    """,
            (blocked_domain.domain, blocked_domain.added_by, blocked_domain.first_blocked_on,
             blocked_domain.site.name if blocked_domain.site else None)
        )
        connection.commit()
        return cursor.rowcount > 0  # if the row was added, rowcount will be 1


# def add_blocking_instance(blocking_instance: t.BlockingInstance):
#     with get_connection() as connection:
#         cursor = connection.cursor()
#         cursor.execute(
#             """
#                     INSERT IGNORE INTO blocking_instances (domain, blocker, blocked_on)
#                     VALUES (%s, %s, %s)
#                     """,
#             (blocking_instance.domain, blocking_instance.isp, blocking_instance.blocked_on)
#         )
#         connection.commit()
#
#
# def add_blocking_instances(blocking_instances: list[t.BlockingInstance]):
#     with get_connection() as connection:
#         cursor = connection.cursor()
#         cursor.executemany(
#             """
#                     INSERT IGNORE INTO blocking_instances (domain, blocker, blocked_on)
#                     VALUES (%s, %s, %s)
#                     """,
#             [(blocking_instance.domain, blocking_instance.isp, blocking_instance.blocked_on) for blocking_instance in
#              blocking_instances]
#         )
#         connection.commit()
#
#
# def remove_blocking_instance(domain: str, isp: str):
#     with get_connection() as connection:
#         cursor = connection.cursor()
#         cursor.execute(
#             """
#                     DELETE FROM blocking_instances WHERE domain = %s AND blocker = %s
#                     """,
#             (domain, isp)
#         )
#         connection.commit()


def remove_blocked_domain(domain: str):
    with get_connection() as connection:
        cursor = connection.cursor()
        # delete the domain from the blocked_domains and blocking_instances tables
        cursor.execute(
            """
                    DELETE FROM blocking_instances WHERE domain = %s
                    """,
            (domain,)
        )
        cursor.execute(
            """
                    DELETE FROM blocked_domains WHERE domain = %s
                    """,
            (domain,)
        )
        connection.commit()


def get_ignorelist() -> list[str]:
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT domain FROM domain_ignorelist")
        return [domain for domain, in cursor.fetchall()]


def add_potentially_blocked_domain(blocked_domain: t.BlockedDomain) -> bool:
    # returns True if the domain was added, False if it already exists
    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """            
                    INSERT IGNORE INTO potentially_blocked (domain)
                    VALUES (%s)
                    """,
            (blocked_domain.domain,)
        )
        connection.commit()
        print(cursor.rowcount)
        return cursor.rowcount > 0  # if the row was added, rowcount will be 1
