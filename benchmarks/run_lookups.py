import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import numpy as np
from benchmarks.db_adapters import get_adapter, PLATFORMS

with open("results/start_nodes.json") as f:
    START_NODES = json.load(f)

with open("results/lookup_prefixes.json") as f:
    PREFIXES = json.load(f)

CYPHER_POINT = "MATCH (p:Person {id: $id}) RETURN p"
CYPHER_FILTERED = "MATCH (p:Person) WHERE p.name STARTS WITH $prefix RETURN p"

AQL_POINT = "FOR p IN Person FILTER p.id == @id RETURN p"
AQL_FILTERED = "FOR p IN Person FILTER STARTS_WITH(p.name, @prefix) RETURN p"


def run_point_lookup(adapter, platform):
    latencies = []
    for node_id in START_NODES:
        if platform == "arangodb":
            ms = adapter.timed_query(AQL_POINT, {"id": node_id})
        else:
            ms = adapter.timed_query(CYPHER_POINT, {"id": node_id})
        latencies.append(ms)
    return np.percentile(latencies, 50), np.percentile(latencies, 95)


def run_filtered_lookup(adapter, platform):
    latencies = []
    for prefix in PREFIXES:
        if platform == "arangodb":
            ms = adapter.timed_query(AQL_FILTERED, {"prefix": prefix})
        else:
            ms = adapter.timed_query(CYPHER_FILTERED, {"prefix": prefix})
        latencies.append(ms)
    return np.percentile(latencies, 50), np.percentile(latencies, 95)


results = {}

for platform in PLATFORMS:
    print(f"\n--- {platform} ---")
    results[platform] = {}
    try:
        adapter = get_adapter(platform)

        p50, p95 = run_point_lookup(adapter, platform)
        results[platform]["point_lookup"] = {"p50_ms": round(p50, 2), "p95_ms": round(p95, 2)}
        print(f"Point lookup (indexed on id): p50={p50:.2f}ms  p95={p95:.2f}ms")

        p50, p95 = run_filtered_lookup(adapter, platform)
        results[platform]["filtered_lookup"] = {"p50_ms": round(p50, 2), "p95_ms": round(p95, 2)}
        print(f"Filtered lookup (unindexed name prefix): p50={p50:.2f}ms  p95={p95:.2f}ms")

        adapter.close()
    except Exception as e:
        print(f"❌ {platform} failed: {e}")
        results[platform]["error"] = str(e)

with open("results/lookup_results.json", "w") as f:
    json.dump(results, f, indent=2)

print("\nSaved results to results/lookup_results.json")