\## CognoDB

\- Ingest: 20,000 nodes @ 444.7 nodes/sec, 160,000 relationships @ 422.0 rels/sec, total 424.09s

\- One transient connection reset during edge loading (ConnectionResetError), auto-retried by the neo4j driver and recovered successfully. Likely free-tier connection throttling under sustained write load.

\## Environment note (Windows)
\- Neo4j AuraDB connection initially failed with SSLCertVerificationError due to Python's bundled certifi trust store missing the correct intermediate chain for SSL.com-issued certs. Fixed by installing pip-system-certs, which makes Python use the Windows OS certificate store instead.

\## Neo4j AuraDB Free
- Ingest: 20,000 nodes @ 2354.8 nodes/sec, 160,000 relationships @ 2442.7 rels/sec, total 73.99s
- No connection errors or retries during load (unlike CognoDB, which had one transient reset)
- Notably faster ingest throughput than CognoDB free tier (~5-6x) despite both being "free" tiers — worth investigating in analysis (likely due to underlying infra differences, not something CognoDB does wrong)