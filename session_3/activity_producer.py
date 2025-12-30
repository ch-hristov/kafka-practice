"""
User Activity Event Producer

Generates high-volume realistic user activity events and publishes to Kafka.
Simulates real user behavior patterns with sessions, searches, and purchases.
"""

import json
import os
import random
import sys
import time
import uuid
from datetime import datetime, timezone
from confluent_kafka import Producer
from dotenv import load_dotenv

# Add session_4 utils to path
sys.path.insert(0, str(os.path.join(os.path.dirname(__file__), '..', 'session_4')))

from utils.logging_config import setup_logging
from utils.metrics import increment, gauge, histogram, timer, get_metrics

load_dotenv()

# Setup logging
logger = setup_logging("activity_producer", level=os.getenv("LOG_LEVEL", "INFO"))

# Configuration
BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("KAFKA_ACTIVITIES_TOPIC", "user-activities")
EVENTS_PER_SECOND = int(os.getenv("EVENTS_PER_SECOND", "10"))
VERBOSE = os.getenv("VERBOSE", "false").lower() == "true"

# Event type distribution (as specified in plan)
EVENT_TYPES = {
    "page_view": 0.60,    # 60%
    "click": 0.25,        # 25%
    "search": 0.10,       # 10%
    "add_to_cart": 0.03,  # 3%
    "purchase": 0.02      # 2%
}

# Sample data pools
PAGES = [
    "/",
    "/products/laptop",
    "/products/mouse",
    "/products/keyboard",
    "/products/monitor",
    "/products/headphones",
    "/category/electronics",
    "/category/computers",
    "/search",
    "/cart",
    "/checkout",
    "/about",
    "/contact"
]

PRODUCTS = [
    {"id": "PROD-001", "name": "Laptop", "price": 999.99, "category": "electronics"},
    {"id": "PROD-002", "name": "Mouse", "price": 29.99, "category": "electronics"},
    {"id": "PROD-003", "name": "Keyboard", "price": 79.99, "category": "electronics"},
    {"id": "PROD-004", "name": "Monitor", "price": 299.99, "category": "electronics"},
    {"id": "PROD-005", "name": "Headphones", "price": 149.99, "category": "electronics"},
]

SEARCH_QUERIES = [
    "laptop deals",
    "wireless mouse",
    "gaming keyboard",
    "4k monitor",
    "noise cancelling headphones",
    "cheap laptops",
    "best mouse 2024",
    "mechanical keyboard"
]

DEVICES = [
    {"type": "desktop", "os": "Windows", "browser": "Chrome"},
    {"type": "desktop", "os": "macOS", "browser": "Safari"},
    {"type": "desktop", "os": "Linux", "browser": "Firefox"},
    {"type": "mobile", "os": "iOS", "browser": "Safari"},
    {"type": "mobile", "os": "Android", "browser": "Chrome"},
    {"type": "tablet", "os": "iOS", "browser": "Safari"},
    {"type": "tablet", "os": "Android", "browser": "Chrome"},
]

LOCATIONS = [
    {"country": "US", "city": "New York", "timezone": "America/New_York"},
    {"country": "US", "city": "Los Angeles", "timezone": "America/Los_Angeles"},
    {"country": "US", "city": "Chicago", "timezone": "America/Chicago"},
    {"country": "UK", "city": "London", "timezone": "Europe/London"},
    {"country": "CA", "city": "Toronto", "timezone": "America/Toronto"},
    {"country": "AU", "city": "Sydney", "timezone": "Australia/Sydney"},
]

REFERRERS = [
    "https://google.com",
    "https://bing.com",
    "https://facebook.com",
    "https://twitter.com",
    "https://linkedin.com",
    "direct",
    None
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15",
    "Mozilla/5.0 (Android 10; Mobile) AppleWebKit/537.36",
]

# Producer instance
producer = Producer({"bootstrap.servers": BOOTSTRAP})

# Track active user sessions
active_sessions = {}  # {user_id: {session_id, current_page, cart_value, events_in_session}}


def delivery_report(err, msg):
    """Callback for message delivery"""
    if err is not None:
        logger.error("Delivery failed", extra={
            "error": str(err),
            "topic": msg.topic() if msg else None
        })
        increment("delivery_failure_total")
    else:
        logger.info("Event delivered", extra={
            "topic": msg.topic(),
            "partition": msg.partition(),
            "offset": msg.offset()
        })
        increment("delivery_success_total")
        increment("events_sent_total")


def generate_user_id():
    """Generate a realistic user ID"""
    return f"user-{random.randint(1000, 9999)}"


def get_or_create_session(user_id):
    """Get existing session or create new one for user"""
    if user_id not in active_sessions:
        # Create new session
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
    return "page_view"  # fallback


def generate_event_properties(event_type, session):
    """Generate event-specific properties"""
    properties = {}
    
    if event_type in ["page_view", "click"]:
        # Select a page (sometimes current, sometimes new)
        if random.random() < 0.7:  # 70% chance to continue on current page
            page = session["current_page"]
        else:
            page = random.choice(PAGES)
        session["current_page"] = page
        properties["page_url"] = page
        
        # Sometimes include product info
        if "/products/" in page and random.random() < 0.8:
            product = random.choice(PRODUCTS)
            properties["product_id"] = product["id"]
            properties["product_name"] = product["name"]
            properties["price"] = product["price"]
            properties["category"] = product["category"]
    
    elif event_type == "search":
        query = random.choice(SEARCH_QUERIES)
        properties["search_query"] = query
        session["searched"] = True
    
    elif event_type == "add_to_cart":
        product = random.choice(PRODUCTS)
        properties["product_id"] = product["id"]
        properties["product_name"] = product["name"]
        properties["price"] = product["price"]
        properties["category"] = product["category"]
        session["cart_value"] += product["price"]
        properties["cart_value"] = session["cart_value"]
        session["added_to_cart"] = True
    
    elif event_type == "purchase":
        # Only purchase if something in cart
        if session["cart_value"] > 0:
            properties["cart_value"] = session["cart_value"]
            # Clear cart after purchase
            session["cart_value"] = 0.0
        else:
            # Sometimes purchase without cart (direct purchase)
            product = random.choice(PRODUCTS)
            properties["product_id"] = product["id"]
            properties["product_name"] = product["name"]
            properties["price"] = product["price"]
            properties["category"] = product["category"]
            properties["cart_value"] = product["price"]
    
    return properties


def generate_user_activity_event():
    """Generate a single user activity event"""
    # Select or create user
    user_id = generate_user_id()
    session = get_or_create_session(user_id)
    
    # Select event type
    event_type = select_event_type()
    
    # Realistic pattern: search before purchase, add to cart before purchase
    if event_type == "purchase":
        # 80% chance user searched or added to cart first
        if not session["searched"] and not session["added_to_cart"]:
            if random.random() < 0.8:
                # Make it a search or add_to_cart instead
                event_type = random.choice(["search", "add_to_cart"])
    
    # Generate event properties
    properties = generate_event_properties(event_type, session)
    
    # Select device and location
    device = random.choice(DEVICES)
    location = random.choice(LOCATIONS)
    referrer = random.choice(REFERRERS)
    user_agent = random.choice(USER_AGENTS)
    
    # Generate IP address
    ip_address = f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"
    
    # Determine sender direction
    sender = "user" if event_type in ["page_view", "click", "search", "add_to_cart", "purchase"] else "agent"
    
    # Build event
    event = {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "session_id": session["session_id"],
        "event_type": event_type,
        "page_url": properties.get("page_url", session["current_page"]),
        "referrer": referrer,
        "user_agent": user_agent,
        "ip_address": ip_address,
        "properties": properties,
        "device": device,
        "location": location
    }
    
    # Increment session event count
    session["events_in_session"] += 1
    
    # End session randomly (5% chance after each event, or after 20 events)
    if session["events_in_session"] >= 20 or (session["events_in_session"] > 5 and random.random() < 0.05):
        del active_sessions[user_id]
    
    return event, user_id


def main():
    """Main producer loop"""
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
    print("Generating events... (Ctrl+C to stop)")
    print()
    
    event_count = 0
    start_time = time.time()
    last_metrics_time = start_time
    
    try:
        while True:
            # Generate event with timing
            with timer("event_generation_time"):
                event, user_id = generate_user_activity_event()
            
            # Publish to Kafka
            key = user_id.encode("utf-8")
            value = json.dumps(event).encode("utf-8")
            
            with timer("kafka_produce_time"):
                producer.produce(
                    TOPIC,
                    key=key,
                    value=value,
                    callback=delivery_report
                )
            
            # Poll to handle callbacks
            producer.poll(0)
            
            event_count += 1
            
            # Update metrics
            gauge("active_sessions", len(active_sessions))
            
            # Print progress every 10 events
            if event_count % 10 == 0:
                elapsed = time.time() - start_time
                rate = event_count / elapsed if elapsed > 0 else 0
                gauge("events_sent_per_second", rate)
                
                print(f"📊 Events sent: {event_count} | Rate: {rate:.1f} events/sec | Active sessions: {len(active_sessions)}")
                
                # Log metrics every 50 events
                if event_count % 50 == 0:
                    metrics = get_metrics()
                    logger.info("Producer metrics", extra={
                        "events_sent_total": metrics.get_counters().get("events_sent_total", 0),
                        "events_per_second": rate,
                        "active_sessions": len(active_sessions)
                    })
            
            # Control rate
            time.sleep(1.0 / EVENTS_PER_SECOND)
            
    except KeyboardInterrupt:
        logger.info("Stopping producer...")
        print("\n\nStopping producer...")
    finally:
        # Flush remaining messages
        logger.info("Flushing remaining messages...")
        print("Flushing remaining messages...")
        producer.flush()
        
        # Print final stats
        elapsed = time.time() - start_time
        rate = event_count / elapsed if elapsed > 0 else 0
        
        # Get final metrics
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

