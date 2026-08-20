from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv()

uri = os.environ["MEMGRAPH_URI"]
user = os.environ["MEMGRAPH_USER"]
password = os.environ["MEMGRAPH_PASSWORD"]

driver = GraphDatabase.driver(uri, auth=(user, password))

try:
    driver.verify_connectivity()
    print("✅ Connected to Memgraph successfully!")
except Exception as e:
    print("❌ Connection failed:", e)
finally:
    driver.close()