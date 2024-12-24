import logging
import os

import typer
import yaml
from dotenv import load_dotenv
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit.styles import Style, style_from_pygments_cls
from prompt_toolkit.validation import ValidationError, Validator
from pygments.lexers.graph import CypherLexer
from pygments.styles.tango import TangoStyle
from rich.console import Console

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


class ShellValidator(Validator):
    def validate(self, document):
        text = document.text

        if not text:
            raise ValidationError(message="Query cannot be empty", cursor_position=0)


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

    cypher_completer = WordCompleter(
        [
            "cs:",
            "MATCH",
            "WHERE",
            "RETURN",
            "CREATE",
            "DELETE",
            "MERGE",
            "SET",
            "REMOVE",
            "CALL",
            "OPTIONAL",
            "UNWIND",
            "WITH",
            "ORDER BY",
            "SKIP",
            "LIMIT",
            "RETURN DISTINCT",
            "RETURN COUNT",
            "RETURN EXISTS",
            "RETURN DISTINCT",
            "RETURN COUNT",
            "RETURN EXISTS",
            "RETURN DISTINCT",
            "RETURN COUNT",
            "RETURN EXISTS",
            "RETURN DISTINCT",
            "RETURN COUNT",
            "RETURN EXISTS",
        ],
        ignore_case=True,
        match_middle=True,
    )
    tango_style = style_from_pygments_cls(TangoStyle)
    session = PromptSession(
        lexer=PygmentsLexer(CypherLexer),
        validator=ShellValidator(),
        completer=cypher_completer,
        style=tango_style,
        complete_style=CompleteStyle.READLINE_LIKE,
    )
    while True:
        try:
            query = session.prompt(
                HTML("<ansired>Enter your query:  </ansired>"),
                style=Style.from_dict({"": "ansigray"}),
            )
            if results := flow.run(query):
                console.print(results)
            else:
                console.print("No results found", style="bold red")
        except (KeyboardInterrupt, EOFError):
            console.print("Exiting...", style="bold red")
            break


if __name__ == "__main__":
    app()
