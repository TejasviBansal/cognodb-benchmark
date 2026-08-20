import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import numpy as np
from benchmarks.db_adapters import get_adapter, PLATFORMS

ITERATIONS = 100

CYPHER_COUNT = "MATCH (p:Person) RETURN count(p) AS c"
CYPHER_AVG_DEGREE = """
MATCH (p:Person)
OPTIONAL MATCH (p)-[r:KNOWS]->()
RETURN p.id AS id, count(r) AS out_degree
"""

AQL_COUNT = "RETURN LENGTH(Person)"
AQL_AVG_DEGREE = """
FOR p IN Person
    LET out_degree = LENGTH(FOR v IN 1..1 OUTBOUND p Knows RETURN v)
    RETURN {id: p.id, out_degree: out_degree}
"""


def run_agg(adapter, platform, query_key):
    latencies = []
    for _ in range(ITERATIONS):
        if platform == "arangodb":
            q = AQL_COUNT if query_key == "count" else AQL_AVG_DEGREE
        else:
            q = CYPHER_COUNT if query_key == "count" else CYPHER_AVG_DEGREE
        ms = adapter.timed_query(q)
        latencies.append(ms)
    return np.percentile(latencies, 50), np.percentile(latencies, 95)


results = {}

for platform in PLATFORMS:
    print(f"\n--- {platform} ---")
    results[platform] = {}
    try:
        adapter = get_adapter(platform)

        p50, p95 = run_agg(adapter, platform, "count")
        results[platform]["count"] = {"p50_ms": round(p50, 2), "p95_ms": round(p95, 2)}
        print(f"Count all Person nodes: p50={p50:.2f}ms  p95={p95:.2f}ms")

        p50, p95 = run_agg(adapter, platform, "avg_degree")
        results[platform]["avg_out_degree"] = {"p50_ms": round(p50, 2), "p95_ms": round(p95, 2)}
        print(f"Avg out-degree (group-by-style): p50={p50:.2f}ms  p95={p95:.2f}ms")

        adapter.close()
    except Exception as e:
        print(f"❌ {platform} failed: {e}")
        results[platform]["error"] = str(e)

with open("results/aggregation_results.json", "w") as f:
    json.dump(results, f, indent=2)

print("\nSaved results to results/aggregation_results.json")