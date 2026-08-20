from arango import ArangoClient
from dotenv import load_dotenv
import os

load_dotenv()

uri = os.environ["ARANGO_URI"]
user = os.environ["ARANGO_USER"]
password = os.environ["ARANGO_PASSWORD"]

client = ArangoClient(hosts=uri)

try:
    sys_db = client.db("_system", username=user, password=password)
    print("✅ Connected to ArangoDB successfully! Version:", sys_db.version())
except Exception as e:
    print("❌ Connection failed:", e)