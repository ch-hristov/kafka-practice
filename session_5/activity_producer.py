"""
User Activity Event Producer with Observability

Generates realistic user activity events and publishes to Kafka.
Includes logging and metrics for production-ready observability.
"""

import json
import os
import random
import time
import uuid
from datetime import datetime, timezone
from confluent_kafka import Producer
from dotenv import load_dotenv

# Import observability utilities
from utils.logging_config import setup_logging
from utils.metrics import increment, gauge, timer, get_metrics

load_dotenv()

# ============================================================================
# Configuration
# ============================================================================

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("KAFKA_ACTIVITIES_TOPIC", "user-activities")
EVENTS_PER_SECOND = int(os.getenv("EVENTS_PER_SECOND", "10"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Setup logging
logger = setup_logging("activity_producer", level=LOG_LEVEL)

# Event type distribution
EVENT_TYPES = {
    "page_view": 0.60,    # 60%
    "click": 0.25,        # 25%
    "search": 0.10,       # 10%
    "add_to_cart": 0.03,  # 3%
    "purchase": 0.02      # 2%
}

# Sample data pools
PAGES = [
    "/", "/products/laptop", "/products/mouse", "/products/keyboard",
    "/products/monitor", "/products/headphones", "/category/electronics",
    "/category/computers", "/search", "/cart", "/checkout"
]

PRODUCTS = [
    {"id": "PROD-001", "name": "Laptop", "price": 999.99, "category": "electronics"},
    {"id": "PROD-002", "name": "Mouse", "price": 29.99, "category": "electronics"},
    {"id": "PROD-003", "name": "Keyboard", "price": 79.99, "category": "electronics"},
    {"id": "PROD-004", "name": "Monitor", "price": 299.99, "category": "electronics"},
    {"id": "PROD-005", "name": "Headphones", "price": 149.99, "category": "electronics"},
]

SEARCH_QUERIES = [
    "laptop deals", "wireless mouse", "gaming keyboard", "4k monitor",
    "noise cancelling headphones", "cheap laptops", "best mouse 2024"
]

DEVICES = [
    {"type": "desktop", "os": "Windows", "browser": "Chrome"},
    {"type": "desktop", "os": "macOS", "browser": "Safari"},
    {"type": "mobile", "os": "iOS", "browser": "Safari"},
    {"type": "mobile", "os": "Android", "browser": "Chrome"},
    {"type": "tablet", "os": "iOS", "browser": "Safari"},
]

LOCATIONS = [
    {"country": "US", "city": "New York", "timezone": "America/New_York"},
    {"country": "US", "city": "Los Angeles", "timezone": "America/Los_Angeles"},
    {"country": "UK", "city": "London", "timezone": "Europe/London"},
    {"country": "CA", "city": "Toronto", "timezone": "America/Toronto"},
]

REFERRERS = [
    "https://google.com", "https://bing.com", "https://facebook.com",
    "direct", None
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15",
]

# ============================================================================
# Producer Setup
# ============================================================================

producer = Producer({"bootstrap.servers": BOOTSTRAP})
active_sessions = {}  # Track user sessions


# ============================================================================
# Event Generation Functions
# ============================================================================

def generate_user_id():
    """Generate a realistic user ID"""
    return f"user-{random.randint(1000, 9999)}"


def get_or_create_session(user_id):
    """Get existing session or create new one for user"""
    if user_id not in active_sessions:
        active_sessions[user_id] = {
            "session_id": f"sess-{uuid.uuid4().hex[:8]}",
            "current_page": "/",
            "cart_value": 0.0,
            "events_in_session": 0,
            "searched": False,
            "added_to_cart": False,
        }
    return active_sessions[user_id]


def select_event_type():
    """Select event type based on distribution"""
    rand = random.random()
    cumulative = 0
    for event_type, probability in EVENT_TYPES.items():
        cumulative += probability
        if rand <= cumulative:
            return event_type
    return "page_view"


def generate_event_properties(event_type, session):
    """Generate event-specific properties"""
    properties = {}
    
    if event_type in ["page_view", "click"]:
        page = session["current_page"] if random.random() < 0.7 else random.choice(PAGES)
        session["current_page"] = page
        properties["page_url"] = page
        
        if "/products/" in page and random.random() < 0.8:
            product = random.choice(PRODUCTS)
            properties.update({
                "product_id": product["id"],
                "product_name": product["name"],
                "price": product["price"],
                "category": product["category"]
            })
    
    elif event_type == "search":
        properties["search_query"] = random.choice(SEARCH_QUERIES)
        session["searched"] = True
    
    elif event_type == "add_to_cart":
        product = random.choice(PRODUCTS)
        session["cart_value"] += product["price"]
        properties.update({
            "product_id": product["id"],
            "product_name": product["name"],
            "price": product["price"],
            "category": product["category"],
            "cart_value": session["cart_value"]
        })
        session["added_to_cart"] = True
    
    elif event_type == "purchase":
        if session["cart_value"] > 0:
            properties["cart_value"] = session["cart_value"]
            session["cart_value"] = 0.0
        else:
            product = random.choice(PRODUCTS)
            properties.update({
                "product_id": product["id"],
                "product_name": product["name"],
                "price": product["price"],
                "category": product["category"],
                "cart_value": product["price"]
            })
    
    return properties


def generate_user_activity_event():
    """Generate a single user activity event"""
    user_id = generate_user_id()
    session = get_or_create_session(user_id)
    event_type = select_event_type()
    
    # Realistic pattern: search/cart before purchase
    if event_type == "purchase" and not session["searched"] and not session["added_to_cart"]:
        if random.random() < 0.8:
            event_type = random.choice(["search", "add_to_cart"])
    
    properties = generate_event_properties(event_type, session)
    device = random.choice(DEVICES)
    location = random.choice(LOCATIONS)
    
    event = {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "session_id": session["session_id"],
        "event_type": event_type,
        "page_url": properties.get("page_url", session["current_page"]),
        "referrer": random.choice(REFERRERS),
        "user_agent": random.choice(USER_AGENTS),
        "ip_address": f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}",
        "properties": properties,
        "device": device,
        "location": location
    }
    
    session["events_in_session"] += 1
    
    # End session randomly
    if session["events_in_session"] >= 20 or (session["events_in_session"] > 5 and random.random() < 0.05):
        del active_sessions[user_id]
    
    return event, user_id


# ============================================================================
# Kafka Integration
# ============================================================================

def delivery_report(err, msg):
    """Callback for message delivery - logs and tracks metrics"""
    if err is not None:
        logger.error("Delivery failed", extra={
            "error": str(err),
            "topic": msg.topic() if msg else None
        })
        increment("delivery_failure_total")
    else:
        logger.debug("Event delivered", extra={
            "topic": msg.topic(),
            "partition": msg.partition(),
            "offset": msg.offset()
        })
        increment("delivery_success_total")
        increment("events_sent_total")


# ============================================================================
# Main Producer Loop
# ============================================================================

def main():
    """Main producer loop with observability"""
    logger.info("Starting User Activity Event Producer", extra={
        "topic": TOPIC,
        "bootstrap_servers": BOOTSTRAP,
        "events_per_second": EVENTS_PER_SECOND
    })
    
    print("=" * 80)
    print("🚀 User Activity Event Producer")
    print("=" * 80)
    print(f"Topic: {TOPIC}")
    print(f"Bootstrap servers: {BOOTSTRAP}")
    print(f"Events per second: {EVENTS_PER_SECOND}")
    print("=" * 80)
    print("Generating events... (Ctrl+C to stop)\n")
    
    event_count = 0
    start_time = time.time()
    
    try:
        while True:
            # Generate event with timing
            with timer("event_generation_time"):
                event, user_id = generate_user_activity_event()
            
            # Publish to Kafka with timing
            key = user_id.encode("utf-8")
            value = json.dumps(event).encode("utf-8")
            
            with timer("kafka_produce_time"):
                producer.produce(
                    TOPIC,
                    key=key,
                    value=value,
                    callback=delivery_report
                )
            
            producer.poll(0)
            event_count += 1
            gauge("active_sessions", len(active_sessions))
            
            # Progress update every 10 events
            if event_count % 10 == 0:
                elapsed = time.time() - start_time
                rate = event_count / elapsed if elapsed > 0 else 0
                gauge("events_sent_per_second", rate)
                
                print(f"📊 Events sent: {event_count} | Rate: {rate:.1f} events/sec | Active sessions: {len(active_sessions)}")
            
            # Log metrics snapshot every 50 events
            if event_count % 50 == 0:
                metrics = get_metrics()
                logger.info("Producer metrics snapshot", extra={
                    "events_sent_total": metrics.get_counters().get("events_sent_total", 0),
                    "events_per_second": rate,
                    "active_sessions": len(active_sessions)
                })
            
            time.sleep(1.0 / EVENTS_PER_SECOND)
            
    except KeyboardInterrupt:
        logger.info("Stopping producer...")
        print("\n\nStopping producer...")
    finally:
        logger.info("Flushing remaining messages...")
        print("Flushing remaining messages...")
        producer.flush()
        
        # Final statistics
        elapsed = time.time() - start_time
        rate = event_count / elapsed if elapsed > 0 else 0
        metrics = get_metrics()
        counters = metrics.get_counters()
        
        print()
        print("=" * 80)
        print("📊 Final Statistics")
        print("=" * 80)
        print(f"Total events sent: {event_count}")
        print(f"Total time: {elapsed:.2f} seconds")
        print(f"Average rate: {rate:.2f} events/second")
        print(f"Successful deliveries: {counters.get('delivery_success_total', 0)}")
        print(f"Failed deliveries: {counters.get('delivery_failure_total', 0)}")
        print("=" * 80)
        
        logger.info("Producer stopped", extra={
            "total_events": event_count,
            "total_time_seconds": elapsed,
            "average_rate": rate,
            "successful_deliveries": counters.get('delivery_success_total', 0),
            "failed_deliveries": counters.get('delivery_failure_total', 0)
        })


if __name__ == "__main__":
    main()

