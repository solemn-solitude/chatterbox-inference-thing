"""Entry point for running TTS Inference directly.

This allows running the application with:
    python main.py <command>

Or when installed:
    tts-inference <command>
"""

from src.tts_inference.cli import main

if __name__ == "__main__":
    main()
