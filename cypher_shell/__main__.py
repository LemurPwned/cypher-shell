import logging
import os

import typer
import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Prompt

from .agent import CypherFlowSimple
from .query_runner import QueryRunner
from .utils import get_logger

logger = get_logger()

console = Console()

app = typer.Typer(
    name="cypher-shell",
    help="A shell for running Cypher queries on a Neo4j database.",
    add_completion=True,
)


@app.command(help="Run a Cypher shell")
def run(
    cfg_path: str | None = typer.Option(default=None, help="Path to the .yaml configuration file"),
    env_path: str | None = typer.Option(default=None, help="Path to the .env file"),
    debug: bool = typer.Option(default=False, help="Enable debug mode"),
):
    load_dotenv(env_path, override=True)
    cfg = {}
    if cfg_path is None:
        console.print(
            "No configuration file provided, using auto-schema generation",
            style="bold yellow",
        )
    else:
        with open(cfg_path) as f:
            cfg = yaml.safe_load(f)

        assert cfg is not None, "Configuration file is empty"
        assert (
            "node_descriptions" in cfg and "relationship_descriptions" in cfg
        ), "Both node_descriptions and relationship_descriptions must be provided in the configuration file"
    if debug:
        logger.setLevel(logging.DEBUG)
    query_runner = QueryRunner(
        uri=os.getenv("NEO4J_URI"),
        user=os.getenv("NEO4J_USER"),
        password=os.getenv("NEO4J_PASSWORD"),
    )
    flow = CypherFlowSimple(
        query_runner=query_runner,
        **cfg,
    )
    while True:
        query = Prompt.ask("[bold cyan]Enter your query[/bold cyan]")
        results = flow.run(query)
        if results:
            console.print(results)
        else:
            console.print("No results found", style="bold red")


if __name__ == "__main__":
    app()
