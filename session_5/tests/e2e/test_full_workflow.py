"""
End-to-end tests for complete user activity tracking workflow
"""

import json
import pytest
import time
import sys
from pathlib import Path
from confluent_kafka import Producer, Consumer

# Add session_5 to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from activity_producer import generate_user_activity_event
from analytics_processor import extract_metrics, aggregations
from fraud_detector import process_event, fraud_data


@pytest.fixture
def kafka_config():
    """Kafka configuration for tests"""
    return {
        "bootstrap.servers": "localhost:9092",
        "group.id": "test-group-e2e",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True,
    }


@pytest.fixture
def activities_topic():
    """User activities topic name"""
    return "user-activities"


def test_producer_to_analytics_workflow(kafka_config, activities_topic):
    """Test complete workflow: producer → Kafka → analytics consumer"""
    # Setup producer
    producer = Producer({"bootstrap.servers": kafka_config["bootstrap.servers"]})
    
    # Setup analytics consumer
    consumer = Consumer(kafka_config)
    consumer.subscribe([activities_topic])
    
    # Generate and send events
    events_sent = []
    for _ in range(10):
        event, user_id = generate_user_activity_event()
        events_sent.append((user_id, event))
        
        producer.produce(
            activities_topic,
            key=user_id.encode("utf-8"),
            value=json.dumps(event).encode("utf-8")
        )
    
    producer.flush()
    
    # Consume and process events
    events_processed = 0
    timeout = time.time() + 15
    
    while events_processed < 10 and time.time() < timeout:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            continue
        
        event = json.loads(msg.value().decode("utf-8"))
        extract_metrics(event)
        events_processed += 1
    
    # Verify processing
    assert events_processed == 10
    assert sum(aggregations["event_types"].values()) == 10
    
    consumer.close()


def test_producer_to_fraud_detector_workflow(kafka_config, activities_topic):
    """Test complete workflow: producer → Kafka → fraud detector"""
    import uuid
    test_id = f"fraud-test-{uuid.uuid4().hex[:8]}"
    
    # Setup producer
    producer = Producer({"bootstrap.servers": kafka_config["bootstrap.servers"]})
    
    # Setup fraud detector consumer with unique group
    consumer = Consumer({
        **kafka_config,
        "group.id": f"test-group-fraud-e2e-{uuid.uuid4().hex[:8]}"
    })
    consumer.subscribe([activities_topic])
    
    # Wait for consumer to join group
    time.sleep(1)
    
    # Generate and send purchase events (more likely to trigger fraud)
    events_sent = 0
    purchase_events_sent = 0
    for _ in range(20):
        event, user_id = generate_user_activity_event()
        
        # Add test identifier
        event["test_id"] = test_id
        
        # Force some purchase events
        if events_sent < 5:
            event["event_type"] = "purchase"
            if "properties" not in event:
                event["properties"] = {}
            event["properties"]["cart_value"] = 600.0  # High value
            purchase_events_sent += 1
        
        producer.produce(
            activities_topic,
            key=user_id.encode("utf-8"),
            value=json.dumps(event).encode("utf-8")
        )
        events_sent += 1
    
    producer.flush()
    
    # Consume and process events - only our test events
    events_processed = 0
    purchase_events_processed = 0
    timeout = time.time() + 20
    
    while events_processed < 20 and time.time() < timeout:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            continue
        
        event = json.loads(msg.value().decode("utf-8"))
        
        # Only process events from this test
        if event.get("test_id") != test_id:
            continue
        
        events_processed += 1
        
        # Only process purchase and add_to_cart events (as per fraud_detector logic)
        if event.get("event_type") in ["purchase", "add_to_cart"]:
            process_event(event)
            purchase_events_processed += 1
    
    # Verify processing
    assert events_processed == 20, f"Expected 20 events, got {events_processed}"
    
    # Check if fraud data was populated (we forced 5 purchase events)
    # At minimum, purchase events should be processed
    assert purchase_events_processed >= 5, f"Expected at least 5 purchase events, got {purchase_events_processed} (sent {purchase_events_sent})"
    assert len(fraud_data["user_events"]) > 0, "No fraud data collected - purchase events should have been processed"
    
    consumer.close()


def test_multiple_consumers_same_topic(kafka_config, activities_topic):
    """Test multiple consumers processing same topic independently"""
    # Setup producer
    producer = Producer({"bootstrap.servers": kafka_config["bootstrap.servers"]})
    
    # Setup two consumers with different group IDs
    analytics_consumer = Consumer({
        **kafka_config,
        "group.id": "test-analytics-group"
    })
    analytics_consumer.subscribe([activities_topic])
    
    fraud_consumer = Consumer({
        **kafka_config,
        "group.id": "test-fraud-group"
    })
    fraud_consumer.subscribe([activities_topic])
    
    # Send events
    for _ in range(10):
        event, user_id = generate_user_activity_event()
        producer.produce(
            activities_topic,
            key=user_id.encode("utf-8"),
            value=json.dumps(event).encode("utf-8")
        )
    
    producer.flush()
    
    # Both consumers should receive all messages
    analytics_count = 0
    fraud_count = 0
    timeout = time.time() + 15
    
    while (analytics_count < 10 or fraud_count < 10) and time.time() < timeout:
        # Poll analytics consumer
        msg = analytics_consumer.poll(0.5)
        if msg and not msg.error():
            analytics_count += 1
        
        # Poll fraud consumer
        msg = fraud_consumer.poll(0.5)
        if msg and not msg.error():
            fraud_count += 1
    
    # Both should process all messages
    assert analytics_count == 10
    assert fraud_count == 10
    
    analytics_consumer.close()
    fraud_consumer.close()

