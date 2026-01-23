#!/usr/bin/env python3
"""Test script to verify ZMQ configuration changes."""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from tts_inference.utils.config import CONFIG

print("=" * 60)
print("ZMQ Configuration Test")
print("=" * 60)
print()

# Test 1: Check default input address
print("Test 1: Default Input Address")
print(f"  TTS_INPUT_ADDRESS: {os.getenv('TTS_INPUT_ADDRESS', 'Not set')}")
print(f"  CONFIG.zmq_input_address: {CONFIG.zmq_input_address}")
print(f"  Expected: tcp://localhost:20501")
print(f"  ✓ PASS" if CONFIG.zmq_input_address == "tcp://localhost:20501" else f"  ✗ FAIL")
print()

# Test 2: Check PUB address
print("Test 2: PUB Address")
print(f"  TTS_PUB_ADDRESS: {os.getenv('TTS_PUB_ADDRESS', 'Not set')}")
print(f"  CONFIG.zmq_pub_address: {CONFIG.zmq_pub_address}")
print(f"  Expected: '' (empty string)")
print(f"  ✓ PASS" if CONFIG.zmq_pub_address == "" else f"  ✗ FAIL")
print()

# Test 3: Check with environment variables set
print("Test 3: With Environment Variables")
os.environ['TTS_INPUT_ADDRESS'] = 'tcp://127.0.0.1:9999'
os.environ['TTS_PUB_ADDRESS'] = 'tcp://127.0.0.1:9998'

# Reload config
from tts_inference.utils.config import Config
test_config = Config()

print(f"  TTS_INPUT_ADDRESS: {os.getenv('TTS_INPUT_ADDRESS')}")
print(f"  test_config.zmq_input_address: {test_config.zmq_input_address}")
print(f"  ✓ PASS" if test_config.zmq_input_address == "tcp://127.0.0.1:9999" else f"  ✗ FAIL")
print()
print(f"  TTS_PUB_ADDRESS: {os.getenv('TTS_PUB_ADDRESS')}")
print(f"  test_config.zmq_pub_address: {test_config.zmq_pub_address}")
print(f"  ✓ PASS" if test_config.zmq_pub_address == "tcp://127.0.0.1:9998" else f"  ✗ FAIL")
print()

print("=" * 60)
print("All configuration tests completed!")
print("=" * 60)
