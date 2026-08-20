import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import numpy as np
from benchmarks.db_adapters import get_adapter, PLATFORMS

with open("results/start_nodes.json") as f:
    START_NODES = json.load(f)

# Cypher works for cognodb, neo4j, memgraph, falkordb (all Bolt/Cypher-family)
CYPHER_QUERIES = {
    1: "MATCH (a:Person {id: $id})-[:KNOWS]->(b) RETURN count(b) AS c",
    2: "MATCH (a:Person {id: $id})-[:KNOWS*2]->(b) RETURN count(b) AS c",
    3: "MATCH (a:Person {id: $id})-[:KNOWS*3]->(b) RETURN count(b) AS c",
}

# ArangoDB needs AQL instead
AQL_QUERIES = {
    1: "WITH Person FOR v IN 1..1 OUTBOUND CONCAT('Person/', @id) Knows RETURN v",
    2: "WITH Person FOR v IN 2..2 OUTBOUND CONCAT('Person/', @id) Knows RETURN v",
    3: "WITH Person FOR v IN 3..3 OUTBOUND CONCAT('Person/', @id) Knows RETURN v",
}


def run_hop_benchmark(adapter, platform, hop):
    latencies = []
    for node_id in START_NODES:
        if platform == "arangodb":
            ms = adapter.timed_query(AQL_QUERIES[hop], {"id": node_id})
        else:
            ms = adapter.timed_query(CYPHER_QUERIES[hop], {"id": node_id})
        latencies.append(ms)
    p50 = np.percentile(latencies, 50)
    p95 = np.percentile(latencies, 95)
    return p50, p95


results = {}

for platform in PLATFORMS:
    print(f"\n--- {platform} ---")
    results[platform] = {}
    try:
        adapter = get_adapter(platform)
        for hop in [1, 2, 3]:
            p50, p95 = run_hop_benchmark(adapter, platform, hop)
            results[platform][f"{hop}hop"] = {"p50_ms": round(p50, 2), "p95_ms": round(p95, 2)}
            print(f"{hop}-hop: p50={p50:.2f}ms  p95={p95:.2f}ms")
        adapter.close()
    except Exception as e:
        print(f"❌ {platform} failed: {e}")
        results[platform]["error"] = str(e)

# Save results
os.makedirs("results", exist_ok=True)
output_path = "results/traversal_results.json"
with open(output_path, "w") as f:
    json.dump(results, f, indent=2)

print(f"\nSaved results to {output_path}")