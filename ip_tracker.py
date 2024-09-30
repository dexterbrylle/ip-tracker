import requests
import time
import logging
import os
from datetime import datetime,date, timedelta
from dotenv import load_dotenv
from db_operations import insert_ip_record, insert_log_file_record, insert_speed_test_record, get_last_ip_record, close_connection
from speed_test import run_speedtest
from pymongo.errors import ConnectionFailure
from email_report import compile_and_send_report
load_dotenv()

def get_log_filename():
  """Generate log file name"""
  os.makedirs('./logs', exist_ok=True)
  return f"./logs/ip_tracker_{datetime.now().strftime('%Y-%m-%d')}.log"

def setup_logging():
  """Setup logging"""
  log_filename = get_log_filename()
  logging.basicConfig(filename=log_filename, level=logging.INFO,
                    format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
  return log_filename

def get_public_ip():
  """Fetch public IP using ipify API"""
  try:
    response = requests.get('https://api.ipify.org')
    if response.status_code == 200:
      return response.text
  except requests.RequestException as e:
    logging.error(f"Error fetching public IP: {e}")
    return None

def main():
  check_interval = int(os.getenv("CHECK_INTERVAL"))
  current_date = date.today()
  log_filename = setup_logging()
  last_report_time = datetime.now()

  try:
    while True:
      now = datetime.now()

      # Check if it's time to send a report (every 12 hours)
      if now - last_report_time > timedelta(hours=12):
        try:
          compile_and_send_report()
          last_report_time = now
          logging.info("Report sent successfully")
        except Exception as e:
          logging.error(f"Error sending report: {e}")

      # Check if it's a new day, if so, update logging and record the previous log file
      if now.date() > current_date:
        try:
          insert_log_file_record(os.path.abspath(log_filename), now)
        except ConnectionFailure:
          logging.warning("Failed to insert log file record due to db connection failure.")
        current_date = now.date()
        log_filename = setup_logging() # Update logging

      current_ip = get_public_ip()

      if current_ip:
        last_record = get_last_ip_record()
        changed = not last_record or current_ip != last_record['ip']

        insert_ip_record(current_ip, changed)

        if changed:
          log_message = f"IP Address changed to: {current_ip}"
        else:
          log_message = f"IP Address unchanged: {current_ip}"

        last_check_time = last_record['timestamp'] if last_record else "N/A"
        log_message += f" (Last checked: {last_check_time})"

        logging.info(log_message)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {log_message}")

        # Run speedtest
        print("Running speedtest...")
        speed_result = run_speedtest()
        if speed_result:  # If speedtest result is not None
          speed_log = (f"Download speed: {speed_result['download_speed']} Mbps, "
                                 f"Upload speed: {speed_result['upload_speed']} Mbps, "
                                 f"Ping: {speed_result['ping']} ms, "
                                 f"Server: {speed_result['server']['name']} (ID: {speed_result['server']['id']}), ")
          logging.info(speed_log)
          print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {speed_log}")
          insert_speed_test_record(speed_result)
      else:
        logging.warning("Failed to get public IP")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Failed to get public IP")

      time.sleep(check_interval)
  except KeyboardInterrupt:
    print("\nIP tracking stopped...")
  finally:
    insert_log_file_record(os.path.abspath(log_filename), datetime.now())
    close_connection()


if __name__ == "__main__":
  main()
