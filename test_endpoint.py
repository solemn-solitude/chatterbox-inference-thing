#!/usr/bin/env python3
"""Test script to verify the endpoint generates valid audio files."""

import requests
import os
from pathlib import Path

# Configuration
API_KEY = os.getenv("CHATTERBOX_API_KEY", "your-api-key")
BASE_URL = "http://localhost:20480"
OUTPUT_DIR = Path("test_samples")

def test_synthesize_endpoint(text: str, audio_format: str):
    """Test the synthesize endpoint."""
    print(f"Testing {audio_format.upper()} format...")
    
    # Make request
    response = requests.post(
        f"{BASE_URL}/tts/synthesize",
        json={
            "text": text,
            "voice_mode": "default",
            "audio_format": audio_format,
            "voice_config": {
                "speed": 1.0
            }
        },
        headers={"Authorization": f"Bearer {API_KEY}"},
        stream=True
    )
    
    if response.status_code != 200:
        print(f"  ✗ Request failed: {response.status_code}")
        print(f"    {response.text}")
        return False
    
    # Collect audio data
    audio_data = b""
    for chunk in response.iter_content(chunk_size=8192):
        audio_data += chunk
    
    # Save to file
    extension = "ogg" if audio_format == "vorbis" else audio_format
    filepath = OUTPUT_DIR / f"from_endpoint_fixed.{extension}"
    
    with open(filepath, "wb") as f:
        f.write(audio_data)
    
    file_size = len(audio_data)
    print(f"  ✓ Saved {filepath} ({file_size:,} bytes)")
    
    return True

def main():
    """Run tests."""
    print("Testing synthesize_tts endpoint fix")
    print("=" * 60)
    
    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Test text
    text = "Hello world, this is a test of the text to speech system."
    
    # Test each format
    formats = ["wav", "vorbis"]
    
    for fmt in formats:
        try:
            test_synthesize_endpoint(text, fmt)
        except Exception as e:
            print(f"  ✗ Error testing {fmt}: {e}")
    
    print()
    print("Verification:")
    print("  Run: file test_samples/from_endpoint_fixed.*")
    print("  The files should now have proper headers (RIFF/Ogg)")

if __name__ == "__main__":
    main()
