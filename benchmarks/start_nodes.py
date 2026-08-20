import random
import json

random.seed(123)  # different seed from dataset generation, but still reproducible
NUM_NODES = 20000
SAMPLE_SIZE = 100  # per the assignment's "≥100 iterations" suggestion

start_nodes = random.sample(range(NUM_NODES), SAMPLE_SIZE)

with open("results/start_nodes.json", "w") as f:
    json.dump(start_nodes, f)

print(f"Generated {len(start_nodes)} fixed start node IDs, saved to results/start_nodes.json")