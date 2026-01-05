"""Click CLI for Chatterbox Inference."""

import click
import asyncio
import logging
import sys
import uvicorn

from .server import run_zmq_server
from .utils.config import config


def setup_logging(log_level: str):
    """Setup logging configuration.
    
    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR)
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Chatterbox Inference - TTS streaming server."""
    pass


@main.group()
def run():
    """Run the server in different modes."""
    pass


@run.command()
@click.option(
    '--host',
    default=None,
    help='Host to bind to (default: from env or 0.0.0.0)'
)
@click.option(
    '--port',
    default=None,
    type=int,
    help='Port to bind to (default: from env or 20480)'
)
@click.option(
    '--log-level',
    default=None,
    help='Log level (default: from env or INFO)'
)
@click.option(
    '--reload',
    is_flag=True,
    help='Enable auto-reload for development'
)
def fastapi(host, port, log_level, reload):
    """Run FastAPI HTTP/WebSocket server."""
    # Apply config overrides
    if log_level:
        config.log_level = log_level
    if host:
        config.fastapi_host = host
    if port:
        config.fastapi_port = port
    
    # Setup logging
    setup_logging(config.log_level)
    
    logger = logging.getLogger(__name__)
    logger.info("Starting Chatterbox Inference in FastAPI mode")
    logger.info(f"Host: {config.fastapi_host}, Port: {config.fastapi_port}")
    
    # Check API key
    try:
        config.validate_api_key()
        logger.info("API key validation successful")
    except ValueError as e:
        logger.error(str(e))
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    
    # Run uvicorn server
    uvicorn.run(
        "chatterbox_inference.server.fastapi_server:app",
        host=config.fastapi_host,
        port=config.fastapi_port,
        reload=reload,
        log_level=config.log_level.lower(),
    )


@run.command()
@click.option(
    '--host',
    default=None,
    help='Host to bind to (default: from env or *)'
)
@click.option(
    '--port',
    default=None,
    type=int,
    help='Port to bind to (default: from env or 5555)'
)
@click.option(
    '--log-level',
    default=None,
    help='Log level (default: from env or INFO)'
)
def zmq(host, port, log_level):
    """Run ZMQ ROUTER server."""
    # Apply config overrides
    if log_level:
        config.log_level = log_level
    if host:
        config.zmq_host = host
    if port:
        config.zmq_port = port
    
    # Setup logging
    setup_logging(config.log_level)
    
    logger = logging.getLogger(__name__)
    logger.info("Starting Chatterbox Inference in ZMQ mode")
    logger.info(f"Host: {config.zmq_host}, Port: {config.zmq_port}")
    
    # Check API key
    try:
        config.validate_api_key()
        logger.info("API key validation successful")
    except ValueError as e:
        logger.error(str(e))
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    
    # Run ZMQ server
    try:
        asyncio.run(run_zmq_server(config.zmq_host, config.zmq_port))
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


@main.command()
def config_info():
    """Display current configuration."""
    click.echo("Chatterbox Inference Configuration")
    click.echo("=" * 40)
    click.echo(f"Voice Directory: {config.voice_dir}")
    click.echo(f"Voice Audio Directory: {config.voice_audio_dir}")
    click.echo(f"Database Path: {config.database_path}")
    click.echo(f"API Key Configured: {'Yes' if config.api_key else 'No'}")
    click.echo(f"\nFastAPI Settings:")
    click.echo(f"  Host: {config.fastapi_host}")
    click.echo(f"  Port: {config.fastapi_port}")
    click.echo(f"\nZMQ Settings:")
    click.echo(f"  Host: {config.zmq_host}")
    click.echo(f"  Port: {config.zmq_port}")
    click.echo(f"\nLog Level: {config.log_level}")
    click.echo("=" * 40)


@main.command()
@click.option(
    '--text',
    default="Hello world, this is a test of the text to speech system.",
    help='Text to synthesize'
)
@click.option(
    '--output-dir',
    default="./test_samples",
    help='Directory to save test files'
)
@click.option(
    '--turbo',
    is_flag=True,
    help='Use turbo model'
)
def test_gen(text, output_dir, turbo):
    """Generate test audio files in all formats for debugging."""
    import numpy as np
    from pathlib import Path
    from .tts import tts_engine
    from .utils.audio_utils import AudioStreamEncoder
    
    setup_logging("INFO")
    logger = logging.getLogger(__name__)
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    click.echo(f"Generating test samples...")
    click.echo(f"Text: {text}")
    click.echo(f"Output directory: {output_path}")
    click.echo(f"Turbo mode: {turbo}")
    click.echo()
    
    async def generate():
        # Initialize engine
        click.echo("Loading TTS model...")
        await tts_engine.initialize()
        click.echo(f"✓ Model loaded (sample rate: {tts_engine.sample_rate})")
        click.echo()
        
        # Generate audio (collect all chunks)
        click.echo("Synthesizing audio...")
        chunks = []
        async for chunk, sr in tts_engine.synthesize_streaming(
            text=text,
            use_turbo=turbo
        ):
            chunks.append(chunk)
        
        full_audio = np.concatenate(chunks)
        sample_rate = tts_engine.sample_rate
        
        click.echo(f"✓ Generated {len(full_audio)} samples at {sample_rate}Hz")
        click.echo(f"  Duration: {len(full_audio) / sample_rate:.2f} seconds")
        click.echo()
        
        # Save in all formats
        formats = ["pcm", "wav", "vorbis"]
        for fmt in formats:
            try:
                click.echo(f"Encoding {fmt.upper()}...")
                encoder = AudioStreamEncoder(fmt, sample_rate)
                
                # Accumulate (for WAV/Vorbis) or encode directly (for PCM)
                for chunk in chunks:
                    encoder.encode_chunk(chunk)
                
                # Finalize encoding
                encoded_data = encoder.finalize()
                
                # For PCM, we need to encode since finalize returns empty
                if fmt == "pcm":
                    encoded_data = encoder.encode_complete(full_audio)
                
                # Save file
                filename = f"test.{fmt if fmt != 'vorbis' else 'ogg'}"
                filepath = output_path / filename
                
                with open(filepath, 'wb') as f:
                    f.write(encoded_data)
                
                file_size = len(encoded_data)
                click.echo(f"✓ Saved {filepath} ({file_size:,} bytes)")
                
            except Exception as e:
                click.echo(f"✗ Failed to encode {fmt}: {e}", err=True)
                logger.error(f"Error encoding {fmt}", exc_info=True)
        
        click.echo()
        click.echo("Done! Check the files with:")
        click.echo(f"  file {output_path}/*")
        click.echo(f"  ffplay {output_path}/test.wav")
    
    try:
        asyncio.run(generate())
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        logger.error("Test generation failed", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
