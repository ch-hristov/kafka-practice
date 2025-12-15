import json
import os
import time
from confluent_kafka import Producer
from dotenv import load_dotenv

load_dotenv()

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "car_parts_published")

p = Producer({"bootstrap.servers": BOOTSTRAP})

def delivery_report(err, msg):
    if err is not None:
        print(f"Delivery failed: {err}")
    else:
        print(f"Delivered to {msg.topic()} [{msg.partition()}] @ offset {msg.offset()}")

events = [
    {"site": "mobile.com", "part": "alternator", "price": 120.0},
    {"site": "mobile.com", "part": "brake pads", "price": 45.0},
    {"site": "olx.com", "part": "radiator", "price": 80.0},
    {"site": "bazar.com", "part": "starter motor", "price": 95.0},
]

for e in events:
    key = e["site"]  # IMPORTANT: same site => same partition
    value = json.dumps(e).encode("utf-8")
    p.produce(TOPIC, key=key.encode("utf-8"), value=value, callback=delivery_report)
    p.poll(0)
    time.sleep(0.2)

p.flush()
print("Done.")