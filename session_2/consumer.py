import json
import os
from confluent_kafka import Consumer
from dotenv import load_dotenv

load_dotenv()

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "car_parts_published")
GROUP = os.getenv("KAFKA_GROUP_ID", "demo_group")

c = Consumer({
    "bootstrap.servers": BOOTSTRAP,
    "group.id": GROUP,
    "auto.offset.reset": "earliest",
    "enable.auto.commit": True,
})

c.subscribe([TOPIC])
print(f"Consuming from {TOPIC} as group '{GROUP}'... Ctrl+C to stop.")

try:
    while True:
        msg = c.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            print(f"Error: {msg.error()}")
            continue

        key = msg.key().decode("utf-8") if msg.key() else None
        val = json.loads(msg.value().decode("utf-8"))
        print(f"[partition={msg.partition()} offset={msg.offset()} key={key}] {val}")

except KeyboardInterrupt:
    pass
finally:
    c.close()