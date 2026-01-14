"""Example usage of Chatterbox Inference client."""

import sys
import os

# Add client to path if not installed
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../client/src'))

from chatterbox_inference_client import Client
from chatterbox_inference_client.schemas import VoiceConfig


def example_http_client():
    """Example: HTTP client usage."""
    print("=" * 60)
    print("HTTP Client Example")
    print("=" * 60)
    
    # Create HTTP client
    client = Client.http(
        server_url="http://localhost:20480",
        api_key=os.getenv("CHATTERBOX_API_KEY", "your-api-key")
    )
    
    try:
        # Health check
        print("\n1. Health Check:")
        health = client.health_check()
        print(f"   Status: {health['status']}")
        
        # Synthesize speech with custom voice config
        print("\n2. Synthesizing speech...")
        audio_data = b""
        chunk_count = 0
        
        # Create voice config with custom settings
        voice_config = VoiceConfig(
            voice_name="default",
            speed=1.0,
            temperature=0.8,
            exaggeration=0.5,
            cfg_weight=0.5
        )
        
        for chunk in client.synthesize(
            text="Hello! This is a test of the Chatterbox TTS system.",
            voice_mode="default",
            voice_config=voice_config,
            audio_format="pcm"
        ):
            audio_data += chunk
            chunk_count += 1
        
        print(f"   Received {chunk_count} chunks, {len(audio_data)} total bytes")
        
        # Save to file
        output_file = "output_http.pcm"
        with open(output_file, "wb") as f:
            f.write(audio_data)
        print(f"   Saved to {output_file}")
        
        # List voices
        print("\n3. Listing voices:")
        voices = client.list_voices()
        print(f"   Total voices: {voices.get('total', 0)}")
        
    finally:
        client.close()
        print("\nHTTP client closed.\n")


def example_zmq_client():
    """Example: ZMQ client usage."""
    print("=" * 60)
    print("ZMQ Client Example")
    print("=" * 60)
    
    # Create ZMQ client
    client = Client.zmq(
        server_url="tcp://localhost:5555",
        api_key=os.getenv("CHATTERBOX_API_KEY", "your-api-key")
    )
    
    try:
        # Health check
        print("\n1. Health Check:")
        health = client.health_check()
        print(f"   Status: {health['status']}")
        print(f"   Model loaded: {health.get('model_loaded', 'unknown')}")
        
        # Synthesize speech with higher speed and expressiveness
        print("\n2. Synthesizing speech via ZMQ...")
        audio_data = b""
        chunk_count = 0
        
        # Custom voice config with increased speed and exaggeration
        voice_config = VoiceConfig(
            speed=1.2,
            exaggeration=0.7,
            temperature=0.9
        )
        
        for chunk in client.synthesize(
            text="This is streaming over ZMQ for high performance!",
            voice_mode="default",
            voice_config=voice_config,
            audio_format="pcm"
        ):
            audio_data += chunk
            chunk_count += 1
        
        print(f"   Received {chunk_count} chunks, {len(audio_data)} total bytes")
        
        # Save to file
        output_file = "output_zmq.pcm"
        with open(output_file, "wb") as f:
            f.write(audio_data)
        print(f"   Saved to {output_file}")
        
        # List voices
        print("\n3. Listing voices:")
        voices = client.list_voices()
        print(f"   Total voices: {voices.get('total', 0)}")
        
    finally:
        client.close()
        print("\nZMQ client closed.\n")


def example_context_manager():
    """Example: Using context manager."""
    print("=" * 60)
    print("Context Manager Example")
    print("=" * 60)
    
    api_key = os.getenv("CHATTERBOX_API_KEY", "your-api-key")
    
    # Automatically handles cleanup
    with Client.http("http://localhost:20480", api_key) as client:
        print("\n1. Quick synthesis with auto-cleanup:")
        
        total_bytes = 0
        for chunk in client.synthesize("Context manager handles cleanup!"):
            total_bytes += len(chunk)
        
        print(f"   Generated {total_bytes} bytes")
    
    print("   Client automatically closed\n")


def main():
    """Run all examples."""
    print("\nChatterbox Inference Client Examples")
    print("=" * 60)
    print("\nMake sure the server is running!")
    print("  FastAPI: chatterbox-inference run fastapi")
    print("  ZMQ:     chatterbox-inference run zmq")
    print()
    
    # Check API key
    if not os.getenv("CHATTERBOX_API_KEY"):
        print("WARNING: CHATTERBOX_API_KEY not set!")
        print("Using default 'your-api-key' - this may fail.\n")
    
    try:
        # Run examples
        example_context_manager()
        example_http_client()
        
        # Only run ZMQ if server is available
        print("Attempting ZMQ example (will skip if server not running)...")
        try:
            example_zmq_client()
        except Exception as e:
            print(f"ZMQ example skipped: {e}\n")
        
        print("=" * 60)
        print("Examples completed successfully!")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
