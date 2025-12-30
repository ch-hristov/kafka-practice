# Session 5: User Activity Tracking with Testing & Observability

## 🎯 What This Is

A **production-ready user activity tracking system** with comprehensive testing and observability - perfect for client demonstrations and real-world applications.

**Key Features:**
- ✅ Real-time event processing
- ✅ Comprehensive analytics
- ✅ Fraud detection
- ✅ **Unit, Integration & E2E Tests** (quality assurance)
- ✅ **Structured logging** (debugging & monitoring)
- ✅ **Metrics collection** (performance tracking)

---

## 🚀 Quick Start

### 1. Start Kafka
```bash
docker ps | grep kafka  # Verify Kafka is running
```

### 2. Create Topic
```bash
./scripts/create_user_activities_topic.sh
```

### 3. Run the System

**Terminal 1 - Analytics:**
```bash
python session_5/analytics_processor.py
```

**Terminal 2 - Fraud Detector:**
```bash
python session_5/fraud_detector.py
```

**Terminal 3 - Producer:**
```bash
python session_5/activity_producer.py
```

---

## 📊 What You'll See

### Producer Output
```
🚀 User Activity Event Producer
==========================================
📊 Events sent: 50 | Rate: 10.0 events/sec | Active sessions: 5
✅ Delivered to user-activities [partition=2] @ offset 45

📊 Final Statistics
==========================================
Total events sent: 100
Successful deliveries: 100
Average rate: 10.0 events/second
```

### Analytics Output (Every 50 events)
```
📊 ANALYTICS AGGREGATION REPORT
==========================================
📈 Event Type Distribution:
  page_view       :    300 (60.0%)
  click           :    125 (25.0%)
  purchase        :     10 (2.0%)

💰 Revenue Analytics:
  Total Revenue     : $9,999.90
  Avg Order Value   : $999.99

🎯 Conversion Funnel:
  Page Views        :    150 users
  Purchases         :     10 users (6.7% conversion)
```

### Fraud Alerts (Real-time)
```
🔴 FRAUD ALERT [HIGH_VELOCITY] - HIGH SEVERITY
   User ID: user-1234
   User has 8 events in the last minute
```

### Logs (in `logs/` directory)
```json
{"timestamp": "2024-01-15T10:30:45Z", "level": "INFO", "message": "Event delivered", "topic": "user-activities", "partition": 2, "offset": 45}
```

---

## 🧪 Testing Features

### Unit Tests
- Test event generation functions
- Test analytics processing
- Test fraud detection logic
- Fast, isolated tests

### Integration Tests
- Test producer/consumer with real Kafka
- Test message delivery
- Test round-trip flows

### E2E Tests
- Test complete workflows (producer → Kafka → consumer)
- Test multiple consumers
- Test analytics and fraud detection end-to-end

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=session_5 --cov-report=html

# Run specific test type
pytest -m unit          # Unit tests only
pytest -m integration  # Integration tests only
pytest -m e2e          # E2E tests only
```

## 🔍 Observability Features

### Logging
- **Structured logs** in JSON format (easy to parse)
- **Log files** in `logs/` directory (rotated automatically)
- **Log levels**: DEBUG, INFO, WARNING, ERROR
- **Context**: User IDs, event types, processing times

### Metrics
- **Throughput**: Events per second
- **Latency**: Processing time per event
- **Success rates**: Delivery success/failure
- **Business metrics**: Revenue, conversions, purchases

---

## 📁 Files

- `activity_producer.py` - Event producer with logging & metrics
- `analytics_processor.py` - Analytics consumer with logging & metrics
- `fraud_detector.py` - Fraud detection consumer
- `utils/` - Shared utilities (logging, metrics)
- `tests/` - Comprehensive test suite
  - `unit/` - Unit tests
  - `integration/` - Integration tests
  - `e2e/` - End-to-end tests
- `DEMO_GUIDE.md` - Client presentation guide
- `pytest.ini` - Pytest configuration

---

## 🎬 For Client Demos

See `DEMO_GUIDE.md` for:
- Business value explanation
- Step-by-step demo script
- Talking points
- Common questions

---

## 🔧 Configuration

Edit `.env` or set environment variables:

```bash
# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_ACTIVITIES_TOPIC=user-activities

# Producer
EVENTS_PER_SECOND=10

# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR

# Analytics
STATS_INTERVAL=50  # Print stats every N messages
```

---

## 💡 Key Improvements Over Session 3

1. **Comprehensive Testing** - Unit, integration, and E2E tests
2. **Structured Logging** - Easy to search and analyze
3. **Metrics Collection** - Track performance in real-time
4. **Error Tracking** - Know when things go wrong
5. **Production-Ready** - Tests, logging, metrics, error handling
6. **Client-Friendly** - Clear output, easy to understand

---

This is a clean, production-ready version with full testing and observability! 🚀

