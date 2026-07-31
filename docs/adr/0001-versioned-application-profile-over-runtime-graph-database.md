# Use a versioned application profile before a runtime graph database

The prediction explanation graph will be built from a versioned JSON application profile and query-time in-memory indexes, while retaining reviewed JSON-LD/SKOS links to SWEET. This was chosen over importing SWEET/DMDO into Neo4j because the current product needs a small auditable subgraph, deterministic local execution, and explicit similarity-score decomposition; the API boundary allows a graph database to replace the index later when case volume or graph traversal requirements justify the operational cost.
