"""
Fraud Detector Consumer with Observability

Monitors user activity events for suspicious patterns and potential fraud.
Includes logging and metrics for production-ready monitoring.
"""

import json
import os
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from confluent_kafka import Consumer
from dotenv import load_dotenv

# Import observability utilities
from utils.logging_config import setup_logging
from utils.metrics import increment, gauge, get_metrics

load_dotenv()

# ============================================================================
# Configuration
# ============================================================================

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("KAFKA_ACTIVITIES_TOPIC", "user-activities")
GROUP = os.getenv("KAFKA_FRAUD_GROUP", "fraud-detectors")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Fraud detection thresholds
HIGH_VALUE_THRESHOLD = float(os.getenv("HIGH_VALUE_THRESHOLD", "500.0"))
VELOCITY_THRESHOLD = int(os.getenv("VELOCITY_THRESHOLD", "5"))
RAPID_LOCATION_CHANGE_MINUTES = int(os.getenv("RAPID_LOCATION_CHANGE_MINUTES", "10"))
MULTIPLE_IP_THRESHOLD = int(os.getenv("MULTIPLE_IP_THRESHOLD", "3"))

# Setup logging
logger = setup_logging("fraud_detector", level=LOG_LEVEL)

# Consumer configuration
consumer = Consumer({
    "bootstrap.servers": BOOTSTRAP,
    "group.id": GROUP,
    "auto.offset.reset": "earliest",
    "enable.auto.commit": True,
})

# ============================================================================
# Fraud Detection Data Structures
# ============================================================================

fraud_data = {
    "user_events": defaultdict(list),
    "user_velocity": defaultdict(list),
    "user_ips": defaultdict(set),
    "user_locations": defaultdict(list),
    "high_value_purchases": [],
    "alerts": [],
}

message_count = 0
fraud_alerts_count = 0


# ============================================================================
# Fraud Detection Functions
# ============================================================================

def parse_timestamp(timestamp_str):
    """Parse ISO timestamp string to datetime"""
    try:
        return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    except:
        return datetime.now(timezone.utc)


def calculate_velocity(user_id, current_time):
    """Calculate events per minute for a user"""
    if user_id not in fraud_data["user_velocity"]:
        return 0
    
    one_minute_ago = current_time - timedelta(minutes=1)
    recent_events = [
        ts for ts in fraud_data["user_velocity"][user_id]
        if ts > one_minute_ago
    ]
    
    return len(recent_events)


def check_rapid_location_change(user_id, new_location, current_time):
    """Check if user changed location rapidly"""
    if user_id not in fraud_data["user_locations"]:
        return False
    
    locations = fraud_data["user_locations"][user_id]
    if len(locations) == 0:
        return False
    
    last_timestamp, last_location = locations[-1]
    time_diff = (current_time - last_timestamp).total_seconds() / 60
    
    if (last_location.get("country") != new_location.get("country") or
        last_location.get("city") != new_location.get("city")):
        if time_diff < RAPID_LOCATION_CHANGE_MINUTES:
            return True
    
    return False


def detect_fraud_patterns(user_id, event, current_time):
    """Detect various fraud patterns"""
    alerts = []
    event_type = event.get("event_type")
    properties = event.get("properties", {})
    ip_address = event.get("ip_address")
    location = event.get("location", {})
    amount = properties.get("cart_value", 0.0) or properties.get("price", 0.0)
    
    # 1. Check velocity
    velocity = calculate_velocity(user_id, current_time)
    if velocity >= VELOCITY_THRESHOLD:
        alerts.append({
            "type": "HIGH_VELOCITY",
            "severity": "HIGH",
            "user_id": user_id,
            "message": f"User has {velocity} events in the last minute (threshold: {VELOCITY_THRESHOLD})",
            "velocity": velocity,
            "timestamp": current_time.isoformat()
        })
        increment("fraud_alerts_total", labels={"type": "high_velocity"})
    
    # 2. Check for multiple IPs
    if ip_address:
        fraud_data["user_ips"][user_id].add(ip_address)
        ip_count = len(fraud_data["user_ips"][user_id])
        if ip_count >= MULTIPLE_IP_THRESHOLD:
            alerts.append({
                "type": "MULTIPLE_IPS",
                "severity": "MEDIUM",
                "user_id": user_id,
                "message": f"User accessed from {ip_count} different IP addresses",
                "ip_addresses": list(fraud_data["user_ips"][user_id]),
                "timestamp": current_time.isoformat()
            })
            increment("fraud_alerts_total", labels={"type": "multiple_ips"})
    
    # 3. Check for rapid location changes
    if location and check_rapid_location_change(user_id, location, current_time):
        alerts.append({
            "type": "RAPID_LOCATION_CHANGE",
            "severity": "HIGH",
            "user_id": user_id,
            "message": f"User changed location rapidly (within {RAPID_LOCATION_CHANGE_MINUTES} minutes)",
            "current_location": location,
            "timestamp": current_time.isoformat()
        })
        increment("fraud_alerts_total", labels={"type": "rapid_location_change"})
    
    # 4. Check for high-value purchases
    if event_type == "purchase" and amount >= HIGH_VALUE_THRESHOLD:
        alerts.append({
            "type": "HIGH_VALUE_PURCHASE",
            "severity": "MEDIUM",
            "user_id": user_id,
            "message": f"High-value purchase detected: ${amount:,.2f}",
            "amount": amount,
            "product_id": properties.get("product_id"),
            "timestamp": current_time.isoformat()
        })
        fraud_data["high_value_purchases"].append({
            "user_id": user_id,
            "amount": amount,
            "timestamp": current_time.isoformat(),
        })
        increment("fraud_alerts_total", labels={"type": "high_value_purchase"})
    
    # 5. Check for purchase without prior activity
    if event_type == "purchase":
        user_events = fraud_data["user_events"].get(user_id, [])
        if len(user_events) < 3:
            alerts.append({
                "type": "PURCHASE_WITHOUT_ACTIVITY",
                "severity": "MEDIUM",
                "user_id": user_id,
                "message": f"Purchase with minimal prior activity ({len(user_events)} events)",
                "amount": amount,
                "timestamp": current_time.isoformat()
            })
            increment("fraud_alerts_total", labels={"type": "purchase_without_activity"})
    
    return alerts


def process_event(event):
    """Process a single event for fraud detection"""
    global fraud_alerts_count
    
    event_type = event.get("event_type")
    user_id = event.get("user_id")
    timestamp_str = event.get("timestamp")
    properties = event.get("properties", {})
    ip_address = event.get("ip_address")
    location = event.get("location", {})
    amount = properties.get("cart_value", 0.0) or properties.get("price", 0.0)
    
    # Only process purchase and add_to_cart events
    if event_type not in ["purchase", "add_to_cart"]:
        return
    
    current_time = parse_timestamp(timestamp_str)
    
    # Track user events
    fraud_data["user_events"][user_id].append((
        current_time,
        event_type,
        ip_address,
        location,
        amount
    ))
    
    # Track velocity
    fraud_data["user_velocity"][user_id].append(current_time)
    
    # Track location
    if location:
        fraud_data["user_locations"][user_id].append((current_time, location))
    
    # Clean old data (keep last hour)
    one_hour_ago = current_time - timedelta(hours=1)
    fraud_data["user_velocity"][user_id] = [
        ts for ts in fraud_data["user_velocity"][user_id]
        if ts > one_hour_ago
    ]
    fraud_data["user_events"][user_id] = [
        e for e in fraud_data["user_events"][user_id]
        if e[0] > one_hour_ago
    ]
    fraud_data["user_locations"][user_id] = [
        (ts, loc) for ts, loc in fraud_data["user_locations"][user_id]
        if ts > one_hour_ago
    ]
    
    # Detect fraud patterns
    alerts = detect_fraud_patterns(user_id, event, current_time)
    
    # Store and display alerts
    for alert in alerts:
        fraud_data["alerts"].append(alert)
        fraud_alerts_count += 1
        print_alert(alert)
        
        # Log alert
        logger.warning("Fraud alert detected", extra={
            "alert_type": alert["type"],
            "severity": alert["severity"],
            "user_id": alert["user_id"],
            "alert_message": alert["message"]  # Changed from "message" to avoid LogRecord conflict
        })


def print_alert(alert):
    """Print a fraud alert"""
    severity_icons = {
        "HIGH": "🔴",
        "MEDIUM": "🟡",
        "LOW": "🟢"
    }
    icon = severity_icons.get(alert["severity"], "⚪")
    
    print(f"\n{icon} FRAUD ALERT [{alert['type']}] - {alert['severity']} SEVERITY")
    print(f"   User ID: {alert['user_id']}")
    print(f"   {alert['message']}")
    print(f"   Time: {alert['timestamp']}")
    if "velocity" in alert:
        print(f"   Velocity: {alert['velocity']} events/min")
    if "amount" in alert:
        print(f"   Amount: ${alert['amount']:,.2f}")
    if "ip_addresses" in alert:
        print(f"   IP Addresses: {', '.join(alert['ip_addresses'])}")
    print()


def print_summary():
    """Print fraud detection summary"""
    print("\n" + "=" * 80)
    print("🛡️  FRAUD DETECTION SUMMARY")
    print("=" * 80)
    
    total_alerts = len(fraud_data["alerts"])
    high_severity = len([a for a in fraud_data["alerts"] if a["severity"] == "HIGH"])
    medium_severity = len([a for a in fraud_data["alerts"] if a["severity"] == "MEDIUM"])
    
    print(f"\n📊 Alert Statistics:")
    print(f"   Total Alerts: {total_alerts}")
    print(f"   High Severity: {high_severity}")
    print(f"   Medium Severity: {medium_severity}")
    
    # Alert types breakdown
    alert_types = defaultdict(int)
    for alert in fraud_data["alerts"]:
        alert_types[alert["type"]] += 1
    
    print(f"\n📋 Alert Types:")
    for alert_type, count in sorted(alert_types.items(), key=lambda x: x[1], reverse=True):
        print(f"   {alert_type:30} : {count:4}")
    
    # High-value purchases
    if fraud_data["high_value_purchases"]:
        print(f"\n💰 High-Value Purchases ({len(fraud_data['high_value_purchases'])}):")
        for purchase in fraud_data["high_value_purchases"][:10]:
            print(f"   User: {purchase['user_id']:15} | ${purchase['amount']:>10,.2f} | {purchase['timestamp']}")
    
    print("\n" + "=" * 80)
    print(f"Total Events Processed: {message_count}")
    print(f"Total Fraud Alerts: {fraud_alerts_count}")
    print("=" * 80 + "\n")


# ============================================================================
# Main Consumer Loop
# ============================================================================

def main():
    """Main consumer loop with observability"""
    global message_count
    
    consumer.subscribe([TOPIC])
    
    logger.info("Starting Fraud Detector", extra={
        "topic": TOPIC,
        "consumer_group": GROUP,
        "bootstrap_servers": BOOTSTRAP,
        "high_value_threshold": HIGH_VALUE_THRESHOLD,
        "velocity_threshold": VELOCITY_THRESHOLD
    })
    
    print("=" * 80)
    print("🛡️  Fraud Detector Consumer")
    print("=" * 80)
    print(f"Topic: {TOPIC}")
    print(f"Consumer Group: {GROUP}")
    print(f"Bootstrap servers: {BOOTSTRAP}")
    print(f"\nFraud Detection Thresholds:")
    print(f"  High Value Purchase: ${HIGH_VALUE_THRESHOLD:,.2f}+")
    print(f"  Velocity Threshold: {VELOCITY_THRESHOLD}+ events/minute")
    print(f"  Rapid Location Change: <{RAPID_LOCATION_CHANGE_MINUTES} minutes")
    print(f"  Multiple IPs: {MULTIPLE_IP_THRESHOLD}+ different IPs")
    print("=" * 80)
    print("Monitoring for fraud... (Ctrl+C to stop)\n")
    
    try:
        while True:
            msg = consumer.poll(1.0)
            
            if msg is None:
                continue
            
            if msg.error():
                logger.error("Consumer error", extra={"error": str(msg.error())})
                increment("consumer_errors_total")
                continue
            
            # Process event
            try:
                event = json.loads(msg.value().decode("utf-8"))
                user_id = msg.key().decode("utf-8") if msg.key() else None
                
                process_event(event)
                
                message_count += 1
                increment("messages_consumed_total")
                
            except json.JSONDecodeError as e:
                logger.error("Failed to parse message", extra={"error": str(e)})
                increment("parse_errors_total")
                continue
            except Exception as e:
                logger.error("Error processing message", extra={"error": str(e)}, exc_info=True)
                increment("processing_errors_total")
                continue
                
    except KeyboardInterrupt:
        logger.info("Stopping fraud detector...")
        print("\n\nStopping fraud detector...")
    finally:
        # Print final summary
        if message_count > 0:
            print_summary()
            
            # Log final metrics
            metrics = get_metrics()
            logger.info("Fraud detector stopped", extra={
                "total_messages": message_count,
                "total_alerts": fraud_alerts_count,
                "fraud_alerts_by_type": metrics.get_counters()
            })
        
        consumer.close()
        logger.info("Fraud detector closed")
        print("Fraud detector closed.")


if __name__ == "__main__":
    main()

