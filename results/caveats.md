\## CognoDB

\- Ingest: 20,000 nodes @ 444.7 nodes/sec, 160,000 relationships @ 422.0 rels/sec, total 424.09s

\- One transient connection reset during edge loading (ConnectionResetError), auto-retried by the neo4j driver and recovered successfully. Likely free-tier connection throttling under sustained write load.

\## Environment note (Windows)
\- Neo4j AuraDB connection initially failed with SSLCertVerificationError due to Python's bundled certifi trust store missing the correct intermediate chain for SSL.com-issued certs. Fixed by installing pip-system-certs, which makes Python use the Windows OS certificate store instead.

\## Neo4j AuraDB Free
- Ingest: 20,000 nodes @ 2354.8 nodes/sec, 160,000 relationships @ 2442.7 rels/sec, total 73.99s
- No connection errors or retries during load (unlike CognoDB, which had one transient reset)
- Notably faster ingest throughput than CognoDB free tier (~5-6x) despite both being "free" tiers — worth investigating in analysis (likely due to underlying infra differences, not something CognoDB does wrong)

## Memgraph Cloud
- Free tier is a 14-day trial (not indefinite like CognoDB/Neo4j Aura)
- Smallest free-tier size available: 2 GB RAM / 2 CPU — significantly larger than CognoDB's 0.5 vCPU/256MB and likely larger than Neo4j Aura Free. Memgraph does not appear to offer a smaller free option (1GB tier appears to require payment). This is a genuine resource mismatch across platforms, documented here per the assignment's fairness requirement — results should be interpreted with this in mind, especially for ingest throughput and concurrency numbers.

## Memgraph Cloud (query language differences)
- Index syntax differs from Neo4j/CognoDB: `CREATE INDEX ON :Person(id)` instead of `CREATE INDEX ... FOR (p:Person) ON (p.id)`
- Memgraph does not allow index creation inside an explicit/wrapped transaction (execute_write) — must run as a direct auto-committing statement via session.run(), unlike Neo4j and CognoDB which accept both.

## Memgraph Cloud (ingest results)
- Ingest: 20,000 nodes @ 1582.6 nodes/sec, 160,000 relationships @ 1660.1 rels/sec, total 109.02s
- Slower than Neo4j Aura despite larger instance size (2GB/2CPU vs Aura's smaller free tier) — possibly network latency to Frankfurt region, or Memgraph's durability/persistence settings; worth investigating in final analysis

## ArangoDB
- Deployed via ArangoDB Oasis, AWS Asia Pacific (Mumbai) region
- Free trial expires in 14 days (same trial-based model as Memgraph Cloud — neither CognoDB nor Neo4j Aura Free have an expiry)

## ArangoDB (ingest results)
- Ingest: 20,000 nodes @ 11916.2 nodes/sec, 160,000 relationships @ 8076.4 rels/sec, total 21.49s
- By far the fastest ingest of all platforms tested so far — likely due to document-batch insert_many() being more efficient than Cypher UNWIND transactions, and/or AWS Mumbai region proximity reducing latency

## FalkorDB Cloud (ingest results)
- Ingest: 20,000 nodes @ 19971.7 nodes/sec, 160,000 relationships @ 7979.0 rels/sec, total 21.05s
- Fastest node ingest of all 5 platforms tested
- No connection or TLS issues; self-selected password (not provider-generated)
- Redis-based architecture, Cypher-like query syntax via FalkorDB Python client (not the neo4j driver)

## Query language note
- AQL traversals require an explicit `WITH <collection>` declaration before the FOR loop; Cypher (used by CognoDB/Neo4j/Memgraph/FalkorDB) infers this automatically.

## Traversal results observations
- CognoDB latency is flat (~277ms) across all hop depths — likely dominated by network/connection overhead rather than actual traversal cost, consistent with it being the most geographically distant/smallest instance
- ArangoDB shows a p95 spike on 3-hop (360ms vs ~40ms p50) — worth noting as variance, possibly a cold-cache effect on deeper traversals
- FalkorDB fastest and most consistent across all hop depths (~35ms flat)

## Lookup results observations
- Indexed (id) vs unindexed (name prefix) lookup gap is visible on every platform, most pronounced on CognoDB: p95 goes from 282ms (indexed) to 564ms (unindexed) — a ~2x degradation from the missing index on `name`
- Only `id` was indexed on all 5 platforms (created in each loader script); `name` was left unindexed deliberately to produce this comparison

## Aggregation results observations
- Simple count queries are fast and fairly close across platforms (35-273ms range)
- Row-returning aggregation (avg out-degree, 20,000 rows returned) shows much wider divergence:
  - CognoDB: 273ms -> 2205ms p50 (~8x slower) — likely smallest instance tier + result serialization/network cost compounding
  - ArangoDB: 39ms -> 1451ms p50 (~37x slower) — larger relative jump than other platforms, worth further investigation; possibly the nested FOR subquery pattern used for AQL degree calculation is less optimized than Cypher's OPTIONAL MATCH
  - Neo4j and FalkorDB scaled best proportionally (~2.5x and ~8.4x respectively, but starting from a much lower base)
- This suggests result-set size matters more for some platforms than others — worth highlighting as a key finding in the analysis section