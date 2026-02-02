#!/usr/bin/env python3
"""
Test script to simulate TradingView webhook calls
"""

import requests
import json
from datetime import datetime

# Configuration
WEBHOOK_URL = "http://localhost:8000/webhook"
WEBHOOK_SECRET = "your-secret-key"  # Change this to your actual secret

def test_entry_long():
    """Test LONG entry signal"""
    payload = {
        "signal_type": "entry_long",
        "symbol": "BTCUSDT",
        "timeframe": "7m",
        "price": 45000.50,
        "momentum": -5.3,
        "vwap": 45100.00,
        "atr_high": 46000.00,
        "atr_low": 44000.00,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    headers = {
        "Authorization": f"Bearer {WEBHOOK_SECRET}",
        "Content-Type": "application/json"
    }
    
    print("Testing LONG entry signal...")
    response = requests.post(WEBHOOK_URL, json=payload, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_exit_long():
    """Test LONG exit signal with TP/SL"""
    payload = {
        "signal_type": "exit_long",
        "symbol": "BTCUSDT",
        "timeframe": "7m",
        "price": 45050.00,
        "momentum": -4.8,
        "tp_price": 45100.00,
        "sl_price": 44000.00,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    headers = {
        "Authorization": f"Bearer {WEBHOOK_SECRET}",
        "Content-Type": "application/json"
    }
    
    print("Testing LONG exit signal...")
    response = requests.post(WEBHOOK_URL, json=payload, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_entry_short():
    """Test SHORT entry signal"""
    payload = {
        "signal_type": "entry_short",
        "symbol": "ETHUSDT",
        "timeframe": "7m",
        "price": 2500.00,
        "momentum": 5.4,
        "vwap": 2490.00,
        "atr_high": 2550.00,
        "atr_low": 2450.00,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    headers = {
        "Authorization": f"Bearer {WEBHOOK_SECRET}",
        "Content-Type": "application/json"
    }
    
    print("Testing SHORT entry signal...")
    response = requests.post(WEBHOOK_URL, json=payload, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_health():
    """Test health endpoint"""
    print("Testing health endpoint...")
    response = requests.get("http://localhost:8000/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

if __name__ == "__main__":
    print("=== TradingView Webhook Test Suite ===\n")
    
    try:
        test_health()
        test_entry_long()
        test_exit_long()
        test_entry_short()
        print("✅ All tests completed!")
    except Exception as e:
        print(f"❌ Error: {e}")
