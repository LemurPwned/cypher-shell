from neo4j import GraphDatabase
import os
from .utils import get_logger

logger = get_logger()


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
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def run(self, query: str):
        with self.driver.session() as session:
            res = session.run(query)
            logger.debug(f"Query results: {res}")
            return res.data()
