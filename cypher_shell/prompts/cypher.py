import neo4j

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
You need to generate a Cypher query that will return the data you need to answer the user's question.
"""

PROMPT_FIX_QUERY = """
You are a top-tier Cypher expert.
Given a query and an error message, fix the query.
You can also use the previous queries and errors to fix the query.
DO NOT REPEAT THE SAME QUERY.
Return only the fixed query as a string.
"""


def get_nodes_schema(session: neo4j.Session):
    schema_query = """CALL db.schema.visualization()"""
    results = session.run(schema_query)
    data = results.data()
    return data


def node_and_rel_labels(session: neo4j.Session):
    nodes = "CALL db.relationshipTypes()"
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
