"""
Analytics Processor Consumer

Processes user activity events and aggregates analytics:
- Page views, clicks, conversions
- Conversion funnel analysis
- Revenue tracking
- Popular products and pages
- Geographic distribution
- User activity scores
"""

from typing import Any


import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from confluent_kafka import Consumer
from dotenv import load_dotenv

# Add session_4 utils to path
sys.path.insert(0, str(os.path.join(os.path.dirname(__file__), '..', 'session_4')))

from utils.logging_config import setup_logging
from utils.metrics import increment, gauge, histogram, timer, get_metrics

load_dotenv()

# Setup logging
logger = setup_logging("analytics_processor", level=os.getenv("LOG_LEVEL", "INFO"))

# Configuration
BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("KAFKA_ACTIVITIES_TOPIC", "user-activities")
GROUP = os.getenv("KAFKA_ANALYTICS_GROUP", "analytics-processors")
STATS_INTERVAL = int(os.getenv("STATS_INTERVAL", "50"))  # Print stats every N messages

# Consumer configuration
consumer = Consumer({
    "bootstrap.servers": BOOTSTRAP,
    "group.id": GROUP,
    "auto.offset.reset": "earliest",
    "enable.auto.commit": True,
})

# Aggregation data structures
aggregations = {
    # Event type counts
    "event_types": defaultdict(int),
    
    # Page views per page
    "page_views": defaultdict[Any, int](int),
    
    # Events per user
    "user_activity": defaultdict[Any, int](int),
    
    # Conversion funnel tracking
    "funnel": {
        "page_views": set(),      # Users who viewed pages
        "clicks": set(),          # Users who clicked
        "searches": set(),        # Users who searched
        "add_to_cart": set(),     # Users who added to cart
        "purchases": set(),       # Users who purchased
    },
    
    # Revenue tracking
    "revenue": {
        "total": 0.0,
        "by_hour": defaultdict(float),
        "by_product": defaultdict(float),
        "purchase_count": 0,
    },
    
    # Popular products
    "products": defaultdict(int),  # Product views/purchases
    
    # Geographic distribution
    "geography": {
        "countries": defaultdict(int),
        "cities": defaultdict(int),
    },
    
    # Device distribution
    "devices": {
        "types": defaultdict(int),
        "browsers": defaultdict(int),
        "os": defaultdict(int),
    },
    
    # Session tracking (for duration calculation)
    "sessions": {},  # {session_id: {start_time, events, user_id}}
    
    # User journeys (simplified)
    "user_journeys": defaultdict(list),  # {user_id: [event_types]}
}

# Message counter
message_count = 0


def extract_metrics(event):
    """Extract and transform metrics from event"""
    start_time = time.time()
    event_type = event.get("event_type")
    user_id = event.get("user_id")
    session_id = event.get("session_id")
    properties = event.get("properties", {})
    device = event.get("device", {})
    location = event.get("location", {})
    
    # Track event type
    aggregations["event_types"][event_type] += 1
    increment("events_processed_total", labels={"event_type": event_type})
    
    # Track page views
    if "page_url" in event:
        aggregations["page_views"][event["page_url"]] += 1
    
    # Track user activity
    aggregations["user_activity"][user_id] += 1
    
    # Track conversion funnel
    if event_type == "page_view":
        aggregations["funnel"]["page_views"].add(user_id)
    elif event_type == "click":
        aggregations["funnel"]["clicks"].add(user_id)
    elif event_type == "search":
        aggregations["funnel"]["searches"].add(user_id)
    elif event_type == "add_to_cart":
        aggregations["funnel"]["add_to_cart"].add(user_id)
    elif event_type == "purchase":
        aggregations["funnel"]["purchases"].add(user_id)
    
    # Track revenue
    if event_type == "purchase":
        cart_value = properties.get("cart_value", 0.0)
        if cart_value > 0:
            aggregations["revenue"]["total"] += cart_value
            aggregations["revenue"]["purchase_count"] += 1
            increment("revenue_total", value=int(cart_value * 100))  # Store as cents
            increment("purchases_total")
            
            # Revenue by hour
            try:
                timestamp = datetime.fromisoformat(event.get("timestamp", "").replace("Z", "+00:00"))
                hour_key = timestamp.strftime("%Y-%m-%d %H:00")
                aggregations["revenue"]["by_hour"][hour_key] += cart_value
            except:
                pass
            
            # Revenue by product
            product_id = properties.get("product_id")
            if product_id:
                aggregations["revenue"]["by_product"][product_id] += cart_value
    
    # Track popular products
    product_id = properties.get("product_id")
    if product_id:
        aggregations["products"][product_id] += 1
    
    # Track geography
    country = location.get("country")
    city = location.get("city")
    if country:
        aggregations["geography"]["countries"][country] += 1
    if city:
        aggregations["geography"]["cities"][city] += 1
    
    # Track devices
    device_type = device.get("type")
    browser = device.get("browser")
    os_name = device.get("os")
    if device_type:
        aggregations["devices"]["types"][device_type] += 1
    if browser:
        aggregations["devices"]["browsers"][browser] += 1
    if os_name:
        aggregations["devices"]["os"][os_name] += 1
    
    # Track session for duration calculation
    if session_id:
        if session_id not in aggregations["sessions"]:
            try:
                timestamp = datetime.fromisoformat(event.get("timestamp", "").replace("Z", "+00:00"))
                aggregations["sessions"][session_id] = {
                    "start_time": timestamp,
                    "events": 0,
                    "user_id": user_id
                }
            except:
                pass
        if session_id in aggregations["sessions"]:
            aggregations["sessions"][session_id]["events"] += 1
    
    # Track user journey
    aggregations["user_journeys"][user_id].append(event_type)
    
    # Track processing time
    processing_time = (time.time() - start_time) * 1000  # Convert to ms
    histogram("event_processing_time_ms", processing_time)


def calculate_conversion_rates():
    """Calculate conversion funnel rates"""
    funnel = aggregations["funnel"]
    
    total_page_views = len(funnel["page_views"])
    total_clicks = len(funnel["clicks"])
    total_searches = len(funnel["searches"])
    total_add_to_cart = len(funnel["add_to_cart"])
    total_purchases = len(funnel["purchases"])
    
    rates = {}
    if total_page_views > 0:
        rates["page_view_to_click"] = (total_clicks / total_page_views) * 100
        rates["page_view_to_search"] = (total_searches / total_page_views) * 100
        rates["page_view_to_cart"] = (total_add_to_cart / total_page_views) * 100
        rates["page_view_to_purchase"] = (total_purchases / total_page_views) * 100
    
    if total_clicks > 0:
        rates["click_to_purchase"] = (total_purchases / total_clicks) * 100
    
    if total_add_to_cart > 0:
        rates["cart_to_purchase"] = (total_purchases / total_add_to_cart) * 100
    
    return rates


def calculate_avg_session_duration():
    """Calculate average session duration"""
    durations = []
    current_time = datetime.now(timezone.utc)
    
    for session_id, session_data in aggregations["sessions"].items():
        if session_data["events"] > 1:  # Only count sessions with multiple events
            start_time = session_data["start_time"]
            duration = (current_time - start_time).total_seconds()
            if duration > 0:
                durations.append(duration)
    
    if durations:
        return sum(durations) / len(durations)
    return 0


def print_statistics():
    """Print aggregated statistics"""
    print("\n" + "=" * 80)
    print("📊 ANALYTICS AGGREGATION REPORT")
    print("=" * 80)
    
    # Event type distribution
    print("\n📈 Event Type Distribution:")
    total_events = sum(aggregations["event_types"].values())
    for event_type, count in sorted(aggregations["event_types"].items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_events * 100) if total_events > 0 else 0
        print(f"  {event_type:15} : {count:6} ({percentage:5.1f}%)")
    
    # Top pages
    print("\n🌐 Top 10 Pages:")
    for page, count in sorted(aggregations["page_views"].items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {page:40} : {count:6} views")
    
    # Conversion funnel
    print("\n🎯 Conversion Funnel:")
    funnel = aggregations["funnel"]
    rates = calculate_conversion_rates()
    print(f"  Page Views        : {len(funnel['page_views']):6} users")
    print(f"  Clicks            : {len(funnel['clicks']):6} users ({rates.get('page_view_to_click', 0):.1f}% of page views)")
    print(f"  Searches          : {len(funnel['searches']):6} users ({rates.get('page_view_to_search', 0):.1f}% of page views)")
    print(f"  Add to Cart       : {len(funnel['add_to_cart']):6} users ({rates.get('page_view_to_cart', 0):.1f}% of page views)")
    print(f"  Purchases         : {len(funnel['purchases']):6} users ({rates.get('page_view_to_purchase', 0):.1f}% of page views)")
    if rates.get("cart_to_purchase", 0) > 0:
        print(f"  Cart → Purchase   : {rates['cart_to_purchase']:.1f}% conversion rate")
    
    # Revenue
    print("\n💰 Revenue Analytics:")
    revenue = aggregations["revenue"]
    print(f"  Total Revenue     : ${revenue['total']:,.2f}")
    print(f"  Total Purchases   : {revenue['purchase_count']}")
    if revenue['purchase_count'] > 0:
        avg_order_value = revenue['total'] / revenue['purchase_count']
        print(f"  Avg Order Value   : ${avg_order_value:,.2f}")
    
    # Top products by revenue
    if revenue['by_product']:
        print("\n  Top Products by Revenue:")
        for product_id, rev in sorted(revenue['by_product'].items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"    {product_id:15} : ${rev:,.2f}")
    
    # Popular products
    print("\n🛍️  Top 5 Popular Products:")
    for product_id, count in sorted(aggregations["products"].items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {product_id:15} : {count:6} interactions")
    
    # Geographic distribution
    print("\n🌍 Geographic Distribution:")
    print("  Top Countries:")
    for country, count in sorted(aggregations["geography"]["countries"].items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"    {country:15} : {count:6} events")
    print("  Top Cities:")
    for city, count in sorted(aggregations["geography"]["cities"].items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"    {city:20} : {count:6} events")
    
    # Device distribution
    print("\n📱 Device Distribution:")
    print("  Device Types:")
    for device_type, count in sorted(aggregations["devices"]["types"].items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_events * 100) if total_events > 0 else 0
        print(f"    {device_type:15} : {count:6} ({percentage:5.1f}%)")
    
    # User activity
    print("\n👥 User Activity:")
    active_users = len(aggregations["user_activity"])
    if active_users > 0:
        avg_events_per_user = total_events / active_users
        print(f"  Active Users      : {active_users}")
        print(f"  Avg Events/User   : {avg_events_per_user:.1f}")
        
        # Top active users
        print("  Top 5 Most Active Users:")
        for user_id, count in sorted(aggregations["user_activity"].items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"    {user_id:15} : {count:6} events")
    
    # Session metrics
    avg_duration = calculate_avg_session_duration()
    if avg_duration > 0:
        print(f"\n⏱️  Average Session Duration: {avg_duration:.1f} seconds ({avg_duration/60:.1f} minutes)")
    
    print("\n" + "=" * 80)
    print(f"Total Events Processed: {message_count}")
    print("=" * 80 + "\n")


def main():
    """Main consumer loop"""
    global message_count
    
    consumer.subscribe([TOPIC])
    
    logger.info("Starting Analytics Processor", extra={
        "topic": TOPIC,
        "consumer_group": GROUP,
        "bootstrap_servers": BOOTSTRAP,
        "stats_interval": STATS_INTERVAL
    })
    
    print("=" * 80)
    print("📊 Analytics Processor Consumer")
    print("=" * 80)
    print(f"Topic: {TOPIC}")
    print(f"Consumer Group: {GROUP}")
    print(f"Bootstrap servers: {BOOTSTRAP}")
    print(f"Stats interval: Every {STATS_INTERVAL} messages")
    print("=" * 80)
    print("Consuming events... (Ctrl+C to stop)")
    print()
    
    start_time = time.time()
    last_metrics_time = start_time
    
    try:
        while True:
            msg = consumer.poll(1.0)
            
            if msg is None:
                continue
            
            if msg.error():
                logger.error("Consumer error", extra={"error": str(msg.error())})
                increment("consumer_errors_total")
                continue
            
            # Parse message
            try:
                process_start = time.time()
                event = json.loads(msg.value().decode("utf-8"))
                user_id = msg.key().decode("utf-8") if msg.key() else None
                
                # Extract and aggregate metrics
                extract_metrics(event)
                
                message_count += 1
                increment("messages_consumed_total")
                
                # Update rate metrics
                elapsed = time.time() - start_time
                if elapsed > 0:
                    rate = message_count / elapsed
                    gauge("messages_consumed_per_second", rate)
                
                # Log message processing
                processing_time = (time.time() - process_start) * 1000
                logger.debug("Event processed", extra={
                    "user_id": user_id,
                    "event_type": event.get("event_type"),
                    "processing_time_ms": processing_time,
                    "partition": msg.partition(),
                    "offset": msg.offset()
                })
                
                # Print statistics every N messages
                if message_count % STATS_INTERVAL == 0:
                    print_statistics()
                    
                    # Log metrics
                    metrics = get_metrics()
                    logger.info("Analytics metrics snapshot", extra={
                        "messages_consumed": message_count,
                        "events_processed": metrics.get_counters().get("events_processed_total", 0),
                        "revenue_total": aggregations["revenue"]["total"],
                        "purchases": aggregations["revenue"]["purchase_count"]
                    })
                
            except json.JSONDecodeError as e:
                logger.error("Failed to parse message", extra={"error": str(e)})
                increment("parse_errors_total")
                continue
            except Exception as e:
                logger.error("Error processing message", extra={"error": str(e)}, exc_info=True)
                increment("processing_errors_total")
                continue
                
    except KeyboardInterrupt:
        logger.info("Stopping consumer...")
        print("\n\nStopping consumer...")
    finally:
        # Print final statistics
        if message_count > 0:
            print("\n" + "=" * 80)
            print("📊 FINAL STATISTICS")
            print_statistics()
            
            # Log final metrics
            metrics = get_metrics()
            logger.info("Analytics processor stopped", extra={
                "total_messages": message_count,
                "total_events_processed": metrics.get_counters().get("events_processed_total", 0),
                "total_revenue": aggregations["revenue"]["total"],
                "total_purchases": aggregations["revenue"]["purchase_count"]
            })
        
        consumer.close()
        logger.info("Consumer closed")
        print("Consumer closed.")


if __name__ == "__main__":
    main()

