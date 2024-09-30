import speedtest
from datetime import datetime
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("MONGO_DB_NAME")
SPEEDTEST_COLLECTION_NAME = os.getenv("MONGO_SPEEDTEST_COLLECTION")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
speedtest_collection = db[SPEEDTEST_COLLECTION_NAME]

def run_speedtest():
  """Run speedtest and return results"""
  try:
    # Run speedtest-cli command
    st = speedtest.Speedtest()
    st.get_best_server()
    #servers = st.get_servers()
    #print("Available servers:", servers)

    # Run download and upload tests
    print("Running download test...")
    download_speed = st.download() / 1_000_000  # Convert to Mbps
    print(f"Download speed: {download_speed} Mbps")
    print("Running upload test...")
    upload_speed = st.upload() / 1_000_000  # Convert to Mbps
    print(f"Upload speed: {upload_speed} Mbps")

    # Get results
    results = st.results.dict()

    record = {
        "timestamp": datetime.now(),
        "download_speed": round(download_speed, 2),
        "upload_speed": round(upload_speed, 2),
        "server": {
            "name": results['server']['sponsor'],
            "id": results['server']['id'],
        },
        "ping": round(results['ping'], 2)
    }

    return record
  except Exception as e:
    print(f"Error running speedtest: {e}")
    return None

if __name__ == "__main__":
  print(f"Running speedtest...")
  result = run_speedtest()
  if result:
    print(f"Download speed: {result['download_speed']} Mbps")
    print(f"Upload speed: {result['upload_speed']} Mbps")
    print(f"Ping: {result['ping']} ms")
    print(f"Server: {result['server']['name']} (ID: {result['server']['id']})")
