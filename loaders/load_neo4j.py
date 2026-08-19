from neo4j import GraphDatabase
from dotenv import load_dotenv
import csv
import time
import os

load_dotenv()

uri = os.environ["NEO4J_URI"]
user = os.environ["NEO4J_USER"]
password = os.environ["NEO4J_PASSWORD"]

driver = GraphDatabase.driver(uri, auth=(user, password))

BATCH_SIZE = 1000


def load_nodes(tx, batch):
    tx.run(
        "UNWIND $rows AS row CREATE (p:Person {id: toInteger(row.id), name: row.name})",
        rows=batch,
    )


def load_edges(tx, batch):
    tx.run(
        """
        UNWIND $rows AS row
        MATCH (a:Person {id: toInteger(row.source)})
        MATCH (b:Person {id: toInteger(row.target)})
        CREATE (a)-[:KNOWS]->(b)
        """,
        rows=batch,
    )


def create_index(tx):
    tx.run("CREATE INDEX person_id_index IF NOT EXISTS FOR (p:Person) ON (p.id)")


def run_batched(session, filepath, batch_fn, label):
    start = time.time()
    count = 0
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        batch = []
        for row in reader:
            batch.append(row)
            count += 1
            if len(batch) == BATCH_SIZE:
                session.execute_write(batch_fn, batch)
                batch = []
        if batch:
            session.execute_write(batch_fn, batch)
    elapsed = time.time() - start
    print(f"{label}: loaded {count} rows in {elapsed:.2f}s ({count/elapsed:.1f} rows/sec)")
    return count, elapsed


with driver.session() as session:
    print("Creating index on Person.id ...")
    session.execute_write(create_index)

    print("Loading nodes...")
    node_count, node_time = run_batched(session, "data/nodes.csv", load_nodes, "Nodes")

    print("Loading edges...")
    edge_count, edge_time = run_batched(session, "data/edges.csv", load_edges, "Edges")

    total_time = node_time + edge_time
    print(f"\nTOTAL: {node_count} nodes + {edge_count} edges in {total_time:.2f}s")
    print(f"Node throughput: {node_count/node_time:.1f} nodes/sec")
    print(f"Edge throughput: {edge_count/edge_time:.1f} rels/sec")

driver.close()