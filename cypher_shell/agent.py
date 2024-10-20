from swarm import Agent, Swarm

from .memory import Memory
from .prompts.cypher import PROMPT_FIX_QUERY, PROMPT_GENERATE_QUERY
from .query_runner import QueryRunner
from .utils import get_logger

logger = get_logger()


class BaseFlow:
    def __init__(
        self,
        query_runner: QueryRunner,
        node_descriptions: str,
        relationship_descriptions: str,
    ):
        self.client = Swarm()
        self.query_runner = query_runner
        self.node_descriptions = node_descriptions
        self.relationship_descriptions = relationship_descriptions
        self._init_memory()

    def _init_memory(self):
        self.memory = Memory()


class CypherFlowSimple(BaseFlow):
    def __init__(
        self,
        query_runner: QueryRunner,
        node_descriptions: str,
        relationship_descriptions: str,
    ):
        super().__init__(query_runner, node_descriptions, relationship_descriptions)
        self.query_generator = Agent(
            name="Cypher Query generator",
            model="gpt-4o-mini",
            temperature=0.0,
            instructions=PROMPT_GENERATE_QUERY.format(
                node_labels=node_descriptions, rel_labels=relationship_descriptions
            ),
        )
        self.query_fixer = Agent(
            name="Cypher Query Fixer",
            model="gpt-4o-mini",
            temperature=0.0,
            instructions=PROMPT_FIX_QUERY,
        )
        self.client = Swarm()

    def _run_query(self, query: str, attempt=2):
        cleaned_query = query.replace("```", "").strip().replace("cypher", "")

        if attempt == 0:
            logger.error("retried too many times")
            return None
        try:
            logger.info(f"Running query: {cleaned_query}")
            results = self.query_runner.run(cleaned_query)
        except Exception as e:
            logger.exception(f"Query failed: {e}")
            query = self.client.run(
                agent=self.query_fixer,
                messages=[{"role": "user", "content": cleaned_query}],
            )
            query = query.messages[-1]["content"]
            results = self._run_query(query, attempt=attempt - 1)
        return results

    def run(self, query: str):
        query_candidate = self.client.run(agent=self.query_generator, messages=[{"role": "user", "content": query}])
        query_candidate = query_candidate.messages[-1]["content"]

        return self._run_query(query_candidate, attempt=2)
