"""
Unit tests for fraud detection functions
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add session_5 to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fraud_detector import (
    parse_timestamp,
    calculate_velocity,
    check_rapid_location_change,
    detect_fraud_patterns,
    fraud_data,
    VELOCITY_THRESHOLD,
    RAPID_LOCATION_CHANGE_MINUTES,
    MULTIPLE_IP_THRESHOLD,
    HIGH_VALUE_THRESHOLD
)


class TestFraudDetection:
    """Test fraud detection functions"""
    
    def setup_method(self):
        """Reset fraud data before each test"""
        fraud_data["user_events"].clear()
        fraud_data["user_velocity"].clear()
        fraud_data["user_ips"].clear()
        fraud_data["user_locations"].clear()
        fraud_data["high_value_purchases"].clear()
        fraud_data["alerts"].clear()
    
    def test_parse_timestamp(self):
        """Test timestamp parsing"""
        timestamp_str = "2024-01-15T10:30:00Z"
        dt = parse_timestamp(timestamp_str)
        
        assert isinstance(dt, datetime)
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15
    
    def test_calculate_velocity(self):
        """Test velocity calculation"""
        user_id = "user-123"
        current_time = datetime.now(timezone.utc)
        
        # Add events in the last minute
        fraud_data["user_velocity"][user_id] = [
            current_time - timedelta(seconds=30),
            current_time - timedelta(seconds=45),
            current_time - timedelta(seconds=50),
        ]
        
        velocity = calculate_velocity(user_id, current_time)
        assert velocity == 3
        
        # Add old event (outside 1 minute window)
        fraud_data["user_velocity"][user_id].append(
            current_time - timedelta(minutes=2)
        )
        
        velocity = calculate_velocity(user_id, current_time)
        assert velocity == 3  # Old event shouldn't count
    
    def test_check_rapid_location_change(self):
        """Test rapid location change detection"""
        user_id = "user-123"
        current_time = datetime.now(timezone.utc)
        
        # Add initial location
        fraud_data["user_locations"][user_id] = [
            (current_time - timedelta(minutes=5), {"country": "US", "city": "New York"})
        ]
        
        # Same location - should not trigger
        new_location = {"country": "US", "city": "New York"}
        assert check_rapid_location_change(user_id, new_location, current_time) == False
        
        # Different location but enough time passed (5 min > threshold) - should not trigger
        # Note: RAPID_LOCATION_CHANGE_MINUTES is 10, so 5 minutes is less than threshold
        # Actually, 5 minutes < 10 minutes, so it SHOULD trigger if location changed
        # Let's use a time > 10 minutes to ensure it doesn't trigger
        fraud_data["user_locations"][user_id] = [
            (current_time - timedelta(minutes=15), {"country": "US", "city": "New York"})
        ]
        new_location = {"country": "UK", "city": "London"}
        assert check_rapid_location_change(user_id, new_location, current_time) == False
        
        # Different location and rapid change (< 10 minutes) - should trigger
        fraud_data["user_locations"][user_id] = [
            (current_time - timedelta(minutes=2), {"country": "US", "city": "New York"})
        ]
        new_location = {"country": "UK", "city": "London"}
        assert check_rapid_location_change(user_id, new_location, current_time) == True
    
    def test_detect_fraud_high_velocity(self):
        """Test high velocity fraud detection"""
        user_id = "user-123"
        current_time = datetime.now(timezone.utc)
        
        # Add many events in last minute
        fraud_data["user_velocity"][user_id] = [
            current_time - timedelta(seconds=i) for i in range(VELOCITY_THRESHOLD + 2)
        ]
        
        event = {
            "event_type": "purchase",
            "properties": {"cart_value": 100.0}
        }
        
        alerts = detect_fraud_patterns(user_id, event, current_time)
        
        assert len(alerts) > 0
        assert any(a["type"] == "HIGH_VELOCITY" for a in alerts)
    
    def test_detect_fraud_multiple_ips(self):
        """Test multiple IP fraud detection"""
        user_id = "user-123"
        current_time = datetime.now(timezone.utc)
        
        # Add multiple IPs
        for i in range(MULTIPLE_IP_THRESHOLD):
            fraud_data["user_ips"][user_id].add(f"192.168.1.{i}")
        
        event = {
            "event_type": "purchase",
            "ip_address": "192.168.1.100",
            "properties": {"cart_value": 100.0}
        }
        
        alerts = detect_fraud_patterns(user_id, event, current_time)
        
        assert len(alerts) > 0
        assert any(a["type"] == "MULTIPLE_IPS" for a in alerts)
    
    def test_detect_fraud_high_value_purchase(self):
        """Test high value purchase detection"""
        user_id = "user-123"
        current_time = datetime.now(timezone.utc)
        
        event = {
            "event_type": "purchase",
            "properties": {
                "cart_value": HIGH_VALUE_THRESHOLD + 100.0,
                "product_id": "PROD-001"
            }
        }
        
        alerts = detect_fraud_patterns(user_id, event, current_time)
        
        assert len(alerts) > 0
        assert any(a["type"] == "HIGH_VALUE_PURCHASE" for a in alerts)
        assert any(a["amount"] >= HIGH_VALUE_THRESHOLD for a in alerts)

