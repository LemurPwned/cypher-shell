import os
import time

from neo4j import GraphDatabase

from .utils import get_logger

logger = get_logger()


def timing(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        return result, end_time - start_time

    return wrapper


class QueryRunner:
    def __init__(
        self,
        uri: str = os.getenv("NEO4J_URI"),
        user: str = os.getenv("NEO4J_USER"),
        password: str = os.getenv("NEO4J_PASSWORD"),
    ):
        assert uri, "NEO4J_URI is not set"
        assert user, "NEO4J_USER is not set"
        assert password, "NEO4J_PASSWORD is not set"
        logger.info(f"Connecting to Neo4j [{uri}]")
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        try:
            self.check_connection()
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j [{uri}]: {e}")
            raise e from e

    def check_connection(self):
        with self.driver.session() as session:
            session.run("RETURN 1")

    def close(self):
        self.driver.close()

    @timing
    def run(self, query: str):
        with self.driver.session() as session:
            res = session.run(query)
            logger.debug(f"Query results: {res}")
            return res.data()
