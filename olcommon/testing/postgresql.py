# -*- coding:utf-8 -*-

from plone.testing import Layer

import os
import os.path
import psycopg2
import shutil
import subprocess
import tempfile


class PostgresqlLayer(Layer):
    """Layer for testing postgresql"""

    def setUp(self):

        # Create and run a tempory postgresql

        self["postgresql_install_prefix"] = os.environ["POSTGRESQL_PREFIX"]
        self["postgresql_data_directory"] = tempfile.mkdtemp(
            dir="/dev/shm"
        )  # use the tempfs mount

        # Connection
        self["postgresql_port"] = 5432
        self["postgresql_socket_directory"] = self["postgresql_data_directory"]
        self["postgresql_host"] = ""  # tcp is not wanted
        self["postgresql_user"] = "testing"

        # Connection to the postgres database
        self["postgresql_postgres_url"] = (
            f'dbname=postgres user={self["postgresql_user"]} '
            f'host={self["postgresql_socket_directory"]} '
        )

        # Connection

        # Track databases
        self["postgresql_db_count"] = 0

        subprocess.run(
            (
                f'{os.environ["POSTGRESQL_PREFIX"]}/bin/initdb',
                "--auth",
                "reject",
                "--auth-local",
                "trust",
                "--pgdata",
                self["postgresql_data_directory"],
                "--encoding",
                "UTF8",
                "--username",
                self["postgresql_user"],
            ),
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        self["postgresql_process"] = subprocess.Popen(
            (
                f'{os.environ["POSTGRESQL_PREFIX"]}/bin/postgres',
                "-D",
                self["postgresql_data_directory"],
                "-p",
                str(self["postgresql_port"]),
                "-h",
                self["postgresql_host"],
                "-k",
                self["postgresql_socket_directory"],
                "-F",
            ),  # turn off fsync. We want speed and disposability.
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def testSetUp(self):
        self["postgresql_db_count"] += 1
        self["postgresql_database"] = f'unittest_{self["postgresql_db_count"]}'
        conn = psycopg2.connect(self["postgresql_postgres_url"])
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        cur.execute(f'create database {self["postgresql_database"]};')
        conn.commit()
        self["postgresql_url"] = (
            f"postgresql://"
            f"{self['postgresql_user']}:@"
            f"/{self['postgresql_database']}"
            f"?host={self['postgresql_socket_directory']}"
        )

    def testTearDown(self):
        # Disconnect all connections and clean up databases
        conn = psycopg2.connect(self["postgresql_postgres_url"])
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        cur.execute(
            "select pg_terminate_backend(pid) "
            "from pg_stat_activity "
            f'where datname = \'{self["postgresql_database"]}\' and pid <> pg_backend_pid() '
        )
        cur.execute(f'drop database {self["postgresql_database"]};')
        conn.commit()

        # Clean up values
        del self["postgresql_database"]
        del self["postgresql_url"]

    def tearDown(self):
        """Stop postgresql process and remove data dir"""
        process = self["postgresql_process"]
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            if self.poll() is None:
                process.kill()
                process.wait(timeout=10)
        shutil.rmtree(self["postgresql_data_directory"])


POSTGRESQL_LAYER = PostgresqlLayer()
