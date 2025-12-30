"""
Fraud Detector Consumer

Monitors user activity events for suspicious patterns and potential fraud:
- Purchase and add_to_cart velocity monitoring
- IP address anomaly detection
- High-value purchase alerts
- Rapid location changes (potential account takeover)
- Multiple IPs per user (potential credential stuffing)
- Suspicious session patterns
"""

import json
import os
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from confluent_kafka import Consumer
from dotenv import load_dotenv

load_dotenv()

# Configuration
BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("KAFKA_ACTIVITIES_TOPIC", "user-activities")
GROUP = os.getenv("KAFKA_FRAUD_GROUP", "fraud-detectors")

# Fraud detection thresholds
HIGH_VALUE_THRESHOLD = float(os.getenv("HIGH_VALUE_THRESHOLD", "500.0"))  # $500+
VELOCITY_THRESHOLD = int(os.getenv("VELOCITY_THRESHOLD", "5"))  # 5+ events per minute
RAPID_LOCATION_CHANGE_MINUTES = int(os.getenv("RAPID_LOCATION_CHANGE_MINUTES", "10"))  # 10 minutes
MULTIPLE_IP_THRESHOLD = int(os.getenv("MULTIPLE_IP_THRESHOLD", "3"))  # 3+ different IPs

# Consumer configuration
consumer = Consumer({
    "bootstrap.servers": BOOTSTRAP,
    "group.id": GROUP,
    "auto.offset.reset": "earliest",
    "enable.auto.commit": True,
})

# Fraud detection data structures
fraud_data = {
    # User activity tracking
    "user_events": defaultdict(list),  # {user_id: [(timestamp, event_type, ip, location, amount)]}
    
    # Velocity tracking (events per minute per user)
    "user_velocity": defaultdict(list),  # {user_id: [timestamps]}
    
    # IP address tracking per user
    "user_ips": defaultdict(set),  # {user_id: {ip1, ip2, ...}}
    
    # Location tracking per user
    "user_locations": defaultdict(list),  # {user_id: [(timestamp, location)]}
    
    # High-value purchases
    "high_value_purchases": [],  # List of suspicious high-value purchases
    
    # Suspicious patterns detected
    "alerts": [],  # List of fraud alerts
}

# Message counter
message_count = 0
fraud_alerts_count = 0


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
    
    # Get events from last minute
    one_minute_ago = current_time - timedelta(minutes=1)
    recent_events = [
        ts for ts in fraud_data["user_velocity"][user_id]
        if ts > one_minute_ago
    ]
    
    return len(recent_events)


def check_rapid_location_change(user_id, new_location, current_time):
    """Check if user changed location rapidly (potential account takeover)"""
    if user_id not in fraud_data["user_locations"]:
        return False
    
    locations = fraud_data["user_locations"][user_id]
    if len(locations) == 0:
        return False
    
    # Check last location
    last_timestamp, last_location = locations[-1]
    time_diff = (current_time - last_timestamp).total_seconds() / 60  # minutes
    
    # If location changed and time difference is small
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
    
    # 1. Check velocity (events per minute)
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
    
    # 2. Check for multiple IPs (potential credential stuffing or account sharing)
    if ip_address:
        fraud_data["user_ips"][user_id].add(ip_address)
        ip_count = len(fraud_data["user_ips"][user_id])
        if ip_count >= MULTIPLE_IP_THRESHOLD:
            alerts.append({
                "type": "MULTIPLE_IPS",
                "severity": "MEDIUM",
                "user_id": user_id,
                "message": f"User accessed from {ip_count} different IP addresses (threshold: {MULTIPLE_IP_THRESHOLD})",
                "ip_addresses": list(fraud_data["user_ips"][user_id]),
                "timestamp": current_time.isoformat()
            })
    
    # 3. Check for rapid location changes (potential account takeover)
    if location and check_rapid_location_change(user_id, location, current_time):
        alerts.append({
            "type": "RAPID_LOCATION_CHANGE",
            "severity": "HIGH",
            "user_id": user_id,
            "message": f"User changed location rapidly (within {RAPID_LOCATION_CHANGE_MINUTES} minutes)",
            "current_location": location,
            "timestamp": current_time.isoformat()
        })
    
    # 4. Check for high-value purchases
    if event_type == "purchase" and amount >= HIGH_VALUE_THRESHOLD:
        alerts.append({
            "type": "HIGH_VALUE_PURCHASE",
            "severity": "MEDIUM",
            "user_id": user_id,
            "message": f"High-value purchase detected: ${amount:,.2f} (threshold: ${HIGH_VALUE_THRESHOLD:,.2f})",
            "amount": amount,
            "product_id": properties.get("product_id"),
            "timestamp": current_time.isoformat()
        })
        fraud_data["high_value_purchases"].append({
            "user_id": user_id,
            "amount": amount,
            "timestamp": current_time.isoformat(),
            "location": location,
            "ip_address": ip_address
        })
    
    # 5. Check for purchase without prior activity (potential stolen card)
    if event_type == "purchase":
        user_events = fraud_data["user_events"].get(user_id, [])
        if len(user_events) < 3:  # Very few events before purchase
            alerts.append({
                "type": "PURCHASE_WITHOUT_ACTIVITY",
                "severity": "MEDIUM",
                "user_id": user_id,
                "message": f"Purchase with minimal prior activity ({len(user_events)} events)",
                "amount": amount,
                "timestamp": current_time.isoformat()
            })
    
    # 6. Check for rapid purchases (potential card testing)
    if event_type == "purchase":
        recent_purchases = [
            e for e in user_events
            if e[1] == "purchase" and (current_time - e[0]).total_seconds() < 300  # Last 5 minutes
        ]
        if len(recent_purchases) >= 3:
            alerts.append({
                "type": "RAPID_PURCHASES",
                "severity": "HIGH",
                "user_id": user_id,
                "message": f"User made {len(recent_purchases) + 1} purchases in last 5 minutes",
                "purchase_count": len(recent_purchases) + 1,
                "timestamp": current_time.isoformat()
            })
    
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
    
    # Only process purchase and add_to_cart events (as per plan)
    if event_type not in ["purchase", "add_to_cart"]:
        return
    
    # Parse timestamp
    current_time = parse_timestamp(timestamp_str)
    
    # Track user events
    fraud_data["user_events"][user_id].append((
        current_time,
        event_type,
        ip_address,
        location,
        amount
    ))
    
    # Track velocity (add timestamp)
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
        for purchase in fraud_data["high_value_purchases"][:10]:  # Show top 10
            print(f"   User: {purchase['user_id']:15} | ${purchase['amount']:>10,.2f} | {purchase['timestamp']}")
    
    # Users with multiple IPs
    multi_ip_users = {
        user_id: len(ips) for user_id, ips in fraud_data["user_ips"].items()
        if len(ips) >= MULTIPLE_IP_THRESHOLD
    }
    if multi_ip_users:
        print(f"\n🌐 Users with Multiple IPs ({len(multi_ip_users)}):")
        for user_id, ip_count in sorted(multi_ip_users.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"   {user_id:15} : {ip_count} different IPs")
    
    print("\n" + "=" * 80)
    print(f"Total Events Processed: {message_count}")
    print(f"Total Fraud Alerts: {fraud_alerts_count}")
    print("=" * 80 + "\n")


def main():
    """Main consumer loop"""
    global message_count
    
    consumer.subscribe([TOPIC])
    
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
    print("Monitoring for fraud... (Ctrl+C to stop)")
    print()
    
    try:
        while True:
            msg = consumer.poll(1.0)
            
            if msg is None:
                continue
            
            if msg.error():
                print(f"❌ Error: {msg.error()}")
                continue
            
            # Parse message
            try:
                event = json.loads(msg.value().decode("utf-8"))
                user_id = msg.key().decode("utf-8") if msg.key() else None
                
                # Process event for fraud detection
                process_event(event)
                
                message_count += 1
                
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse message: {e}")
                continue
            except Exception as e:
                print(f"❌ Error processing message: {e}")
                continue
                
    except KeyboardInterrupt:
        print("\n\nStopping fraud detector...")
    finally:
        # Print final summary
        if message_count > 0:
            print_summary()
        
        consumer.close()
        print("Fraud detector closed.")


if __name__ == "__main__":
    main()

