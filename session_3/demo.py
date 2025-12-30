"""
Simple Demo Script for Client Presentation

Shows the system working with clear, visual output.
Run this to demonstrate the user activity tracking system.
"""

import subprocess
import sys
import time
import os

def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")

def print_step(step_num, description):
    """Print a step description"""
    print(f"\n📌 Step {step_num}: {description}")
    print("-" * 80)

def main():
    """Main demo script"""
    print_header("🚀 User Activity Tracking System - Demo")
    
    print("""
This demo will show you:
1. Real-time event generation (simulating user activity)
2. Analytics processing (conversion rates, revenue, popular pages)
3. Fraud detection (suspicious activity alerts)

The system processes events in real-time, showing you:
- How many users are active
- What pages they're viewing
- Conversion rates (visitors → customers)
- Revenue tracking
- Fraud alerts
    """)
    
    input("Press Enter to start the demo...")
    
    print_step(1, "Starting Analytics Processor")
    print("This will analyze all user activity and show you:")
    print("  • Conversion funnel (page views → purchases)")
    print("  • Revenue metrics")
    print("  • Popular pages and products")
    print("  • Geographic distribution")
    print("\nStarting analytics processor in background...")
    
    # Note: In a real demo, you'd start these in separate terminals
    # For this script, we'll just show instructions
    print("\n💡 To run the full demo:")
    print("   Terminal 1: python session_3/analytics_processor.py")
    print("   Terminal 2: python session_3/fraud_detector.py")
    print("   Terminal 3: python session_3/activity_producer.py")
    
    print("\n" + "=" * 80)
    print("Demo instructions displayed above.")
    print("Run the commands in separate terminals to see the full demo.")
    print("=" * 80)

if __name__ == "__main__":
    main()

