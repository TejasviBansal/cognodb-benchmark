import csv
import random
from faker import Faker

fake = Faker()
random.seed(42)  # reproducible: same seed = same graph every time

NUM_NODES = 20000
AVG_EDGES_PER_NODE = 8   # ~20,000 * 8 = 160,000 relationships

# --- Generate nodes ---
with open("data/nodes.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["id", "name"])
    for i in range(NUM_NODES):
        writer.writerow([i, fake.name()])

print(f"Generated {NUM_NODES} nodes.")

# --- Generate edges with a power-law-ish structure ---
# A small number of "hub" nodes get disproportionately more connections,
# mimicking real social network structure.
hub_nodes = random.sample(range(NUM_NODES), k=int(NUM_NODES * 0.02))  # top 2% are hubs

edges = set()
target_edges = NUM_NODES * AVG_EDGES_PER_NODE

while len(edges) < target_edges:
    if random.random() < 0.3 and hub_nodes:
        source = random.choice(hub_nodes)
    else:
        source = random.randint(0, NUM_NODES - 1)
    target = random.randint(0, NUM_NODES - 1)
    if source != target:
        edges.add((source, target))

with open("data/edges.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["source", "target"])
    for source, target in edges:
        writer.writerow([source, target])

print(f"Generated {len(edges)} relationships.")