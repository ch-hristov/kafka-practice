"""
Unit tests for analytics processing functions
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add session_5 to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from analytics_processor import (
    extract_metrics,
    calculate_conversion_rates,
    calculate_avg_session_duration,
    aggregations
)


class TestAnalytics:
    """Test analytics processing functions"""
    
    def setup_method(self):
        """Reset aggregations before each test"""
        aggregations["event_types"].clear()
        aggregations["page_views"].clear()
        aggregations["user_activity"].clear()
        aggregations["funnel"]["page_views"].clear()
        aggregations["funnel"]["clicks"].clear()
        aggregations["funnel"]["searches"].clear()
        aggregations["funnel"]["add_to_cart"].clear()
        aggregations["funnel"]["purchases"].clear()
        aggregations["revenue"]["total"] = 0.0
        aggregations["revenue"]["purchase_count"] = 0
        aggregations["products"].clear()
        aggregations["geography"]["countries"].clear()
        aggregations["geography"]["cities"].clear()
        aggregations["devices"]["types"].clear()
        aggregations["sessions"].clear()
        aggregations["user_journeys"].clear()
    
    def test_extract_metrics_page_view(self):
        """Test extracting metrics from page_view event"""
        event = {
            "event_type": "page_view",
            "user_id": "user-123",
            "session_id": "sess-456",
            "page_url": "/products/laptop",
            "device": {"type": "desktop", "browser": "Chrome", "os": "Windows"},
            "location": {"country": "US", "city": "New York"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "properties": {}
        }
        
        extract_metrics(event)
        
        assert aggregations["event_types"]["page_view"] == 1
        assert aggregations["page_views"]["/products/laptop"] == 1
        assert aggregations["user_activity"]["user-123"] == 1
        assert "user-123" in aggregations["funnel"]["page_views"]
    
    def test_extract_metrics_purchase(self):
        """Test extracting metrics from purchase event"""
        event = {
            "event_type": "purchase",
            "user_id": "user-123",
            "session_id": "sess-456",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "properties": {
                "cart_value": 999.99,
                "product_id": "PROD-001",
                "product_name": "Laptop"
            }
        }
        
        extract_metrics(event)
        
        assert aggregations["event_types"]["purchase"] == 1
        assert aggregations["revenue"]["total"] == 999.99
        assert aggregations["revenue"]["purchase_count"] == 1
        assert "user-123" in aggregations["funnel"]["purchases"]
    
    def test_calculate_conversion_rates(self):
        """Test conversion rate calculation"""
        # Setup funnel data
        aggregations["funnel"]["page_views"].add("user-1")
        aggregations["funnel"]["page_views"].add("user-2")
        aggregations["funnel"]["page_views"].add("user-3")
        
        aggregations["funnel"]["clicks"].add("user-1")
        aggregations["funnel"]["clicks"].add("user-2")
        
        aggregations["funnel"]["purchases"].add("user-1")
        
        rates = calculate_conversion_rates()
        
        assert rates["page_view_to_click"] == pytest.approx(66.67, rel=0.01)
        assert rates["page_view_to_purchase"] == pytest.approx(33.33, rel=0.01)
        assert rates["click_to_purchase"] == pytest.approx(50.0, rel=0.01)
    
    def test_calculate_avg_session_duration(self):
        """Test average session duration calculation"""
        from datetime import timedelta
        current_time = datetime.now(timezone.utc)
        
        # Create sessions with different durations
        aggregations["sessions"]["sess-1"] = {
            "start_time": current_time - timedelta(seconds=60),
            "events": 5,
            "user_id": "user-1"
        }
        
        aggregations["sessions"]["sess-2"] = {
            "start_time": current_time - timedelta(seconds=120),
            "events": 10,
            "user_id": "user-2"
        }
        
        avg_duration = calculate_avg_session_duration()
        
        # Should be around 90 seconds (average of 60 and 120)
        assert avg_duration > 80
        assert avg_duration < 100

