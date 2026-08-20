from arango import ArangoClient
from dotenv import load_dotenv
import csv
import time
import os

load_dotenv()

uri = os.environ["ARANGO_URI"]
user = os.environ["ARANGO_USER"]
password = os.environ["ARANGO_PASSWORD"]

client = ArangoClient(hosts=uri)
sys_db = client.db("_system", username=user, password=password)

DB_NAME = "benchmark"
BATCH_SIZE = 1000

# Create a dedicated database if it doesn't exist
if not sys_db.has_database(DB_NAME):
    sys_db.create_database(DB_NAME)

db = client.db(DB_NAME, username=user, password=password)

# Create vertex collection (nodes) and edge collection (relationships)
if not db.has_collection("Person"):
    db.create_collection("Person")
if not db.has_collection("Knows"):
    db.create_collection("Knows", edge=True)

person_collection = db.collection("Person")
knows_collection = db.collection("Knows")

# Create an index on id for fast lookups
person_collection.add_index({"type": "persistent", "fields": ["id"], "unique": True})


def load_nodes():
    start = time.time()
    count = 0
    with open("data/nodes.csv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        batch = []
        for row in reader:
            batch.append({"_key": row["id"], "id": int(row["id"]), "name": row["name"]})
            count += 1
            if len(batch) == BATCH_SIZE:
                person_collection.insert_many(batch)
                batch = []
        if batch:
            person_collection.insert_many(batch)
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
            batch.append({
                "_from": f"Person/{row['source']}",
                "_to": f"Person/{row['target']}",
            })
            count += 1
            if len(batch) == BATCH_SIZE:
                knows_collection.insert_many(batch)
                batch = []
        if batch:
            knows_collection.insert_many(batch)
    elapsed = time.time() - start
    print(f"Edges: loaded {count} rows in {elapsed:.2f}s ({count/elapsed:.1f} rows/sec)")
    return count, elapsed


print("Loading nodes...")
node_count, node_time = load_nodes()

print("Loading edges...")
edge_count, edge_time = load_edges()

total_time = node_time + edge_time
print(f"\nTOTAL: {node_count} nodes + {edge_count} edges in {total_time:.2f}s")
print(f"Node throughput: {node_count/node_time:.1f} nodes/sec")
print(f"Edge throughput: {edge_count/edge_time:.1f} rels/sec")