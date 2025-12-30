# Session 3: User Activity Tracking System

## 🎯 What This Does

A **real-time user activity tracking and analytics system** - like Google Analytics, but you own the data and can customize everything.

**Perfect for:**
- Understanding user behavior
- Tracking conversions and revenue
- Detecting fraud
- Real-time business insights

---

## 🚀 Quick Start Demo

### Step 1: Start Kafka
```bash
# Make sure Kafka is running
docker ps | grep kafka
```

### Step 2: Create Topic
```bash
./scripts/create_user_activities_topic.sh
```

### Step 3: Run the System (3 Terminals)

**Terminal 1 - Analytics Processor:**
```bash
python session_3/analytics_processor.py
```
*Shows: Conversion rates, revenue, popular pages*

**Terminal 2 - Fraud Detector:**
```bash
python session_3/fraud_detector.py
```
*Shows: Fraud alerts, suspicious activity*

**Terminal 3 - Event Producer:**
```bash
python session_3/activity_producer.py
```
*Generates: User activity events*

---

## 📊 What You'll See

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

### Producer Metrics (Every 10 events)
```
📊 Events sent: 50 | Rate: 10.0 events/sec | Active sessions: 5
✅ Delivered to user-activities [partition=2] @ offset 45
```

---

## 🔧 Configuration

### Environment Variables

Edit `.env` file or set environment variables:

```bash
# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_ACTIVITIES_TOPIC=user-activities

# Producer Settings
EVENTS_PER_SECOND=10          # How many events per second
VERBOSE=false                 # Show delivery confirmations

# Consumer Settings
KAFKA_ANALYTICS_GROUP=analytics-processors
KAFKA_FRAUD_GROUP=fraud-detectors
STATS_INTERVAL=50             # Print stats every N messages

# Logging
LOG_LEVEL=INFO               # DEBUG, INFO, WARNING, ERROR
```

---

## 📈 Key Features

### ✅ Real-time Processing
- Events processed as they happen
- < 1 second latency from event to analytics

### ✅ Multiple Consumers
- Analytics processor (business insights)
- Fraud detector (security)
- Both process same data independently

### ✅ Comprehensive Analytics
- Conversion funnel tracking
- Revenue metrics
- Popular pages/products
- Geographic distribution
- Device analytics

### ✅ Fraud Detection
- High velocity detection
- Multiple IP tracking
- Rapid location changes
- High-value purchase alerts

### ✅ Observability
- Structured logging (see `logs/` directory)
- Metrics collection (events/sec, processing time)
- Error tracking

---

## 📁 Files

- `activity_producer.py` - Generates user activity events
- `analytics_processor.py` - Analyzes events and shows metrics
- `fraud_detector.py` - Detects suspicious activity
- `CLIENT_DEMO_GUIDE.md` - Detailed demo guide for presentations
- `USER_ACTIVITY_PLAN.md` - System architecture and design

---

## 🎬 For Client Presentations

See `CLIENT_DEMO_GUIDE.md` for:
- Business value explanation
- Demo script
- Talking points
- Common questions & answers

---

## 🔍 Understanding the Output

### Analytics Metrics Explained

**Conversion Funnel:**
- Shows how many users progress through: Page View → Click → Purchase
- Lower conversion = opportunity to optimize

**Revenue Metrics:**
- Total revenue from all purchases
- Average order value = total revenue / number of purchases

**Popular Pages:**
- Which pages get the most views
- Helps identify what content/products users care about

### Fraud Alerts Explained

**HIGH_VELOCITY:**
- User acting too fast (possibly a bot)
- Threshold: 5+ events per minute

**HIGH_VALUE_PURCHASE:**
- Large purchase detected
- Threshold: $500+ (configurable)

**RAPID_LOCATION_CHANGE:**
- User changed location very quickly
- Could indicate account takeover

---

## 🎯 Business Value

### For Marketing
- Real-time campaign performance
- Conversion optimization insights
- User segmentation data

### For Product
- Feature usage tracking
- User journey analysis
- A/B testing support

### For Security
- Fraud prevention
- Account security monitoring
- Risk scoring

### For Business Intelligence
- Revenue tracking
- Geographic insights
- Trend analysis

---

## 🚀 Next Steps

1. **Run the demo** - See it in action
2. **Customize metrics** - Add your own analytics
3. **Add more consumers** - Dashboard, notifications, etc.
4. **Scale up** - Increase event rate to see performance
5. **Production** - Add monitoring, alerting, scaling

---

This system demonstrates the power of event-driven architecture for real-time analytics! 🎉

