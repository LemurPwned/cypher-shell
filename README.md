# Cypher Shell

A shell for querying Neo4j with Cypher using LLMs.

## Installation

```bash
pip install cypher-shell
```

## How to use

```bash
python -m cypher_shell --help
```

or

```bash
python -m cypher_shell --config configs/movies.yaml
```

where `configs/movies.yaml` is a configuration file that contains the node and relationship descriptions.

If no configuration file is provided, the tool will try to generate a schema automatically. This might give worse results.

You need to set the `.env` file with your OpenAI API key and Neo4j credentials. See `.env_template` for more information.
