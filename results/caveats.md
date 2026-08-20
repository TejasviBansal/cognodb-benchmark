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