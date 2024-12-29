import os
import re

from neo4j.exceptions import CypherSyntaxError
from openai import OpenAI
from rich.markdown import Markdown
from swarm import Agent, Swarm

from .memory import Memory
from .prompts.cypher import (
    PROMPT_FIX_QUERY,
    PROMPT_GENERATE_QUERY,
    PROMPT_GENERATE_QUERY_AUTOSCHEMA,
    get_nodes_schema,
    get_properties,
    get_relationship_structure_sampled,
)
from .prompts.general import PROMPT_FORMAT_RESULT
from .query_runner import QueryRunner
from .utils import get_logger

logger = get_logger()


class BaseFlow:
    def __init__(
        self,
        query_runner: QueryRunner,
        node_descriptions: str,
        relationship_descriptions: str,
        write_to_file: bool = False,
    ):
        self.client = Swarm()
        self.query_runner = query_runner
        self.node_descriptions = node_descriptions
        self.relationship_descriptions = relationship_descriptions
        self._init_memory(write_to_file)

    def _init_memory(self, write_to_file: bool):
        self.memory = Memory(write_to_file=write_to_file)


class CypherFlowSimple(BaseFlow):
    def __init__(
        self,
        query_runner: QueryRunner,
        node_descriptions: str | None = None,
        relationship_descriptions: str | None = None,
        max_attempts_per_query: int = 3,
        default_model: str = "gpt-4o-mini",
        write_to_file: bool = False,
    ):
        super().__init__(query_runner, node_descriptions, relationship_descriptions, write_to_file)
        logger.debug(f"Using model: {default_model}")
        if node_descriptions is None and relationship_descriptions is None:
            generic_schema = get_nodes_schema(query_runner.driver.session())
            node_properties, rel_properties = get_properties(query_runner.driver.session())
            relationship_structure = get_relationship_structure_sampled(query_runner.driver.session())
            instructions = PROMPT_GENERATE_QUERY_AUTOSCHEMA.format(
                schema=generic_schema,
                node_properties=node_properties,
                rel_properties=rel_properties,
                relationship_structure=relationship_structure,
            )
            logger.debug(instructions)
        else:
            assert node_descriptions is not None and relationship_descriptions is not None
            instructions = PROMPT_GENERATE_QUERY.format(
                node_labels=node_descriptions, rel_labels=relationship_descriptions
            )
        self.query_generator = Agent(
            name="Cypher Query generator",
            model=default_model,
            temperature=0.0,
            instructions=instructions,
        )
        self.query_fixer = Agent(
            name="Cypher Query Fixer",
            model=default_model,
            temperature=0.0,
            instructions=PROMPT_FIX_QUERY,
        )

        self.output_formatter = Agent(
            name="Cypher Output Formatter",
            model=default_model,
            temperature=0.0,
            instructions=PROMPT_FORMAT_RESULT,
        )
        _client = None
        self.use_optiLLM = os.environ.get("USE_OPTILLM", "false") == "true"
        if self.use_optiLLM:
            logger.info("Using OptiLLM")
            OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
            OPENAI_BASE_URL = "http://localhost:8000/v1"
            _client = OpenAI(api_key=OPENAI_KEY, base_url=OPENAI_BASE_URL)
        self.client = Swarm(client=_client)
        self.max_attempts_per_query = max_attempts_per_query

    def _run_query(
        self,
        query: str,
        attempt=2,
        past_errors: list[str] | None = None,
        prev_query_attempts: list[str] | None = None,
        show_syntax_error: bool = False,
    ):
        # cleaned_query = query.replace("```", "").strip().replace("cypher", "")
        # grab anything between ```cypher and ```
        logger.debug(query)
        cleaned_query = None
        try:
            cleaned_query = re.search(r"```cypher(.*)```", query, re.DOTALL)[1]
        except Exception:
            cleaned_query = query.replace("```", "").strip().replace("cypher", "")
        if past_errors is None:
            past_errors = []
        if prev_query_attempts is None:
            prev_query_attempts = []
        if attempt == 0:
            logger.error("retried too many times")
            return None
        try:
            logger.info(f"Running query: {cleaned_query}")
            results, query_timing = self.query_runner.run(cleaned_query)
        except CypherSyntaxError as e:
            msg = f"Query failed due to syntax error: {e.message}"
            if show_syntax_error:
                logger.error(msg)
            else:
                logger.debug(msg)
            return None
        except Exception as e:
            query = self.client.run(
                agent=self.query_fixer,
                messages=[
                    {
                        "role": "user",
                        "content": f"Query: {cleaned_query}\nPrevious queries: {prev_query_attempts}"
                        f"\nPrevious errors: {past_errors}\nError: {e.message}",
                    }
                ],
            )
            query = query.messages[-1]["content"]

            past_errors.append(e.message)
            fn_result = self._run_query(
                query,
                attempt=attempt - 1,
                past_errors=past_errors,
                prev_query_attempts=prev_query_attempts,
            )
            if fn_result is None:
                return None
            results, cleaned_query, query_timing = fn_result
        return results, cleaned_query, query_timing

    def run(self, query: str, use_formatter: bool = True):
        if user_result := self.memory.check_user_query(query):
            logger.info(f"Found user result for query: {query} in memory. Returning.")
            return user_result

        if query.startswith("cs:"):
            logger.debug("Running manual query")
            # this is a manual query, don't ask the agent to generate it
            query = query[3:]
            result = self._run_query(query, attempt=1)
        else:
            logger.debug(f"Previous results: {self.memory.get()}")
            messages = [
                {
                    "role": "user",
                    "content": f"Previous results: {self.memory.get()}\nUser query: {query}",
                }
            ]
            if self.use_optiLLM:
                # use underlying client to avoid extra tool calls
                messages = [{"role": "system", "content": self.query_generator.instructions}] + messages
                query_candidate = self.client.client.chat.completions.create(
                    model="moa-gpt-4o-mini",
                    messages=messages,
                    extra_body={"optillm_approach": "mcts"},
                    temperature=0.0,
                )
                query_candidate = query_candidate.choices[0].message.content
            else:
                query_candidate = self.client.run(
                    agent=self.query_generator,
                    messages=messages,
                )
                query_candidate = query_candidate.messages[-1]["content"]

            result = self._run_query(query_candidate, attempt=self.max_attempts_per_query)
        if result:
            result, machine_query, query_timing = result
            self.memory.add_user_result(query, machine_query, result, query_timing)
            if use_formatter:
                result = self.client.run(
                    agent=self.output_formatter,
                    messages=[
                        {
                            "role": "user",
                            "content": f"User query: {query}\nResults: {result}",
                        }
                    ],
                )
                result = Markdown(result.messages[-1]["content"])
        return result
