"""
Unit tests for event generation functions in activity_producer.py
"""

import pytest
import sys
from pathlib import Path

# Add session_5 to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from activity_producer import (
    generate_user_id,
    select_event_type,
    get_or_create_session,
    generate_event_properties,
    EVENT_TYPES
)


class TestEventGeneration:
    """Test event generation functions"""
    
    def test_generate_user_id(self):
        """Test user ID generation"""
        user_id = generate_user_id()
        assert user_id.startswith("user-")
        assert len(user_id) > 5
        # Should be numeric after "user-"
        assert user_id[5:].isdigit()
    
    def test_select_event_type(self):
        """Test event type selection follows distribution"""
        event_types = []
        for _ in range(1000):
            event_type = select_event_type()
            event_types.append(event_type)
            assert event_type in EVENT_TYPES.keys()
        
        # Check distribution (roughly)
        page_views = event_types.count("page_view")
        assert page_views > 500  # Should be around 60%
        assert page_views < 700
    
    def test_get_or_create_session(self):
        """Test session creation and retrieval"""
        user_id = "test-user-123"
        
        # Clear any existing session
        from activity_producer import active_sessions
        if user_id in active_sessions:
            del active_sessions[user_id]
        
        # First call creates session
        session1 = get_or_create_session(user_id)
        assert "session_id" in session1
        assert session1["current_page"] == "/"
        assert session1["cart_value"] == 0.0
        assert session1["events_in_session"] == 0
        assert session1["searched"] == False
        assert session1["added_to_cart"] == False
        
        # Second call returns same session
        session2 = get_or_create_session(user_id)
        assert session1["session_id"] == session2["session_id"]
        assert session1 is session2  # Should be same object
    
    def test_get_or_create_session_multiple_users(self):
        """Test session creation for multiple users"""
        from activity_producer import active_sessions
        
        user1 = "user-1"
        user2 = "user-2"
        
        # Clear existing
        for uid in [user1, user2]:
            if uid in active_sessions:
                del active_sessions[uid]
        
        session1 = get_or_create_session(user1)
        session2 = get_or_create_session(user2)
        
        assert session1["session_id"] != session2["session_id"]
        assert session1 != session2
    
    def test_generate_event_properties_page_view(self):
        """Test event properties generation for page_view"""
        session = {
            "current_page": "/",
            "cart_value": 0.0,
            "events_in_session": 0,
            "searched": False,
            "added_to_cart": False
        }
        
        properties = generate_event_properties("page_view", session)
        
        assert "page_url" in properties
        assert properties["page_url"] == session["current_page"]
    
    def test_generate_event_properties_search(self):
        """Test event properties generation for search"""
        session = {
            "current_page": "/",
            "cart_value": 0.0,
            "events_in_session": 0,
            "searched": False,
            "added_to_cart": False
        }
        
        properties = generate_event_properties("search", session)
        
        assert "search_query" in properties
        assert session["searched"] == True
    
    def test_generate_event_properties_add_to_cart(self):
        """Test event properties generation for add_to_cart"""
        session = {
            "current_page": "/",
            "cart_value": 0.0,
            "events_in_session": 0,
            "searched": False,
            "added_to_cart": False
        }
        
        initial_cart_value = session["cart_value"]
        properties = generate_event_properties("add_to_cart", session)
        
        assert "product_id" in properties
        assert "product_name" in properties
        assert "price" in properties
        assert "cart_value" in properties
        assert session["cart_value"] > initial_cart_value
        assert session["added_to_cart"] == True
    
    def test_generate_event_properties_purchase(self):
        """Test event properties generation for purchase"""
        session = {
            "current_page": "/",
            "cart_value": 100.0,
            "events_in_session": 5,
            "searched": True,
            "added_to_cart": True
        }
        
        properties = generate_event_properties("purchase", session)
        
        assert "cart_value" in properties
        # Cart should be cleared after purchase
        assert session["cart_value"] == 0.0

