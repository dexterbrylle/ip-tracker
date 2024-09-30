FROM python:3.9-slim
WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt
RUN apt-get update && apt-get install -y speedtest-cli
CMD ["python", "ip_tracker.py"]
