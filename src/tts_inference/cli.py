"""Click CLI for TTS Inference."""

import sys
import uvicorn
import asyncio
import logging
from textwrap import dedent

import click

from .utils.logging import setup_logging
from .utils.config import CONFIG
from .server import run_zmq_server
from .services import TTSService, DatabaseService


@click.group()
@click.version_option(version="0.1.0")
def main():
    """TTS Inference - TTS streaming server."""
    pass


@main.group()
def run():
    """Run the server in different modes."""
    pass


@run.command()
@click.option("--host", default=None, help="Host to bind to (default: from env or 0.0.0.0)")
@click.option("--port", default=None, type=int, help="Port to bind to (default: from env or 20480)")
@click.option("--log-level", default=None, help="Log level (default: from env or INFO)")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
@click.option("--offload-timeout", default=None, type=int, help="Seconds of inactivity before offloading model (default: 600)")
@click.option("--keep-warm", is_flag=True, help="Keep model loaded in memory (disable auto-offloading)")
def fastapi(host, port, log_level, reload, offload_timeout, keep_warm):
    """Run FastAPI HTTP/WebSocket server."""
    _apply_config_overrides(log_level=log_level, host=host, port=port, offload_timeout=offload_timeout, keep_warm=keep_warm)
    setup_logging(CONFIG.log_level)

    logger = logging.getLogger(__name__)
    logger.info("Starting TTS Inference in FastAPI mode")
    logger.info(f"Host: {CONFIG.fastapi_host}, Port: {CONFIG.fastapi_port}")

    _validate_api_key(logger)

    uvicorn.run(
        "tts_inference.server.fastapi_server:app",
        host=CONFIG.fastapi_host,
        port=CONFIG.fastapi_port,
        reload=reload,
        log_level=CONFIG.log_level.lower(),
    )


@run.command()
@click.option("--input-address", default=None, help="Input ROUTER address")
@click.option("--enable-pub", is_flag=True, help="Enable PUB socket for broadcasting")
@click.option("--log-level", default=None, help="Log level (default: from env or INFO)")
@click.option("--offload-timeout", default=None, type=int, help="Seconds of inactivity before offloading model (default: 600)")
@click.option("--keep-warm", is_flag=True, help="Keep model loaded in memory")
def zmq(input_address, enable_pub, log_level, offload_timeout, keep_warm):
    """Run ZMQ ROUTER server."""
    _apply_config_overrides(log_level=log_level, offload_timeout=offload_timeout, keep_warm=keep_warm)
    setup_logging(CONFIG.log_level)

    logger = logging.getLogger(__name__)
    logger.info("Starting TTS Inference in ZMQ mode")

    zmq_input = input_address or CONFIG.zmq_input_address
    logger.info(f"Input address: {zmq_input}")

    zmq_pub = ""
    if enable_pub:
        zmq_pub = CONFIG.zmq_pub_address
        if not zmq_pub:
            logger.error("--enable-pub specified but TTS_PUB_ADDRESS not set")
            click.echo("Error: TTS_PUB_ADDRESS must be set when using --enable-pub", err=True)
            sys.exit(1)
        logger.info(f"PUB address: {zmq_pub}")

    _validate_api_key(logger)

    try:
        asyncio.run(run_zmq_server(zmq_input, enable_pub, zmq_pub))
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


def _apply_config_overrides(log_level=None, host=None, port=None, offload_timeout=None, keep_warm=None):
    if log_level:
        CONFIG.log_level = log_level
    if host:
        CONFIG.fastapi_host = host
    if port:
        CONFIG.fastapi_port = port
    if offload_timeout is not None:
        CONFIG.offload_timeout = offload_timeout
    if keep_warm:
        CONFIG.keep_warm = True


def _validate_api_key(logger):
    try:
        CONFIG.validate_api_key()
        logger.info("API key validation successful")
    except ValueError as e:
        logger.error(str(e))
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.group()
def db():
    """Database management commands."""
    pass


@db.command()
@click.option("--log-level", default="INFO", help="Log level (DEBUG, INFO, WARNING, ERROR)")
def migrate(log_level):
    """Run database migrations."""
    setup_logging(log_level)
    logger = logging.getLogger(__name__)

    click.echo(dedent(f"""\
        Running database migrations...
        Database: {CONFIG.database_path}
    """))

    try:
        service = DatabaseService()
        service.run_migrations()
        click.echo("\n✓ Migrations complete!")
    except Exception as e:
        click.echo(f"✗ Migration failed: {e}", err=True)
        logger.error("Migration error", exc_info=True)
        sys.exit(1)


@db.command()
@click.option("--log-level", default="INFO", help="Log level (DEBUG, INFO, WARNING, ERROR)")
def migration_status(log_level):
    """Show database migration status."""
    setup_logging(log_level)

    try:
        service = DatabaseService()
        click.echo(service.get_migration_history_display())
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
def config_info():
    """Display current configuration."""
    click.echo(dedent(f"""\
        TTS Inference Configuration
        ========================================
        Voice Directory: {CONFIG.voice_dir}
        Voice Audio Directory: {CONFIG.voice_audio_dir}
        Database Path: {CONFIG.database_path}
        API Key Configured: {"Yes" if CONFIG.api_key else "No"}

        FastAPI Settings:
          Host: {CONFIG.fastapi_host}
          Port: {CONFIG.fastapi_port}

        ZMQ Settings:
          Input Address: {CONFIG.zmq_input_address}
          PUB Address: {CONFIG.zmq_pub_address if CONFIG.zmq_pub_address else "Not configured"}

        Model Settings:
          Offload Timeout: {CONFIG.offload_timeout}s
          Keep Warm: {"Yes" if CONFIG.keep_warm else "No"}

        Log Level: {CONFIG.log_level}
        ========================================
    """))


@main.command()
@click.option("--text", default="Hello world, this is a test of the text to speech system.", help="Text to synthesize")
@click.option("--voice-id", required=True, help="Voice ID to use for synthesis")
@click.option("--output-dir", default="./test_samples", help="Directory to save test files")
@click.option("--turbo", is_flag=True, help="Use turbo model")
@click.option("--temperature", default=None, type=float, help="Sampling temperature")
@click.option("--top-p", default=None, type=float, help="Top-p sampling parameter")
@click.option("--top-k", default=None, type=int, help="Top-k sampling parameter")
@click.option("--repetition-penalty", default=None, type=float, help="Repetition penalty")
def test_gen(text, voice_id, output_dir, turbo, temperature, top_p, top_k, repetition_penalty):
    """Generate test audio files in all formats for debugging."""
    setup_logging("INFO")
    logger = logging.getLogger(__name__)

    click.echo(dedent(f"""\
        Generating test samples...
        Text: {text}
        Output directory: {output_dir}
        Turbo mode: {turbo}
    """))

    try:
        results = asyncio.run(TTSService.generate_test_samples(
            text=text,
            voice_id=voice_id,
            output_dir=output_dir,
            use_turbo=turbo,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            repetition_penalty=repetition_penalty,
        ))

        click.echo(dedent(f"""\
            ✓ Generated {results.samples} samples at {results.sample_rate}Hz
              Duration: {results.duration:.2f} seconds
        """))

        for _, info in results.files.items():
            click.echo(f"✓ Saved {info.path} ({info.size:,} bytes)")

        click.echo(dedent(f"""\

            Done! Check the files with:
              file {output_dir}/*
              ffplay {output_dir}/test.wav
        """))

    except Exception as e:
        click.echo(f"✗ Generation failed: {e}", err=True)
        logger.error("Test generation error", exc_info=True)
        sys.exit(1)
