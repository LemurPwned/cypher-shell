from functools import lru_cache
from itertools import groupby

import neo4j

from ..utils import get_logger

logger = get_logger()

PROMPT_GENERATE_QUERY = """
You are a helpful assistant that generates Cypher queries.

You are given a list of node labels and relationship types.
You need to generate a Cypher query that will return the data you need to answer the user's question.

Node descriptions: {node_labels}
Relationship descriptions: {rel_labels}

For array properties, prefer WHERE X in Y instead of WHERE Y CONTAINS X.
Return the Cypher query as a string. Do not include any other text.
"""


PROMPT_GENERATE_QUERY_AUTOSCHEMA = """
You are a helpful assistant that generates Cypher queries.

You are given a list of node labels and relationship types based on the database schema.
Here is the schema:
{schema}
Here is the list of node and relationship properties:
Node properties: {node_properties}
Relationship properties: {rel_properties}

Here is the relationship structure:
{relationship_structure}

You need to generate a Cypher query that will return the data you need to answer the user's question.
"""

PROMPT_FIX_QUERY = """
You are a top-tier Cypher expert.
Given a query and an error message, fix the query.
You can also use the previous queries and errors to fix the query.
DO NOT REPEAT THE SAME QUERY.
Return only the fixed query as a string.
"""


def _query_run(session: neo4j.Session, query: str):
    results = session.run(query)
    data = results.data()
    return data


def get_nodes_schema(session: neo4j.Session):
    schema_query = """CALL db.schema.visualization()"""
    results = session.run(schema_query)
    data = results.data()
    return data


def node_and_rel_labels(session: neo4j.Session):
    nodes = "CALL db.labels()"
    rels = "CALL db.relationshipTypes()"
    results_nodes = session.run(nodes)
    results_rels = session.run(rels)

    data_nodes = results_nodes.data()
    data_rels = results_rels.data()
    return data_nodes, data_rels


def get_properties(session: neo4j.Session):
    node_results = session.run("CALL db.schema.nodeTypeProperties()")
    rel_results = session.run("CALL db.schema.relTypeProperties()")
    node_data = node_results.data()
    rel_data = rel_results.data()
    return node_data, rel_data


def format_relationship_structure(relationship_map: list[dict[str, list[str]]]) -> str:
    """Format the relationship structure into a string digestible by LLMs."""
    sorted_relationship_map = sorted(relationship_map, key=lambda x: x["relationshipType"])
    rel_str = ""
    for k, g in groupby(sorted_relationship_map, key=lambda x: x["relationshipType"]):
        start_nodes, end_nodes = [], []
        for x in g:
            start_nodes.extend(x["startNodeLabels"])
            end_nodes.extend(x["endNodeLabels"])
        start_nodes = list(set(start_nodes))
        end_nodes = list(set(end_nodes))
        rel_str += f"Relationship: {k}: Start nodes: {start_nodes} -> End nodes: {end_nodes}\n"
    return rel_str


@lru_cache(maxsize=1)
def get_relationship_structure_sampled(session: neo4j.Session, sample_size: int = 1000):
    logger.info(f"Getting relationship structure with sample size {sample_size}")
    schema_query = f"""
    MATCH (s)-[r]->(e)
    WITH s, r, e, rand() AS random
    ORDER BY random
    LIMIT {sample_size}
    RETURN DISTINCT type(r) AS relationshipType, labels(s) AS startNodeLabels, labels(e) AS endNodeLabels
    """
    results = _query_run(session, schema_query)
    return format_relationship_structure(results)


def get_relationship_structure_detailed(session: neo4j.Session):
    """This is somewhat inefficient, but it's only run once."""
    start_node_query = """
    MATCH (n)
    WITH labels(n) AS nodeLabels
    MATCH (start)-[r]->()
    WHERE all(label IN nodeLabels WHERE label IN labels(start))
    RETURN DISTINCT nodeLabels, collect(DISTINCT type(r)) AS relationshipTypes
    """
    start_node_data = _query_run(session, start_node_query)

    end_node_query = """
    MATCH (n)
    WITH labels(n) AS nodeLabels
    MATCH ()-[r]->(end)
    WHERE all(label IN nodeLabels WHERE label IN labels(end))
    RETURN DISTINCT nodeLabels, collect(DISTINCT type(r)) AS relationshipTypes
    """
    end_node_data = _query_run(session, end_node_query)

    # combine the results
    relationship_map = {}
    for rel_data in start_node_data:
        for rel in rel_data["relationshipTypes"]:
            if rel not in relationship_map:
                relationship_map[rel] = {
                    "start_nodes": [],
                    "end_nodes": [],
                }
            relationship_map[rel]["start_nodes"].extend(rel_data["nodeLabels"])
    for rel_data in end_node_data:
        for rel in rel_data["relationshipTypes"]:
            if rel not in relationship_map:
                relationship_map[rel] = {
                    "start_nodes": [],
                    "end_nodes": [],
                }
            relationship_map[rel]["end_nodes"].extend(rel_data["nodeLabels"])

    return relationship_map
