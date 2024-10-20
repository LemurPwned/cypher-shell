PROMPT_GENERATE_QUERY = """
You are a helpful assistant that generates Cypher queries.

You are given a list of node labels and relationship types.
You need to generate a Cypher query that will return the data you need to answer the user's question.

Node descriptions: {node_labels}
Relationship descriptions: {rel_labels}

For array properties, prefer WHERE X in Y instead of WHERE Y CONTAINS X.
Return the Cypher query as a string. Do not include any other text.
"""


PROMPT_FIX_QUERY = """
You are a top-tier Cypher expert.
Given a query and an error message, fix the query.
Return only the fixed query as a string.
"""


def get_node_schema(session, node_labels: list[str]):
    schema_query = [f"Match (n:{node_label}) return properties(n), ID(n) LIMIT 1" for node_label in node_labels]
    results = session.run(schema_query)
    return results
