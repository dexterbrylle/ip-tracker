import os
import csv
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import smtplib
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("MONGO_DB_NAME")
IP_COLLECTION_NAME = os.getenv("MONGO_COLLECTION")
SPEEDTEST_COLLECTION_NAME = os.getenv("MONGO_SPEEDTEST_COLLECTION")

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_TO = os.getenv("EMAIL_TO")

def get_data_from_db(hours=12):
  """Get data from MongoDB"""
  try:
      print(f"Connecting to MongoDB at {MONGO_URL}")
      client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
      client.server_info()  # This will raise an exception if the connection fails
      print("Successfully connected to MongoDB")

      db = client[DB_NAME]
      ip_collection = db[IP_COLLECTION_NAME]
      speedtest_collection = db[SPEEDTEST_COLLECTION_NAME]

      time_threshold = datetime.utcnow() - timedelta(hours=hours)

      ip_data = list(ip_collection.find({"timestamp": {"$gt": time_threshold}}))
      speedtest_data = list(speedtest_collection.find({"timestamp": {"$gt": time_threshold}}))

      print(f"Retrieved {len(ip_data)} IP records and {len(speedtest_data)} speedtest records")

      client.close()
      return ip_data, speedtest_data
  except ConnectionFailure as e:
      print(f"Failed to connect to MongoDB: {e}")
      raise
  except Exception as e:
      print(f"An error occurred while fetching data from MongoDB: {e}")
      raise

def create_csv_file(ip_data, speedtest_data):
  """Create CSV file from data"""
  filename = f"network_report_{datetime.now().strftime('%Y-%m-%d')}.csv"
  with open(filename, 'w', newline='') as csvfile:
    fieldnames = ['timestamp', 'ip_address', 'download_speed', 'upload_speed', 'ping', 'server_name', 'server_id']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    for ip in ip_data:
      writer.writerow({
        'timestamp': ip['timestamp'],
        'ip_address': ip['ip'],
        'download_speed': '',
        'upload_speed': '',
        'ping': ''
      })

    for speed in speedtest_data:
      writer.writerow({
        'timestamp': speed['timestamp'],
        'ip_address': '',
        'download_speed': speed['download_speed'],
        'upload_speed': speed['upload_speed'],
        'ping': speed['ping'],
        'server_name': speed['server']['name'],
        'server_id': speed['server']['id']
      })

  return filename

def analyze_speedtest_data(speedtest_data):
  """Analyze speedtest data"""
  download_speeds = [s['download_speed'] for s in speedtest_data]
  upload_speeds = [s['upload_speed'] for s in speedtest_data]

  avg_download_speed = sum(download_speeds) / len(download_speeds) if download_speeds else 0
  avg_upload_speed = sum(upload_speeds) / len(upload_speeds) if upload_speeds else 0

  slow_downloads = [(s['timestamp'], s['download_speed']) for s in speedtest_data if s['download_speed'] < 500]
  slow_uploads = [(s['timestamp'], s['upload_speed']) for s in speedtest_data if s['upload_speed'] < 500]

  return avg_download_speed, avg_upload_speed, slow_downloads, slow_uploads

from collections import Counter
from datetime import datetime

def analyze_ip_data(ip_data):
    """Analyze IP data"""
    ip_addresses = [i['ip'] for i in ip_data]
    ip_counter = Counter(ip_addresses)

    num_unique_ips = len(ip_counter)
    num_ip_changes = sum(1 for i in ip_data if i.get('changed', False))
    most_common_ip = ip_counter.most_common(1)[0] if ip_counter else None

    ip_change_times = [i['timestamp'] for i in ip_data if i.get('changed', False)]
    first_change = min(ip_change_times) if ip_change_times else None
    last_change = max(ip_change_times) if ip_change_times else None

    return {
        'num_unique_ips': num_unique_ips,
        'num_ip_changes': num_ip_changes,
        'most_common_ip': most_common_ip,
        'first_change': first_change,
        'last_change': last_change
    }

def send_email(csv_filename, avg_download_speed, avg_upload_speed, slow_downloads, slow_uploads, ip_analysis):
  """Send email with CSV file and analysis"""
  msg = MIMEMultipart()
  msg['From'] = EMAIL_FROM
  msg['To'] = EMAIL_TO
  msg['Subject'] = f"Network Report: {datetime.now().strftime('%Y-%m-%d')}"

  body = f"""
  Average download speed: {avg_download_speed:.2f} Mbps
    Average upload speed: {avg_upload_speed:.2f} Mbps

    Number of times download speed was < 500 Mbps: {len(slow_downloads)}
    Number of times upload speed was < 500 Mbps: {len(slow_uploads)}

    Number of unique IP addresses: {ip_analysis['num_unique_ips']}
    Number of IP address changes: {ip_analysis['num_ip_changes']}
    Most common IP address: {ip_analysis['most_common_ip'][0]} (seen {ip_analysis['most_common_ip'][1]} times)
    First IP change: {ip_analysis['first_change'].strftime('%Y-%m-%d %H:%M:%S') if ip_analysis['first_change'] else 'N/A'}
    Last IP change: {ip_analysis['last_change'].strftime('%Y-%m-%d %H:%M:%S') if ip_analysis['last_change'] else 'N/A'}

    Timestamps for slow download speeds:
    {format_timestamps(slow_downloads)}

    Timestamps for slow upload speeds:
    {format_timestamps(slow_uploads)}
  """

  msg.attach(MIMEText(body, 'plain'))

  try:
    print(f"Attempting to connect to SMTP server {SMTP_SERVER}:{SMTP_PORT}")
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.ehlo()
        if SMTP_PORT == 587:
            server.starttls()
            server.ehlo()
        print("Logging in to SMTP server")
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        print("Sending email")
        server.send_message(msg)
        print("Email sent successfully")
  except smtplib.SMTPException as e:
      print(f"An error occurred while sending the email: {e}")
      raise

def format_timestamps(speed_data):
    return '\n'.join([f"  {dt.strftime('%Y-%m-%d %H:%M:%S')}: {speed:.2f} Mbps" for dt, speed in speed_data])

def compile_and_send_report():
    """Compile and send report"""
    try:
        ip_data, speedtest_data = get_data_from_db()
        csv_filename = create_csv_file(ip_data, speedtest_data)
        avg_download_speed, avg_upload_speed, slow_downloads, slow_uploads = analyze_speedtest_data(speedtest_data)
        ip_analysis = analyze_ip_data(ip_data)
        send_email(csv_filename, avg_download_speed, avg_upload_speed, slow_downloads, slow_uploads, ip_analysis)
        os.remove(csv_filename)
        print("Report compiled and sent successfully")
    except Exception as e:
        print(f"An error occurred while compiling and sending the report: {e}")

if __name__ == "__main__":
  compile_and_send_report()
