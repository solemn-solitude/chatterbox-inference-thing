"""Entry point for running Chatterbox Inference directly.

This allows running the application with:
    python main.py <command>

Or when installed:
    chatterbox-inference <command>
"""

from src.chatterbox_inference.cli import main

if __name__ == "__main__":
    main()
