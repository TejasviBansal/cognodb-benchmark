import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import random
import threading
import time
import itertools
from benchmarks.db_adapters import get_adapter, PLATFORMS

CONCURRENCY = 20          # number of concurrent clients
DURATION_SECONDS = 20     # how long to sustain load, per platform
READ_WRITE_RATIO = 0.8    # 80% reads, 20% writes
WRITE_ID_BASE = 1_000_000 # writes use a clearly separate ID range for easy cleanup

with open("results/start_nodes.json") as f:
    READ_POOL = json.load(f)

CYPHER_READ = "MATCH (p:Person {id: $id}) RETURN p"
CYPHER_WRITE = "CREATE (p:Person {id: $id, name: $name})"

AQL_READ = "FOR p IN Person FILTER p.id == @id RETURN p"
AQL_WRITE = "INSERT {id: @id, name: @name} INTO Person"


def worker(platform, adapter, stop_time, counter, lock, write_counter_start, results_list):
    ops = 0
    local_write_id = write_counter_start
    while time.time() < stop_time:
        is_read = random.random() < READ_WRITE_RATIO
        try:
            if is_read:
                node_id = random.choice(READ_POOL)
                if platform == "arangodb":
                    adapter.timed_query(AQL_READ, {"id": node_id})
                else:
                    adapter.timed_query(CYPHER_READ, {"id": node_id})
            else:
                local_write_id += 1
                params = {"id": local_write_id, "name": f"loadtest_{local_write_id}"}
                if platform == "arangodb":
                    adapter.timed_query(AQL_WRITE, params)
                else:
                    adapter.timed_query(CYPHER_WRITE, params)
            ops += 1
        except Exception:
            pass  # count only successful ops; failures are just not counted
    results_list.append(ops)


def cleanup_test_writes(platform):
    """Remove all nodes created during the write portion of the test."""
    adapter = get_adapter(platform)
    try:
        if platform == "arangodb":
            adapter.db.aql.execute(
                "FOR p IN Person FILTER p.id >= @base REMOVE p IN Person",
                bind_vars={"base": WRITE_ID_BASE},
            )
        elif platform == "falkordb":
            adapter.graph.query(
                "MATCH (p:Person) WHERE p.id >= $base DETACH DELETE p",
                {"base": WRITE_ID_BASE},
            )
        else:
            with adapter.driver.session() as session:
                session.run(
                    "MATCH (p:Person) WHERE p.id >= $base DETACH DELETE p",
                    {"base": WRITE_ID_BASE},
                )
    finally:
        adapter.close()


def run_benchmark():
    results = {}

    for platform in PLATFORMS:
        print(f"\n--- {platform} ---")
        try:
            adapters = [get_adapter(platform) for _ in range(CONCURRENCY)]

            stop_time = time.time() + DURATION_SECONDS
            threads = []
            results_list = []
            lock = threading.Lock()

            start = time.time()
            for i, adapter in enumerate(adapters):
                write_start = WRITE_ID_BASE + (i * 100_000)  # non-overlapping write ranges per thread
                t = threading.Thread(
                    target=worker,
                    args=(platform, adapter, stop_time, None, lock, write_start, results_list),
                )
                threads.append(t)
                t.start()

            for t in threads:
                t.join()
            elapsed = time.time() - start

            total_ops = sum(results_list)
            qps = total_ops / elapsed

            results[platform] = {
                "concurrency": CONCURRENCY,
                "duration_s": round(elapsed, 2),
                "total_ops": total_ops,
                "queries_per_second": round(qps, 2),
                "read_write_ratio": READ_WRITE_RATIO,
            }
            print(f"Total ops: {total_ops} in {elapsed:.2f}s -> {qps:.2f} ops/sec (concurrency={CONCURRENCY})")

            for adapter in adapters:
                adapter.close()

            print("Cleaning up test writes...")
            cleanup_test_writes(platform)

        except Exception as e:
            print(f"❌ {platform} failed: {e}")
            results[platform] = {"error": str(e)}

    with open("results/mixed_workload_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\nSaved results to results/mixed_workload_results.json")


if __name__ == "__main__":
    run_benchmark()