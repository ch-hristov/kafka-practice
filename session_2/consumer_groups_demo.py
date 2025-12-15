"""
Demonstration of how multiple consumer groups consume from the same topic.

This script shows:
1. Two different consumer groups can consume from the same topic independently
2. Each consumer group maintains its own offset tracking
3. Messages are distributed across partitions within each group
"""

import json
import os
import signal
import sys
import threading
import time
from confluent_kafka import Consumer
from dotenv import load_dotenv

load_dotenv()

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "car_parts_new")

# Two different consumer groups
GROUP_1 = "group_alpha"
GROUP_2 = "group_beta"

running = True


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    global running
    print("\n\nShutting down consumers...")
    running = False
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def consume_messages(group_id, group_name, color_code):
    """
    Consumer function for a specific consumer group
    
    Args:
        group_id: The Kafka consumer group ID
        group_name: Display name for the group
        color_code: ANSI color code for terminal output
    """
    consumer = Consumer({
        "bootstrap.servers": BOOTSTRAP,
        "group.id": group_id,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True,
    })

    consumer.subscribe([TOPIC])
    
    # ANSI color reset
    reset = "\033[0m"
    
    print(f"{color_code}[{group_name}] Started consuming from '{TOPIC}' as group '{group_id}'{reset}")
    print(f"{color_code}[{group_name}] Waiting for messages... (Ctrl+C to stop){reset}\n")

    message_count = 0
    
    try:
        while running:
            msg = consumer.poll(1.0)
            
            if msg is None:
                continue
                
            if msg.error():
                print(f"{color_code}[{group_name}] Error: {msg.error()}{reset}")
                continue

            message_count += 1
            key = msg.key().decode("utf-8") if msg.key() else None
            val = json.loads(msg.value().decode("utf-8"))
            
            # Display message with partition info
            print(f"{color_code}[{group_name}] "
                  f"partition={msg.partition()} "
                  f"offset={msg.offset()} "
                  f"key={key} "
                  f"msg#{message_count} → {val}{reset}")
            
    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()
        print(f"{color_code}[{group_name}] Consumer closed. Total messages consumed: {message_count}{reset}")


def main():
    """Run two consumer groups in separate threads"""
    print("=" * 80)
    print("CONSUMER GROUPS DEMONSTRATION")
    print("=" * 80)
    print(f"Topic: {TOPIC}")
    print(f"Bootstrap servers: {BOOTSTRAP}")
    print(f"\nStarting TWO consumer groups:")
    print(f"  - Group 1: {GROUP_1} (shown in GREEN)")
    print(f"  - Group 2: {GROUP_2} (shown in BLUE)")
    print(f"\nBoth groups will consume from the SAME topic independently.")
    print(f"Each group maintains its own offset tracking.\n")
    print("=" * 80)
    print()

    # ANSI color codes
    GREEN = "\033[92m"  # Group 1
    BLUE = "\033[94m"   # Group 2

    # Create threads for each consumer group
    thread1 = threading.Thread(
        target=consume_messages,
        args=(GROUP_1, "GROUP_1", GREEN),
        daemon=True
    )
    
    thread2 = threading.Thread(
        target=consume_messages,
        args=(GROUP_2, "GROUP_2", BLUE),
        daemon=True
    )

    # Start both consumers
    thread1.start()
    thread2.start()

    # Wait for both threads (they run until interrupted)
    try:
        thread1.join()
        thread2.join()
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    main()

