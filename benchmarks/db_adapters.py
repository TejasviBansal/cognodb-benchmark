"""
Shared connection + query-execution adapters for all 5 platforms.
Each adapter exposes: connect(), run(query_dict), close()
query_dict is a per-platform dict of {platform_name: query_string} so each
benchmark script can define one logical query with 5 syntax variants.
"""
from neo4j import GraphDatabase
from arango import ArangoClient
from falkordb import FalkorDB
from dotenv import load_dotenv
import os
import time

load_dotenv()


class BoltAdapter:
    """Covers CognoDB, Neo4j, Memgraph — all Bolt/Cypher via the neo4j driver."""

    def __init__(self, uri_env, user_env, pass_env):
        self.uri = os.environ[uri_env]
        self.user = os.environ[user_env]
        self.password = os.environ[pass_env]
        self.driver = None

    def connect(self):
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        return self

    def timed_query(self, cypher, params=None):
        with self.driver.session() as session:
            t0 = time.perf_counter()
            result = session.run(cypher, params or {})
            result.consume()  # force full execution, not just first record
            t1 = time.perf_counter()
        return (t1 - t0) * 1000  # ms

    def close(self):
        if self.driver:
            self.driver.close()


class ArangoAdapter:
    def __init__(self):
        self.uri = os.environ["ARANGO_URI"]
        self.user = os.environ["ARANGO_USER"]
        self.password = os.environ["ARANGO_PASSWORD"]
        self.db = None

    def connect(self):
        client = ArangoClient(hosts=self.uri)
        self.db = client.db("benchmark", username=self.user, password=self.password)
        return self

    def timed_query(self, aql, params=None):
        t0 = time.perf_counter()
        cursor = self.db.aql.execute(aql, bind_vars=params or {})
        list(cursor)  # force full execution
        t1 = time.perf_counter()
        return (t1 - t0) * 1000

    def close(self):
        pass  # python-arango has no persistent connection to close


class FalkorAdapter:
    def __init__(self):
        self.host = os.environ["FALKORDB_HOST"]
        self.port = int(os.environ["FALKORDB_PORT"])
        self.user = os.environ["FALKORDB_USER"]
        self.password = os.environ["FALKORDB_PASSWORD"]
        self.graph = None

    def connect(self):
        db = FalkorDB(host=self.host, port=self.port, username=self.user, password=self.password)
        self.graph = db.select_graph("benchmark")
        return self

    def timed_query(self, cypher, params=None):
        t0 = time.perf_counter()
        self.graph.query(cypher, params or {})
        t1 = time.perf_counter()
        return (t1 - t0) * 1000

    def close(self):
        pass


def get_adapter(platform):
    """Returns a connected adapter for the given platform name."""
    if platform == "cognodb":
        return BoltAdapter("COGNODB_URI", "COGNODB_USER", "COGNODB_PASSWORD").connect()
    elif platform == "neo4j":
        return BoltAdapter("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD").connect()
    elif platform == "memgraph":
        return BoltAdapter("MEMGRAPH_URI", "MEMGRAPH_USER", "MEMGRAPH_PASSWORD").connect()
    elif platform == "arangodb":
        return ArangoAdapter().connect()
    elif platform == "falkordb":
        return FalkorAdapter().connect()
    else:
        raise ValueError(f"Unknown platform: {platform}")


PLATFORMS = ["cognodb", "neo4j", "memgraph", "arangodb", "falkordb"]