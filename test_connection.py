from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv()

uri = os.environ["COGNODB_URI"]
user = os.environ["COGNODB_USER"]
password = os.environ["COGNODB_PASSWORD"]

driver = GraphDatabase.driver(uri, auth=(user, password))

try:
    driver.verify_connectivity()
    print("✅ Connected to CognoDB successfully!")
except Exception as e:
    print("❌ Connection failed:", e)
finally:
    driver.close()