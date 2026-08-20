from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv()

uri = os.environ["NEO4J_URI"]
user = os.environ["NEO4J_USER"]
password = os.environ["NEO4J_PASSWORD"]

driver = GraphDatabase.driver(uri, auth=(user, password))

try:
    driver.verify_connectivity()
    print("✅ Connected to Neo4j AuraDB successfully!")
except Exception as e:
    print("❌ Connection failed:", e)
finally:
    driver.close()