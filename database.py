from threading import Lock
import os

from mysql.connector.pooling import PooledMySQLConnection

import data_types as t
from mysql.connector import pooling

__all__ = [
    "get_connection",
    "get_dns_resolvers",
    "get_blocked_domains",
    "get_blocking_instances",
    "add_blocked_domain",
    "add_blocking_instance",
    "add_blocking_instances"
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
        cursor.execute("SELECT name, ip, is_blocking, isp FROM dns_resolvers")
        results = cursor.fetchall()
    for name, ip, is_blocking, isp in results:
        resolvers.append(t.DNSResolver(name, t.Address.parse(ip), bool(is_blocking), isp))
    return resolvers


def get_blocked_domains() -> list[t.BlockedDomain]:
    # table: blocked_domains
    # columns: domain, added_by, first_blocked_on
    blocked_domains = []
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT domain, added_by, first_blocked_on FROM blocked_domains")
        results = cursor.fetchall()
    for domain, added_by, first_blocked_on in results:
        blocked_domains.append(t.BlockedDomain(domain, added_by, first_blocked_on))
    return blocked_domains


def get_blocking_instances() -> list[t.BlockingInstance]:
    # table: blocking_instances
    # columns: domain, blocker, blocked_on
    blocking_instances = []
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT domain, blocker, blocked_on FROM blocking_instances")
        for domain, isp, blocked_on in cursor.fetchall():
            blocking_instances.append(t.BlockingInstance(domain, isp, blocked_on))
    return blocking_instances


def add_blocked_domain(blocked_domain: t.BlockedDomain) -> bool:
    # returns True if the domain was added, False if it already exists
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
                    INSERT IGNORE INTO blocked_domains (domain, added_by, first_blocked_on) 
                    VALUES (%s, %s, %s)
                    """,
            (blocked_domain.domain, blocked_domain.added_by, blocked_domain.first_blocked_on)
        )
        connection.commit()
        return cursor.rowcount > 0  # if the row was added, rowcount will be 1


def add_blocking_instance(blocking_instance: t.BlockingInstance):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
                    INSERT IGNORE INTO blocking_instances (domain, blocker, blocked_on) 
                    VALUES (%s, %s, %s)
                    """,
            (blocking_instance.domain, blocking_instance.isp, blocking_instance.blocked_on)
        )
        connection.commit()


def add_blocking_instances(blocking_instances: list[t.BlockingInstance]):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.executemany(
            """
                    INSERT IGNORE INTO blocking_instances (domain, blocker, blocked_on) 
                    VALUES (%s, %s, %s)
                    """,
            [(blocking_instance.domain, blocking_instance.isp, blocking_instance.blocked_on) for blocking_instance in
             blocking_instances]
        )
        connection.commit()


def remove_blocking_instance(domain: str, isp: str):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
                    DELETE FROM blocking_instances WHERE domain = %s AND blocker = %s
                    """,
            (domain, isp)
        )
        connection.commit()
