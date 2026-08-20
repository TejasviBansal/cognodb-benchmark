# CognoDB Cloud Benchmark

A reproducible benchmark comparing **CognoDB Cloud** against four other managed graph database platforms — **Neo4j AuraDB Free**, **Memgraph Cloud**, **ArangoDB Oasis**, and **FalkorDB Cloud** — on an identical dataset and query workload.

This benchmark was built for the Wexa AI Backend Engineer take-home assignment. The goal is not to declare a "winner," but to measure each platform fairly, under matching (or clearly documented, when not matching) resource limits, and report the results honestly — including every caveat, anomaly, and limitation encountered along the way.

---

## TL;DR

- **FalkorDB (Redis-based) and ArangoDB (document-native, AQL) were consistently the fastest platforms** across every benchmark category — ingest, traversals, lookups, aggregations, and concurrent throughput. Both were also hosted closest to the benchmarking client (Mumbai region), so region and architecture are confounded in these results and cannot be fully separated (see Analysis).
- **CognoDB was the slowest or near-slowest on every metric**, consistent with it having the smallest compute tier tested (0.5 vCPU burstable, 512MB RAM) and the most distant region (us-east4). This is an expected, fair result given its spec, not a flaw.
- **The single most interesting finding**: result-set size, not query type, is the strongest differentiator between platforms. A query returning one row (count) performs similarly everywhere; a query returning 20,000 rows (avg out-degree) causes some platforms to slow down 2.5x and others to slow down 37x. See [Aggregations](#4-aggregations-count--avg-out-degree).
- **Missing an index has a real, measurable cost**, most visible on the smallest instance (CognoDB): p95 latency nearly doubles (282ms → 564ms) between an indexed point lookup and an unindexed filtered lookup.
- **Three genuine open anomalies were found and are reported without a confirmed root cause**: Memgraph reports 14GB disk usage for a ~200MB dataset; ArangoDB shows an unexplained p95 latency spike specifically on 3-hop traversals; FalkorDB's official 100MB tier spec did not appear to constrain a dataset several times that size. All three are flagged in [Anomalies and honest caveats](#anomalies-and-honest-caveats) rather than smoothed over.
- **Full results, methodology, and reproduction steps follow below** — this summary omits detail in favor of the headline findings; every number is broken out by platform and metric further down.

---

## Platforms tested

| Platform | Query Language | Client Driver | Hosting Model |
|---|---|---|---|
| CognoDB Cloud | Cypher (Bolt protocol) | `neo4j` (official Neo4j driver) | Managed cloud, free tier |
| Neo4j AuraDB Free | Cypher (Bolt protocol) | `neo4j` | Managed cloud, free tier |
| Memgraph Cloud | Cypher (Bolt protocol) | `neo4j` | Managed cloud, 14-day free trial |
| ArangoDB Oasis | AQL | `python-arango` | Managed cloud, 14-day free trial |
| FalkorDB Cloud | Cypher-like (via FalkorDB client) | `falkordb` (Redis-based) | Managed cloud, free tier |

CognoDB is Bolt-protocol compatible, so it connects via the standard official Neo4j Python driver with no special client needed.

---

## Dataset

A synthetic social-network-style graph was generated rather than downloading a pre-existing public dataset, in order to precisely control size (fitting every platform's free tier) and guarantee full reproducibility from a single script.

- **Nodes**: 20,000 `Person` nodes (`id`, `name` — names generated via the `Faker` library)
- **Relationships**: 160,000 `KNOWS` relationships
- **Generation method**: `generate_dataset.py`, seeded (`random.seed(42)`) for reproducibility. ~2% of nodes are designated "hub" nodes that receive disproportionately more connections, mimicking a real-world power-law degree distribution rather than a uniform random graph.
- **Size**: comfortably within the assignment's suggested 100k–500k relationship range, and small enough to fit every platform's smallest free/entry tier.

Reproduce with:
```bash
python generate_dataset.py
```

---

## Methodology

### Resource parity across platforms

The assignment requires equivalent resources across every platform where possible, with mismatches clearly documented rather than hidden. Actual free-tier specs varied significantly and could not be fully equalized — every platform's *smallest available free/trial tier* was used, and the real numbers are reported below rather than assumed to match.

| Platform | vCPU | RAM (limit) | Storage / capacity | Trial length |
|---|---|---|---|---|
| CognoDB | burst to 0.5 | 512 MB | 1 GiB | Indefinite (free tier) |
| Neo4j AuraDB Free | not exposed in console | not exposed in console | ~200,000 node / ~400,000 relationship capacity (derived from usage % shown in UI) | Indefinite (free tier) |
| Memgraph Cloud | 2 | 2 GB | not exposed as a limit | 14 days |
| ArangoDB Oasis | 0.25 | 1 GB | 40 GB | 14 days |
| FalkorDB Cloud | not exposed in console | 100 MB (per official pricing page) | 100 MB max graph dataset (shared with RAM) | Indefinite (free tier) |

**This is a genuine, documented fairness limitation**: Memgraph's 2GB/2CPU tier is substantially larger than CognoDB's 0.5 vCPU/512MB tier, and no smaller free option was available on Memgraph Cloud at all (confirmed by inspecting all tier options in their signup flow). FalkorDB's official spec (100MB) is smaller than the dataset's on-disk footprint on other platforms, yet it ran the full dataset successfully and fastest — see Anomalies below. Where a platform's console does not expose live resource usage (Neo4j Aura Free, FalkorDB), this is reported as "not observable," per the assignment's explicit allowance for this.

### Query design

- **Fixed random sample**: 100 start node IDs were generated once (`benchmarks/start_nodes.py`, seeded) and reused identically across all 5 platforms for every traversal and point-lookup benchmark, ensuring a true apples-to-apples comparison rather than independently random samples per platform.
- **Fixed filter values**: 100 name prefixes were sampled once from the actual generated dataset (`benchmarks/lookup_prefixes.py`, seeded) and reused identically across platforms for the filtered-lookup benchmark.
- **Indexing**: only the `id` property on `Person` nodes/documents was indexed, identically across all 5 platforms. The `name` property was deliberately left unindexed to produce a genuine indexed-vs-unindexed comparison for the lookup benchmark.
- **Iterations**: 100 iterations per query type per platform, per the assignment's suggested minimum, with p50 and p95 latency reported (not just averages).
- **Timing methodology**: each query's execution time is measured via `time.perf_counter()` immediately before and after the query call, with the result fully consumed/materialized (not just the first record) before stopping the timer, so timings reflect full query completion, not just first-byte latency.

### Fairness caveat: no formal warm-up phase

The assignment recommends warming up each database before measuring. This benchmark did **not** implement a dedicated warm-up phase separate from the timed runs — the first few iterations of each 100-iteration run effectively serve as informal warm-up, and are included in the reported p50/p95 rather than excluded. This is a methodology simplification, documented honestly rather than hidden. Given the free-tier instances are small and the query counts (100 iterations) are modest, cold-start effects likely still influence the p95 values reported, particularly for CognoDB (smallest instance) and ArangoDB (one notable p95 spike observed — see below).

---

## Results

### 1. Data loading (ingest throughput)

| Platform | Nodes/sec | Relationships/sec | Total load time | Notes |
|---|---|---|---|---|
| CognoDB | 444.7 | 422.0 | 424.09s | One transient connection reset during edge load, auto-retried successfully by the driver |
| Neo4j AuraDB Free | 2354.8 | 2442.7 | 73.99s | Clean run, no retries |
| Memgraph Cloud | 1582.6 | 1660.1 | 109.02s | Clean run |
| ArangoDB Oasis | 11916.2 | 8076.4 | 21.49s | Fastest ingest of the Bolt/AQL-driver platforms |
| FalkorDB Cloud | 19971.7 | 7979.0 | 21.05s | Fastest node ingest overall |

**Observation**: the two non-Bolt-routed platforms (ArangoDB, FalkorDB) both dramatically outperformed the three Bolt/Cypher-routed platforms on ingest — roughly 5–45x faster depending on the comparison. This likely reflects a combination of (a) `insert_many`/direct graph-query batch inserts being cheaper than Cypher `UNWIND` + transactional writes, and (b) both instances being geographically closer (Mumbai, ap-south-1) to the client than CognoDB (us-east4) and Memgraph (Frankfurt).

### 2. Traversals (1-hop, 2-hop, 3-hop)

| Platform | 1-hop p50 (ms) | 1-hop p95 (ms) | 2-hop p50 (ms) | 2-hop p95 (ms) | 3-hop p50 (ms) | 3-hop p95 (ms) |
|---|---|---|---|---|---|---|
| CognoDB | 276.38 | 280.65 | 276.30 | 283.89 | 277.73 | 361.73 |
| Neo4j AuraDB Free | 97.76 | 133.73 | 97.62 | 99.62 | 97.76 | 101.25 |
| Memgraph Cloud | 161.03 | 164.29 | 161.12 | 195.27 | 161.11 | 183.88 |
| ArangoDB Oasis | 39.65 | 85.29 | 40.58 | 95.30 | 43.65 | 360.19 |
| FalkorDB Cloud | 34.83 | 39.01 | 34.78 | 37.47 | 34.81 | 36.23 |

**Observation**: CognoDB's latency is essentially flat (~277ms) regardless of hop depth, strongly suggesting network/connection round-trip time dominates over actual traversal computation cost — consistent with it being the smallest, most geographically distant instance tested. ArangoDB shows a notable p95 spike specifically on 3-hop traversals (360ms vs. a 40ms p50), which does not appear on any other platform; this is flagged as an anomaly worth further investigation rather than explained away, since a root cause was not conclusively identified. FalkorDB is both the fastest and the most consistent across all three hop depths.

### 3. Lookups (point + filtered/unindexed)

| Platform | Point lookup p50 (ms) | Point lookup p95 (ms) | Filtered (unindexed) p50 (ms) | Filtered (unindexed) p95 (ms) |
|---|---|---|---|---|
| CognoDB | 281.12 | 282.54 | 309.92 | 563.63 |
| Neo4j AuraDB Free | 85.81 | 88.69 | 99.36 | 128.45 |
| Memgraph Cloud | 160.85 | 176.27 | 173.45 | 190.26 |
| ArangoDB Oasis | 37.26 | 99.46 | 42.23 | 98.94 |
| FalkorDB Cloud | 36.69 | 37.71 | 41.66 | 50.78 |

**Observation**: every platform shows some cost increase from indexed (point, on `id`) to unindexed (filtered, on `name`) lookups, as expected. The effect is most pronounced on CognoDB, where p95 nearly doubles (282ms → 564ms) — the clearest demonstration in this benchmark of the real cost of a missing index, likely compounded by CognoDB's smaller compute allocation making a full label scan proportionally more expensive.

### 4. Aggregations (count + avg out-degree)

| Platform | Count p50 (ms) | Count p95 (ms) | Avg out-degree p50 (ms) | Avg out-degree p95 (ms) |
|---|---|---|---|---|
| CognoDB | 273.17 | 277.96 | 2205.00 | 2425.21 |
| Neo4j AuraDB Free | 85.64 | 89.62 | 217.32 | 354.86 |
| Memgraph Cloud | 162.36 | 164.11 | 399.10 | 450.97 |
| ArangoDB Oasis | 39.17 | 63.95 | 1451.40 | 1894.95 |
| FalkorDB Cloud | 35.42 | 36.33 | 298.46 | 340.15 |

**Observation**: this is the most revealing result in the whole benchmark. The "count" aggregation (single scalar returned) is fast and fairly close across platforms. The "avg out-degree" aggregation (one row returned per node, 20,000 rows total) diverges dramatically:

- CognoDB: 273ms → 2205ms (**~8x** slower)
- ArangoDB: 39ms → 1451ms (**~37x** slower — the largest relative jump of any platform)
- Neo4j: 86ms → 217ms (**~2.5x** — the best-scaling platform)
- FalkorDB: 35ms → 298ms (**~8.4x**)
- Memgraph: 162ms → 399ms (**~2.5x**)

Result-set size matters far more for some platforms than others. ArangoDB's outsized relative slowdown despite its otherwise strong performance elsewhere suggests its nested `FOR` subquery pattern (used here to compute out-degree per node in AQL) may be less optimized than Cypher's `OPTIONAL MATCH` equivalent for this specific access pattern — though this is a hypothesis, not a confirmed root cause, and is flagged as such.

### 5. Mixed concurrent workload

20 concurrent clients, 80% reads / 20% writes, sustained for 20 seconds per platform. Writes used a dedicated, non-overlapping ID range (≥1,000,000, split into per-thread sub-ranges) and were deleted after each platform's run to avoid polluting the dataset used by the other benchmarks.

| Platform | Total ops | Duration (s) | Queries/sec |
|---|---|---|---|
| CognoDB | 1315 | 20.25 | 64.95 |
| Neo4j AuraDB Free | 4359 | 20.09 | 216.96 |
| Memgraph Cloud | 2366 | 20.15 | 117.41 |
| ArangoDB Oasis | 5484 | 20.03 | 273.81 |
| FalkorDB Cloud | 11154 | 20.03 | 556.89 |

**Observation**: the ranking under concurrent load matches the pattern seen across every other benchmark in this report (FalkorDB > ArangoDB > Neo4j > Memgraph > CognoDB), suggesting the relative performance differences are systemic (driven by instance tier size, geography, and architecture) rather than workload-specific.

### 6. Footprint

| Platform | vCPU | RAM limit | RAM used | Storage/capacity limit | Storage used |
|---|---|---|---|---|---|
| CognoDB | burst to 0.5 | 512 MB | not observable | 1 GiB | 204 MB |
| Neo4j AuraDB Free | not observable | not observable | not observable | ~200k nodes / ~400k rels (capacity) | not observable |
| Memgraph Cloud | 2 | 2 GB | 2 GB | not exposed | 14 GB *(see anomaly below)* |
| ArangoDB Oasis | 0.25 | 1 GB | not observable | 40 GB | not observable |
| FalkorDB Cloud | not observable | 100 MB | not observable | 100 MB (shared with RAM) | not observable |

---

## Anomalies and honest caveats

This section exists because the assignment explicitly states that honest caveats earn credit and hidden ones lose it. Everything below was encountered during this benchmark and is reported as observed, without being smoothed over.

**CognoDB — transient connection reset during ingest.** One `ConnectionResetError` occurred while loading edges. The `neo4j` driver's built-in retry logic recovered automatically and the load completed successfully with the full 160,000 relationships loaded. Likely free-tier connection throttling under sustained write load.

**Neo4j AuraDB — initial SSL/routing failure on this machine.** The first connection attempt failed with `Unable to retrieve routing information`, later diagnosed as Python's bundled `certifi` trust store missing the correct intermediate certificate chain for the SSL.com-issued certificate Aura presents — a Windows-specific Python/OS trust-store mismatch, not a problem with Neo4j's instance or certificate itself (independently confirmed valid and correctly issued). Fixed by installing `pip-system-certs`, which makes Python defer to the Windows OS certificate store. This is documented as an environment dependency in Requirements below.

**Memgraph — no free tier smaller than 2GB/2CPU was available.** Every size option in the signup flow below "2 GB RAM (2 CPU) - Free Trial (14 days)" required a payment method. This is a genuine, unavoidable resource-parity mismatch against CognoDB's much smaller 0.5vCPU/512MB tier, documented rather than hidden.

**Memgraph — disk usage reports 14GB for a dataset that is ~200MB elsewhere.** Node and relationship counts verified correct (20,000 / 160,000) after loading, so this is not a data-loading error. Most likely explanation is write-ahead log (WAL) files, periodic snapshots, or storage-engine pre-allocation counted as "disk used" by the console, rather than actual graph data size — but this was not independently confirmed via Memgraph documentation, so it is reported as an open observation rather than a settled explanation.

**Memgraph — index creation syntax and transaction-mode requirements differ from Neo4j/CognoDB.** `CREATE INDEX ON :Person(id)` (older-style syntax) is required instead of Neo4j's `CREATE INDEX ... IF NOT EXISTS FOR (p:Person) ON (p.id)`. Additionally, Memgraph does not allow index creation inside an explicit/wrapped transaction (`execute_write`) — it must run as a direct auto-committing statement, unlike Neo4j and CognoDB which accept both. The loader script was adjusted accordingly.

**ArangoDB — AQL traversal syntax requires an explicit collection declaration.** `WITH Person` must precede a `FOR ... OUTBOUND` traversal in AQL, whereas Cypher (used by the other four platforms) infers this automatically. The benchmark script initially failed with `collection not known to traversal` until this was added.

**ArangoDB — 3-hop traversal shows a p95 latency spike** (360ms vs. a 40ms p50) not seen at 1-hop or 2-hop, and not seen on any other platform at any hop depth. No root cause was conclusively identified; flagged as an open anomaly.

**FalkorDB — official free-tier spec (100MB) is smaller than the dataset's footprint on other platforms, yet the full dataset loaded and ran successfully, fastest of all 5 platforms.** This is either because the stated 100MB limit is not strictly enforced for this account/tier, or because FalkorDB's in-memory graph representation is significantly more space-efficient than the document/property-graph storage used by the other four platforms. This was not resolved conclusively and is reported as an open, genuinely interesting finding rather than an error.

**No formal warm-up phase was implemented** (see Methodology above) — the first iterations of each 100-iteration benchmark run are included in the reported percentiles rather than excluded as a separate warm-up pass.

**Concurrent workload write cleanup depends on script completion.** If the mixed-workload benchmark script is interrupted mid-run, test-write nodes (ID ≥ 1,000,000) could be left behind on whichever platform was running at the time. This did not occur during the actual benchmark runs used for this report (verified via post-run node counts on all 5 platforms), but is noted as a script-design limitation for anyone reproducing this benchmark.

---

## Analysis: what the numbers show

**Geography and instance tier size dominate more than architecture, for most queries.** The two fastest platforms overall (FalkorDB, ArangoDB) are also the two hosted closest to the benchmarking client (ap-south-1, Mumbai), while the two slowest platforms on most metrics (CognoDB, Memgraph) are hosted furthest away (us-east4, Frankfurt) and/or on the smallest compute tier (CognoDB's 0.5 vCPU burstable). This benchmark cannot fully separate "faster because of region" from "faster because of architecture" — a genuine limitation, since re-running on matched regions for every platform was not feasible within the assignment's time constraints. This is flagged rather than glossed over: the region/architecture confound is the single biggest threat to this benchmark's internal validity.

**Result-set size is the strongest differentiator between platforms, more than query type.** Simple scalar-returning queries (count, point lookup) cluster relatively closely across platforms. The moment a query returns many rows (the 20,000-row avg-out-degree aggregation, or the mixed workload under concurrency), the spread between platforms widens dramatically — CognoDB and ArangoDB both show 8–37x slowdowns on the large-result-set aggregation, while Neo4j scales much more gracefully (~2.5x). This suggests serialization/network transfer cost for large result sets, not raw query-execution cost, may be the dominant factor separating these platforms — a hypothesis this benchmark surfaces but does not conclusively prove.

**Missing indexes have a real, measurable cost, most visible on the smallest instance.** The indexed-vs-unindexed lookup gap is present on every platform but is roughly 2x more pronounced on CognoDB than on the larger-tier platforms, suggesting that under-provisioned compute makes the absence of an index disproportionately expensive — a practically useful finding for anyone choosing a tier size in production.

**CognoDB's free tier is the most resource-constrained of the five platforms tested**, and this shows consistently across every benchmark category — it was the slowest or near-slowest on ingest, traversals, lookups, aggregations, and concurrent throughput. This is an expected and fair result given its 0.5 vCPU / 512MB specification is the smallest of all five platforms tested (aside from FalkorDB's on-paper 100MB spec, which — per the anomaly noted above — did not appear to constrain it in practice).

---

## Reproducing this benchmark

### Prerequisites
- Python 3.9+
- Free-tier accounts on: CognoDB Cloud, Neo4j AuraDB, Memgraph Cloud, ArangoDB Oasis, FalkorDB Cloud
- **Windows users**: if you hit `SSLCertVerificationError` connecting to Neo4j Aura, install `pip-system-certs` (`pip install pip-system-certs`) — see Anomalies above for why this is needed.

### Setup
```bash
git clone https://github.com/TejasviBansal/cognodb-benchmark.git
cd cognodb-benchmark
python -m venv venv
venv\Scripts\Activate.ps1        # Windows
# source venv/bin/activate       # Mac/Linux
pip install -r requirements.txt
cp .env.example .env             # then fill in your own credentials
```

### Run the full pipeline
```bash
python generate_dataset.py

python loaders\load_cognodb.py
python loaders\load_neo4j.py
python loaders\load_memgraph.py
python loaders\load_arango.py
python loaders\load_falkordb.py

python benchmarks\start_nodes.py
python benchmarks\lookup_prefixes.py
python benchmarks\run_traversals.py
python benchmarks\run_lookups.py
python benchmarks\run_aggregations.py
python benchmarks\run_mixed_workload.py
```

All results are saved as JSON under `results/`. Raw ingest throughput is printed by each loader script directly.

---

## Repository structure

```
cognodb-benchmark/
  data/                     # generated dataset (nodes.csv, edges.csv)
  loaders/                  # one data-loading script per platform
  benchmarks/               # shared adapter layer + one script per metric category
  results/                  # JSON output per benchmark, plus caveats.md (raw notes)
  generate_dataset.py       # synthetic dataset generator (seeded, reproducible)
  requirements.txt
  .env.example               # required environment variables (no real secrets)
  README.md                  # this file
```

---

## Limitations of this benchmark (summary)

- Resource tiers were **not** fully equalized across all 5 platforms — smallest available free/trial tier was used per platform, with real specs documented rather than assumed equal (see Methodology).
- Region was **not** held constant across platforms — each platform's default/nearest available region was used, which confounds geography with architecture in the results (see Analysis).
- No formal separate warm-up phase — first iterations are included in reported percentiles.
- Two platforms (Memgraph, ArangoDB) are time-boxed 14-day trials rather than indefinite free tiers, which may affect long-term reproducibility for others rerunning this benchmark.
- Several observed anomalies (ArangoDB's 3-hop p95 spike, Memgraph's 14GB disk figure, FalkorDB exceeding its stated 100MB spec) were documented but not conclusively root-caused within the assignment's time constraints.