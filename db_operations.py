from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("MONGO_DB_NAME")
COLLECTION_NAME = os.getenv("MONGO_COLLECTION")
LOGS_COLLECTION_NAME = os.getenv("MONGO_LOGS_COLLECTION")
SPEED_COLLECTION_NAME = os.getenv("MONGO_SPEEDTEST_COLLECTION")

client = MongoClient(MONGO_URL)
db = client[DB_NAME]
ip_collection = db[COLLECTION_NAME]
log_collection = db[LOGS_COLLECTION_NAME]
speed_collection = db[SPEED_COLLECTION_NAME]

def insert_ip_record(ip_address, changed):
  record = {
    "ip": ip_address,
    "timestamp": datetime.now(),
    "changed": changed
  }
  return ip_collection.insert_one(record)

def get_last_ip_record():
  return ip_collection.find_one(sort=[("timestamp", -1)])

def insert_log_file_record(log_file_path, generated_time):
  record = {
    "log_file": log_file_path,
    "generated_time": generated_time
  }
  return log_collection.insert_one(record)

def insert_speed_test_record(data):
  return speed_collection.insert_one(data)

def close_connection():
  client.close()

