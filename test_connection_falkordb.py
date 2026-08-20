from falkordb import FalkorDB
from dotenv import load_dotenv
import os

load_dotenv()

host = os.environ["FALKORDB_HOST"]
port = int(os.environ["FALKORDB_PORT"])
user = os.environ["FALKORDB_USER"]
password = os.environ["FALKORDB_PASSWORD"]

try:
    db = FalkorDB(host=host, port=port, username=user, password=password)
    graph = db.select_graph("test")
    result = graph.query("RETURN 1")
    print("✅ Connected to FalkorDB successfully!")
except Exception as e:
    print("❌ Connection failed:", e)