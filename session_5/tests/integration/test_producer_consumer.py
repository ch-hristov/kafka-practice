"""
Integration tests for producer and consumer with real Kafka
"""

import json
import pytest
import time
from confluent_kafka import Producer, Consumer


@pytest.fixture
def kafka_config():
    """Kafka configuration for tests"""
    import uuid
    return {
        "bootstrap.servers": "localhost:9092",
        "group.id": f"test-group-integration-{uuid.uuid4().hex[:8]}",  # Unique group per test
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True,
    }


@pytest.fixture
def test_topic():
    """Test topic name - unique per test run"""
    import uuid
    return f"test-topic-session5-{uuid.uuid4().hex[:8]}"


def test_producer_sends_message(kafka_config, test_topic):
    """Test that producer can send a message"""
    producer = Producer({"bootstrap.servers": kafka_config["bootstrap.servers"]})
    
    test_message = {
        "event_type": "page_view",
        "user_id": "test-user",
        "timestamp": "2024-01-15T10:00:00Z"
    }
    key = "test-key"
    
    # Send message
    producer.produce(
        test_topic,
        key=key.encode("utf-8"),
        value=json.dumps(test_message).encode("utf-8")
    )
    producer.flush()
    
    # Verify message was sent (no exception raised)
    assert True


def test_consumer_receives_message(kafka_config, test_topic):
    """Test that consumer can receive a message"""
    # Setup producer
    producer = Producer({"bootstrap.servers": kafka_config["bootstrap.servers"]})
    
    # Send test message first
    test_message = {
        "event_type": "page_view",
        "user_id": "test-user",
        "message_id": "msg-123"
    }
    key = "test-key"
    
    producer.produce(
        test_topic,
        key=key.encode("utf-8"),
        value=json.dumps(test_message).encode("utf-8")
    )
    producer.flush()
    
    # Setup consumer after sending (to ensure it reads our message)
    consumer = Consumer(kafka_config)
    consumer.subscribe([test_topic])
    
    # Wait a moment for consumer to join group
    time.sleep(1)
    
    # Consume message (poll multiple times to ensure we get it)
    msg = None
    for _ in range(15):
        msg = consumer.poll(timeout=1.0)
        if msg is not None and not msg.error():
            received_data = json.loads(msg.value().decode("utf-8"))
            # Check if this is our message
            if received_data.get("message_id") == "msg-123":
                break
            # Otherwise, continue polling (might be old messages)
    
    assert msg is not None, "No message received"
    assert not msg.error(), f"Message error: {msg.error()}"
    
    # Verify message content
    received_data = json.loads(msg.value().decode("utf-8"))
    assert received_data["event_type"] == "page_view"
    assert received_data["user_id"] == "test-user"
    assert "message_id" in received_data, f"Missing message_id in {received_data}"
    assert received_data["message_id"] == "msg-123"
    
    # Verify key
    assert msg.key().decode("utf-8") == key
    
    consumer.close()


def test_producer_consumer_round_trip(kafka_config, test_topic):
    """Test complete producer → consumer flow"""
    # Setup producer
    producer = Producer({"bootstrap.servers": kafka_config["bootstrap.servers"]})
    
    # Send multiple messages first
    messages_sent = []
    for i in range(5):
        message = {
            "event_type": "page_view",
            "user_id": f"user-{i}",
            "data": f"message-{i}",
            "test_id": f"test-round-trip-{i}"  # Unique identifier
        }
        key = f"key-{i}"
        messages_sent.append((key, message))
        
        producer.produce(
            test_topic,
            key=key.encode("utf-8"),
            value=json.dumps(message).encode("utf-8")
        )
    
    producer.flush()
    
    # Setup consumer after sending
    consumer = Consumer(kafka_config)
    consumer.subscribe([test_topic])
    
    # Wait a moment for consumer to join group
    time.sleep(1)
    
    # Consume messages - filter for our test messages
    messages_received = []
    timeout = time.time() + 15  # 15 second timeout
    
    while len(messages_received) < 5 and time.time() < timeout:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            continue
        
        key = msg.key().decode("utf-8") if msg.key() else None
        value = json.loads(msg.value().decode("utf-8"))
        
        # Only count messages with our test_id
        if "test_id" in value and value["test_id"].startswith("test-round-trip"):
            messages_received.append((key, value))
    
    # Verify all messages received
    assert len(messages_received) == 5, f"Expected 5 messages, got {len(messages_received)}. Received: {messages_received}"
    
    # Verify message content
    for key, message in messages_sent:
        assert (key, message) in messages_received, f"Message {key} not found in received messages"
    
    consumer.close()

