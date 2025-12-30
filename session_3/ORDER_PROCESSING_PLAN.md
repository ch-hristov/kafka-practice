# User Activity Tracking System - Kafka Showcase

## Why This System Highlights Kafka's Strengths

Kafka excels at:
- ✅ **High-throughput event streaming** - Millions of events per second
- ✅ **Multiple independent consumers** - Same data, different processing
- ✅ **Real-time processing** - Low latency event handling
- ✅ **Decoupling** - Producers don't know about consumers
- ✅ **Replay capability** - Replay events from any point
- ✅ **Scalability** - Horizontal scaling with partitions

**User activity tracking** is a perfect showcase because it demonstrates all of these!

---

## System Overview

A user activity tracking system that:
- **Producer**: Emits high-volume user activity events (clicks, page views, purchases)
- **Multiple Consumers**: Each processes the same data for different purposes
  - Analytics aggregator
  - Fraud detector
  - Real-time dashboard
  - User behavior analyzer

---

## 1. Topic Design

### Single Topic: `user-activities`
- **Partitions**: 6 (for high throughput and parallel processing)
- **Replication Factor**: 1 (development)
- **Key**: `user_id` (ensures all events for same user go to same partition)
- **Retention**: 7 days (or configurable)
- **Purpose**: All user activity events stream here

**Why this design:**
- Multiple partitions = parallel processing = high throughput
- User ID as key = all user events in same partition = easier user-level analysis

---

## 2. Event Schema

### User Activity Event
```json
{
  "event_id": "uuid",
  "timestamp": "2024-01-15T10:30:45.123Z",
  "user_id": "user-12345",
  "session_id": "sess-abc123",
  "event_type": "page_view" | "click" | "purchase" | "search" | "add_to_cart",
  "page_url": "/products/laptop",
  "referrer": "https://google.com",
  "user_agent": "Mozilla/5.0...",
  "ip_address": "192.168.1.1",
  "properties": {
    "product_id": "PROD-001",
    "product_name": "Laptop",
    "price": 999.99,
    "category": "electronics",
    "search_query": "laptop deals",
    "cart_value": 999.99
  },
  "device": {
    "type": "desktop" | "mobile" | "tablet",
    "os": "Windows" | "iOS" | "Android",
    "browser": "Chrome" | "Safari" | "Firefox"
  },
  "location": {
    "country": "US",
    "city": "New York",
    "timezone": "America/New_York"
  }
}
```

---

## 3. Producer (`activity_producer.py`)

### Responsibilities
- Generate **high-volume** realistic user activity events
- Simulate real user behavior patterns
- Emit events at configurable rate (e.g., 10-100 events/second)

### Event Types to Generate
1. **page_view** (60%) - Most common
2. **click** (25%) - Button/link clicks
3. **search** (10%) - Search queries
4. **add_to_cart** (3%) - Add items to cart
5. **purchase** (2%) - Completed purchases

### Features
- **Realistic patterns**: 
  - Users browse multiple pages in sessions
  - Search before purchasing
  - Add to cart before purchase
- **High throughput**: Generate many events quickly
- **User sessions**: Simulate user sessions with multiple events
- **Geographic diversity**: Different countries, cities
- **Device diversity**: Desktop, mobile, tablet

### Example Output
```python
# Generates events like:
{
  "event_type": "page_view",
  "user_id": "user-12345",
  "session_id": "sess-abc123",
  "page_url": "/products/laptop",
  "timestamp": "2024-01-15T10:30:45.123Z"
}
```

---

## 4. Consumers (Multiple Independent Processing)

### Consumer 1: Analytics Aggregator (`analytics_processor.py`)
**Consumer Group**: `analytics-processors`  
**Topic**: `user-activities`

**Processing:**
- **Filter**: All event types
- **Transform**: 
  - Extract metrics (page views, clicks, conversions)
  - Calculate session duration
  - Identify user journeys
- **Aggregate**:
  - Page views per page (top pages)
  - Events per user (user activity score)
  - Conversion funnel (page_view → click → purchase)
  - Revenue per hour/day
  - Popular products
  - Geographic distribution
- **Output**: Print aggregated stats every 50 messages

**Highlights**: Real-time analytics, time-windowed aggregations

---

### Consumer 2: Fraud Detector (`fraud_detector.py`)
**Consumer Group**: `fraud-detectors`  
**Topic**: `user-activities`

**Processing:**
- **Filter**: Focus on `purchase` and `add_to_cart` events
- **Transform**:
  - Calculate velocity (events per minute per user)
  - Detect suspicious patterns
  - Flag unusual IP addresses
- **Aggregate**:
  - Track purchase velocity per user
  - Monitor high-value purchases
  - Flag suspicious sessions
- **Output**: Alert on suspicious activity

**Highlights**: Real-time fraud detection, pattern recognition

---

### Consumer 3: Real-time Dashboard (`dashboard_processor.py`)
**Consumer Group**: `dashboard-processors`  
**Topic**: `user-activities`

**Processing:**
- **Filter**: Recent events (last 1 minute window)
- **Transform**:
  - Calculate real-time metrics
  - Identify trending pages/products
- **Aggregate**:
  - Active users (last 5 minutes)
  - Events per second
  - Current top pages
  - Live conversion rate
- **Output**: Print dashboard stats every 10 seconds

**Highlights**: Real-time monitoring, low-latency processing

---

### Consumer 4: User Behavior Analyzer (`behavior_analyzer.py`)
**Consumer Group**: `behavior-analyzers`  
**Topic**: `user-activities`

**Processing:**
- **Filter**: All events, grouped by user_id
- **Transform**:
  - Build user journey maps
  - Identify user segments (browsers, buyers, researchers)
  - Calculate engagement scores
- **Aggregate**:
  - User paths (most common navigation flows)
  - Drop-off points (where users leave)
  - Time to purchase
  - Device preferences per user segment
- **Output**: Print behavior insights every 100 messages

**Highlights**: User-level analysis, session tracking

---

## 5. Implementation Structure

```
session_3/
├── activity_producer.py         # Producer: high-volume event generation
├── analytics_processor.py       # Consumer: analytics aggregation
├── fraud_detector.py            # Consumer: fraud detection
├── dashboard_processor.py       # Consumer: real-time dashboard
├── behavior_analyzer.py         # Consumer: user behavior analysis
└── USER_ACTIVITY_PLAN.md        # This file
```

---

## 6. Key Kafka Strengths Demonstrated

### ✅ High Throughput
- Producer generates many events per second
- Multiple partitions handle parallel processing
- Consumers process independently without blocking

### ✅ Multiple Independent Consumers
- 4 different consumer groups process same data
- Each has different purpose (analytics, fraud, dashboard, behavior)
- No interference between consumers

### ✅ Real-time Processing
- Low latency from event to processing
- Real-time aggregations and dashboards
- Immediate fraud detection

### ✅ Decoupling
- Producer doesn't know about consumers
- Can add new consumers without changing producer
- Consumers can be added/removed independently

### ✅ Scalability
- More partitions = more parallel processing
- Can scale consumers horizontally
- Handles high event volumes

### ✅ Replay Capability
- Can replay events from any offset
- Useful for debugging, testing, reprocessing

---

## 7. Example Flow

```
1. User clicks on website
   ↓
2. Producer emits: user activity event → user-activities topic
   ↓
3. Multiple consumers process simultaneously:
   ├─→ Analytics Processor: Aggregates metrics
   ├─→ Fraud Detector: Checks for suspicious activity
   ├─→ Dashboard Processor: Updates real-time dashboard
   └─→ Behavior Analyzer: Tracks user journey
   ↓
4. Each consumer processes independently
   ↓
5. Results: Analytics, fraud alerts, dashboard updates, behavior insights
```

---

## 8. Configuration

### Environment Variables
```bash
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_ACTIVITIES_TOPIC=user-activities
KAFKA_ANALYTICS_GROUP=analytics-processors
KAFKA_FRAUD_GROUP=fraud-detectors
KAFKA_DASHBOARD_GROUP=dashboard-processors
KAFKA_BEHAVIOR_GROUP=behavior-analyzers
```

---

## 9. Implementation Checklist

### Producer
- [ ] Generate realistic user activity events
- [ ] Multiple event types (page_view, click, purchase, etc.)
- [ ] High volume (10-100 events/second)
- [ ] User sessions with multiple events
- [ ] Use user_id as key
- [ ] Realistic data (pages, products, locations, devices)

### Consumer 1: Analytics
- [ ] Filter all event types
- [ ] Transform: Extract metrics
- [ ] Aggregate: Page views, clicks, conversions
- [ ] Aggregate: Revenue, popular products
- [ ] Output: Stats every 50 messages

### Consumer 2: Fraud Detector
- [ ] Filter: Purchase events
- [ ] Transform: Calculate velocity
- [ ] Aggregate: Suspicious patterns
- [ ] Output: Alerts on fraud

### Consumer 3: Dashboard
- [ ] Filter: Recent events (time window)
- [ ] Transform: Real-time metrics
- [ ] Aggregate: Active users, events/sec
- [ ] Output: Dashboard every 10 seconds

### Consumer 4: Behavior Analyzer
- [ ] Filter: All events by user
- [ ] Transform: User journeys
- [ ] Aggregate: Navigation paths, drop-offs
- [ ] Output: Insights every 100 messages

---

## 10. Sample Data

### Event Types
- **page_view**: Homepage, product pages, category pages
- **click**: Buttons, links, product cards
- **search**: Product searches, queries
- **add_to_cart**: Add products to cart
- **purchase**: Completed purchases

### Pages
- `/` (homepage)
- `/products/laptop`
- `/products/mouse`
- `/category/electronics`
- `/search?q=laptop`

### Products
- Laptop ($999.99)
- Mouse ($29.99)
- Keyboard ($79.99)
- Monitor ($299.99)

### Users
- Generate realistic user IDs
- Simulate user sessions
- Different user behaviors (browsers, buyers, researchers)

---

## 11. What This Demonstrates

### Kafka's Core Strengths:
1. **High Throughput**: Many events per second
2. **Multiple Consumers**: Same data, different processing
3. **Real-time**: Low latency processing
4. **Scalability**: Parallel processing with partitions
5. **Decoupling**: Producer independent of consumers
6. **Replay**: Can replay events anytime

### Real-world Use Case:
- Exactly how companies like Netflix, LinkedIn, Uber use Kafka
- Real-time analytics, fraud detection, monitoring
- Event-driven architecture at scale

---

## Next Steps

1. **Start Simple**: Producer + 1 consumer (analytics)
2. **Add Consumers**: One by one to see multiple processing
3. **Scale Up**: Increase event rate to see Kafka handle load
4. **Observe**: Watch how partitions distribute load
5. **Experiment**: Add new consumers, change processing logic

This system perfectly showcases what Kafka is actually good at! 🚀
