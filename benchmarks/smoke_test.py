import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from benchmarks.db_adapters import get_adapter, PLATFORMS

QUERIES = {
    "cognodb": "RETURN 1",
    "neo4j": "RETURN 1",
    "memgraph": "RETURN 1",
    "arangodb": "RETURN 1",
    "falkordb": "RETURN 1",
}

for platform in PLATFORMS:
    try:
        adapter = get_adapter(platform)
        ms = adapter.timed_query(QUERIES[platform])
        print(f"✅ {platform}: {ms:.2f} ms")
        adapter.close()
    except Exception as e:
        print(f"❌ {platform}: {e}")