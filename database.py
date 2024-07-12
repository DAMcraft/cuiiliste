from datetime import datetime
from threading import Lock
import mysql.connector
import os

import data_types as t
from mysql.connector import MySQLConnection

__all__ = [
    "get_connection",
    "get_dns_resolvers",
    "get_blocked_domains",
    "get_blocking_instances",
    "add_blocked_domain",
    "add_blocking_instance",
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
            self._connection = None

    def get_connection(self) -> MySQLConnection:
        if self._connection is None or not self._connection.is_connected():
            self._connection = mysql.connector.connect(
                host=os.getenv("DB_HOST"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASS"),
                database=os.getenv("DB_NAME")
            )
        return self._connection


def get_connection() -> MySQLConnection:
    return DatabaseConnection.get_instance().get_connection()


def get_dns_resolvers() -> list[t.DNSResolver]:
    # table: dns_resolvers
    # columns: name, ip, is_blocking, isp
    resolvers = []
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT name, ip, is_blocking, isp FROM dns_resolvers")
    for name, ip, is_blocking, isp in cursor.fetchall():
        resolvers.append(t.DNSResolver(name, t.Address.parse(ip), bool(is_blocking), isp))
    return resolvers


def get_blocked_domains() -> list[t.BlockedDomain]:
    # table: blocked_domains
    # columns: domain, added_by, first_blocked_on
    blocked_domains = []
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT domain, added_by, first_blocked_on FROM blocked_domains")
    for domain, added_by, first_blocked_on in cursor.fetchall():
        blocked_domains.append(t.BlockedDomain(domain, added_by, first_blocked_on))
    return blocked_domains


def get_blocking_instances() -> list[t.BlockingInstance]:
    # table: blocking_instances
    # columns: domain, blocker, blocked_on
    blocking_instances = []
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT domain, blocker, blocked_on FROM blocking_instances")
    for domain, isp, blocked_on in cursor.fetchall():
        blocking_instances.append(t.BlockingInstance(domain, isp, blocked_on))
    return blocking_instances


def add_blocked_domain(domain: str, added_by: str | None, first_blocked_on: datetime | None):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
                INSERT IGNORE INTO blocked_domains (domain, added_by, first_blocked_on) 
                VALUES (%s, %s, %s)
                """,
        (domain, added_by, first_blocked_on)
    )
    connection.commit()


def add_blocking_instance(domain: str, blocker: t.DNSResolver, blocked_on: datetime = None):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
                INSERT IGNORE INTO blocking_instances (domain, blocker, blocked_on) 
                VALUES (%s, %s, %s)
                """,
        (domain, blocker.name, blocked_on)
    )
    connection.commit()
