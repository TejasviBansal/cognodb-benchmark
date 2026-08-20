from falkordb import FalkorDB
from dotenv import load_dotenv
import csv
import time
import os

load_dotenv()

host = os.environ["FALKORDB_HOST"]
port = int(os.environ["FALKORDB_PORT"])
user = os.environ["FALKORDB_USER"]
password = os.environ["FALKORDB_PASSWORD"]

db = FalkorDB(host=host, port=port, username=user, password=password)
graph = db.select_graph("benchmark")

BATCH_SIZE = 1000


def load_nodes():
    start = time.time()
    count = 0
    with open("data/nodes.csv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        batch = []
        for row in reader:
            batch.append({"id": int(row["id"]), "name": row["name"]})
            count += 1
            if len(batch) == BATCH_SIZE:
                graph.query(
                    "UNWIND $rows AS row CREATE (p:Person {id: row.id, name: row.name})",
                    {"rows": batch},
                )
                batch = []
        if batch:
            graph.query(
                "UNWIND $rows AS row CREATE (p:Person {id: row.id, name: row.name})",
                {"rows": batch},
            )
    elapsed = time.time() - start
    print(f"Nodes: loaded {count} rows in {elapsed:.2f}s ({count/elapsed:.1f} rows/sec)")
    return count, elapsed


def load_edges():
    start = time.time()
    count = 0
    with open("data/edges.csv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        batch = []
        for row in reader:
            batch.append({"source": int(row["source"]), "target": int(row["target"])})
            count += 1
            if len(batch) == BATCH_SIZE:
                graph.query(
                    """
                    UNWIND $rows AS row
                    MATCH (a:Person {id: row.source})
                    MATCH (b:Person {id: row.target})
                    CREATE (a)-[:KNOWS]->(b)
                    """,
                    {"rows": batch},
                )
                batch = []
        if batch:
            graph.query(
                """
                UNWIND $rows AS row
                MATCH (a:Person {id: row.source})
                MATCH (b:Person {id: row.target})
                CREATE (a)-[:KNOWS]->(b)
                """,
                {"rows": batch},
            )
    elapsed = time.time() - start
    print(f"Edges: loaded {count} rows in {elapsed:.2f}s ({count/elapsed:.1f} rows/sec)")
    return count, elapsed


print("Creating index on Person.id ...")
graph.query("CREATE INDEX FOR (p:Person) ON (p.id)")

print("Loading nodes...")
node_count, node_time = load_nodes()

print("Loading edges...")
edge_count, edge_time = load_edges()

total_time = node_time + edge_time
print(f"\nTOTAL: {node_count} nodes + {edge_count} edges in {total_time:.2f}s")
print(f"Node throughput: {node_count/node_time:.1f} nodes/sec")
print(f"Edge throughput: {edge_count/edge_time:.1f} rels/sec")