import csv
import random
import json

random.seed(456)

with open("data/nodes.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    names = [row["name"] for row in reader]

sample_names = random.sample(names, 100)
# Use first 3 characters of each sampled name as the filter prefix
prefixes = [name[:3] for name in sample_names]

with open("results/lookup_prefixes.json", "w") as f:
    json.dump(prefixes, f)

print(f"Generated {len(prefixes)} name prefixes, saved to results/lookup_prefixes.json")