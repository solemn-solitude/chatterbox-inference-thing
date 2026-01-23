"""Click CLI for TTS Inference."""

import click
import asyncio
import logging
import sys
import uvicorn
from textwrap import dedent

from .utils.logging import setup_logging

from .server import run_zmq_server
from .utils.config import CONFIG
from .emotion_map.migrations_definition import get_migrator
from .emotion_map import PROMPT_TEMPLATES_SEED
from .services import EmotionalAnchorService
from .emotion_map.anchor_generator import AnchorGenerator
from .tts.engine import create_tts_engine
from .tts.voice_manager import VoiceManager
from .services import TTSService


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
@click.option(
    "--host", default=None, help="Host to bind to (default: from env or 0.0.0.0)"
)
@click.option(
    "--port",
    default=None,
    type=int,
    help="Port to bind to (default: from env or 20480)",
)
@click.option("--log-level", default=None, help="Log level (default: from env or INFO)")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
@click.option(
    "--offload-timeout",
    default=None,
    type=int,
    help="Seconds of inactivity before offloading model (default: 600)",
)
@click.option(
    "--keep-warm",
    is_flag=True,
    help="Keep model loaded in memory (disable auto-offloading)",
)
@click.option(
    "--model",
    default=None,
    type=click.Choice(["chatterbox", "qwen"]),
    help="TTS model to use (default: from env or chatterbox)",
)
def fastapi(host, port, log_level, reload, offload_timeout, keep_warm, model):
    """Run FastAPI HTTP/WebSocket server."""
    # Apply CONFIG overrides
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

    setup_logging(CONFIG.log_level)

    logger = logging.getLogger(__name__)
    logger.info("Starting TTS Inference in FastAPI mode")
    logger.info(f"Host: {CONFIG.fastapi_host}, Port: {CONFIG.fastapi_port}")

    # Check API key
    try:
        CONFIG.validate_api_key()
        logger.info("API key validation successful")
    except ValueError as e:
        logger.error(str(e))
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    # Run uvicorn server
    uvicorn.run(
        "tts_inference.server.fastapi_server:app",
        host=CONFIG.fastapi_host,
        port=CONFIG.fastapi_port,
        reload=reload,
        log_level=CONFIG.log_level.lower(),
    )


@run.command()
@click.option("--input-address", default=None, help="Input ROUTER address (default: from TTS_INPUT_ADDRESS env or tcp://localhost:20501)")
@click.option(
    "--enable-pub",
    is_flag=True,
    help="Enable PUB socket for broadcasting (reads address from TTS_PUB_ADDRESS env)",
)
@click.option("--log-level", default=None, help="Log level (default: from env or INFO)")
@click.option(
    "--offload-timeout",
    default=None,
    type=int,
    help="Seconds of inactivity before offloading model (default: 600)",
)
@click.option(
    "--keep-warm",
    is_flag=True,
    help="Keep model loaded in memory (disable auto-offloading)",
)
def zmq(input_address, enable_pub, log_level, offload_timeout, keep_warm):
    """Run ZMQ ROUTER server."""
    # Apply CONFIG overrides
    if log_level:
        CONFIG.log_level = log_level
    if offload_timeout is not None:
        CONFIG.offload_timeout = offload_timeout
    if keep_warm:
        CONFIG.keep_warm = True

    # Setup logging
    setup_logging(CONFIG.log_level)

    logger = logging.getLogger(__name__)
    logger.info("Starting TTS Inference in ZMQ mode")
    
    # Use provided input_address or default from config
    zmq_input = input_address if input_address else CONFIG.zmq_input_address
    logger.info(f"Input address: {zmq_input}")
    
    # Check if PUB socket is enabled
    zmq_pub = ""
    if enable_pub:
        zmq_pub = CONFIG.zmq_pub_address
        if not zmq_pub:
            logger.error("--enable-pub specified but TTS_PUB_ADDRESS environment variable not set")
            click.echo("Error: TTS_PUB_ADDRESS environment variable must be set when using --enable-pub", err=True)
            sys.exit(1)
        logger.info(f"PUB address: {zmq_pub}")

    # Check API key
    try:
        CONFIG.validate_api_key()
        logger.info("API key validation successful")
    except ValueError as e:
        logger.error(str(e))
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    # Run ZMQ server
    try:
        asyncio.run(run_zmq_server(zmq_input, enable_pub, zmq_pub))
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


@main.group()
def db():
    """Database management commands."""
    pass


@db.command()
@click.option(
    "--log-level", default="INFO", help="Log level (DEBUG, INFO, WARNING, ERROR)"
)
def migrate(log_level):
    """Run database migrations."""
    setup_logging(log_level)
    logger = logging.getLogger(__name__)

    async def run_migrations():
        click.echo(
            dedent(f"""
            Running database migrations...
            Database: {CONFIG.database_path}
            """)
        )

        migrator = get_migrator(CONFIG.database_path)
        await migrator.run_migrations()

        click.echo("\n✓ Migrations complete!")

    try:
        asyncio.run(run_migrations())
    except Exception as e:
        click.echo(f"✗ Migration failed: {e}", err=True)
        logger.error("Migration error", exc_info=True)
        sys.exit(1)


@db.command()
@click.option(
    "--log-level", default="INFO", help="Log level (DEBUG, INFO, WARNING, ERROR)"
)
def migration_status(log_level):
    """Show database migration status."""
    setup_logging(log_level)

    async def show_status():
        migrator = get_migrator(CONFIG.database_path)

        click.echo("Database Migration Status")
        click.echo("=" * 60)
        click.echo(f"Database: {CONFIG.database_path}")

        current_version = await migrator.get_current_version()
        click.echo(f"Current Version: {current_version}")
        click.echo()

        history = await migrator.get_migration_history()

        if history:
            click.echo("Applied Migrations:")
            click.echo("-" * 60)
            for record in history:
                click.echo(dedent(
                    f"""
                        [{record['version']}] {record['name']}")
                        Applied: {record['applied_at']}"""))
        else:
            click.echo("No migrations applied yet")

        click.echo("=" * 60)

    try:
        asyncio.run(show_status())
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@db.command()
@click.option(
    "--log-level", default="INFO", help="Log level (DEBUG, INFO, WARNING, ERROR)"
)
def seed_templates(log_level):
    """Seed prompt templates from SQL file."""
    setup_logging(log_level)
    logger = logging.getLogger(__name__)

    async def run_seed():
        click.echo(
            dedent(f"""
            Seeding prompt templates...
            Database: {CONFIG.database_path}
            Seed file: {PROMPT_TEMPLATES_SEED}
            """)
        )

        service = EmotionalAnchorService(db_path=CONFIG.database_path)

        try:
            count = await service.seed_prompt_templates()
            click.echo(f"✓ Seeded {count} prompt templates")
        except FileNotFoundError as e:
            click.echo(f"✗ {e}", err=True)
            sys.exit(1)

    try:
        asyncio.run(run_seed())
    except Exception as e:
        click.echo(f"✗ Seeding failed: {e}", err=True)
        logger.error("Seeding error", exc_info=True)
        sys.exit(1)


@main.group()
def anchors():
    """Emotional anchor generation commands."""
    pass


@anchors.command()
@click.argument("base_voice_id")
@click.option(
    "--templates",
    default=None,
    help="Comma-separated list of template IDs (default: all templates)",
)
@click.option(
    "--skip-existing/--overwrite",
    default=True,
    help="Skip existing anchors or overwrite them (default: skip)",
)
@click.option(
    "--log-level", default="INFO", help="Log level (DEBUG, INFO, WARNING, ERROR)"
)
@click.option(
    "--keep-warm",
    is_flag=True,
    help="Keep model loaded in memory (faster but uses more GPU memory)",
)
def generate(base_voice_id, templates, skip_existing, log_level, keep_warm):
    """Generate emotional voice anchors from prompt templates.

    BASE_VOICE_ID: The voice ID to use as the base for emotional variations

    Example:
        tts-inference anchors generate my_voice
        tts-inference anchors generate my_voice --templates excited_01,sad_01
    """
    setup_logging(log_level)
    logger = logging.getLogger(__name__)

    async def run_generation():
        # Initialize components
        click.echo(
            dedent(f"""
            Initializing anchor generation for voice: {base_voice_id}
            Database: {CONFIG.database_path}
            """)
        )

        # Initialize service for voice lookup
        service = EmotionalAnchorService(db_path=CONFIG.database_path)

        # Check if base voice exists
        voice = await service.get_voice(base_voice_id)
        if not voice:
            click.echo(f"✗ Voice not found: {base_voice_id}", err=True)
            click.echo("\nAvailable voices:")
            voices = await service.list_voices()
            for v in voices:
                click.echo(f"  - {v['voice_id']}")
            sys.exit(1)

        click.echo(
            dedent(f"""
            ✓ Base voice found: {base_voice_id}
              File: {voice["filename"]}
              Duration: {voice["duration_seconds"]:.2f}s
            """)
        )

        # Get database for TTS components
        db = service.db

        # Initialize TTS engine
        click.echo("Loading TTS model...")
        tts_engine = create_tts_engine(
            inactivity_timeout=999999,  # Disable auto-offload during generation
            keep_warm=keep_warm,
        )
        await tts_engine.initialize()
        click.echo(f"✓ TTS model loaded on {tts_engine.device}")
        click.echo()

        # Initialize voice manager and generator
        voice_manager = VoiceManager(db)
        generator = AnchorGenerator(db, tts_engine, voice_manager)

        # Parse template IDs if provided
        template_ids = None
        if templates:
            template_ids = [t.strip() for t in templates.split(",")]
            click.echo(f"Generating {len(template_ids)} specific templates")
        else:
            all_templates = await db.list_prompt_templates()
            click.echo(f"Generating all {len(all_templates)} templates")

        click.echo(
            dedent(f"""Skip existing: {skip_existing}")
        ===============================
                   
        """)
        )

        # Progress callback
        def progress_callback(current, total, template_id, status):
            pass  # Logging handles this

        # Generate anchors
        try:
            stats = await generator.generate_batch(
                base_voice_id=base_voice_id,
                template_ids=template_ids,
                skip_if_exists=skip_existing,
                progress_callback=progress_callback,
            )

            click.echo(
                dedent(f"""
                
                ======================================================================
                Generation Summary
                ======================================================================
                Total templates: {stats["total"]}
                Successfully generated: {stats["generated"]}
                Failed: {stats["failed"]}
                Duration: {stats["duration_seconds"]:.1f}s
                Average: {stats["duration_seconds"] / stats["total"]:.1f}s per anchor
                ======================================================================
                """)
            )

            if stats["failed"] > 0:
                sys.exit(1)

        except KeyboardInterrupt:
            click.echo("\n\nGeneration interrupted by user")
            sys.exit(1)
        except Exception as e:
            click.echo(f"\n✗ Generation failed: {e}", err=True)
            logger.error("Generation error", exc_info=True)
            sys.exit(1)

    try:
        asyncio.run(run_generation())
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@anchors.command()
@click.argument("base_voice_id")
@click.option(
    "--log-level", default="INFO", help="Log level (DEBUG, INFO, WARNING, ERROR)"
)
def list_anchors(base_voice_id, log_level):
    """List all generated anchors for a base voice.

    BASE_VOICE_ID: The base voice ID to list anchors for
    """
    setup_logging(log_level)

    try:
        asyncio.run(run_list_anchors(base_voice_id))
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@anchors.command()
@click.argument("base_voice_id")
@click.option(
    "--anchor-id", default=None, help="Analyze a specific anchor (default: all anchors)"
)
@click.option(
    "--update-db", is_flag=True, help="Update database with extracted features"
)
@click.option(
    "--log-level", default="INFO", help="Log level (DEBUG, INFO, WARNING, ERROR)"
)
def analyze(base_voice_id, anchor_id, update_db, log_level):
    """Extract acoustic features from emotional anchors.

    BASE_VOICE_ID: The base voice ID to analyze anchors for

    Example:
        tts-inference anchors analyze my_voice
        tts-inference anchors analyze my_voice --anchor-id my_voice_excited_01
        tts-inference anchors analyze my_voice --update-db
    """
    setup_logging(log_level)
    logger = logging.getLogger(__name__)

    async def run_analysis():
        service = EmotionalAnchorService(db_path=CONFIG.database_path)

        # Determine which anchors to analyze
        anchor_ids = [anchor_id] if anchor_id else None

        click.echo(f"Analyzing anchors for voice: {base_voice_id}")
        if anchor_id:
            click.echo(f"  Specific anchor: {anchor_id}")
        click.echo()

        try:
            results = await service.analyze_anchors_batch(
                base_voice_id=base_voice_id, anchor_ids=anchor_ids, update_db=update_db
            )

            # Display results
            if results["total"] == 0:
                click.echo(f"No anchors found for voice: {base_voice_id}")
                return

            click.echo(f"Analysis Summary:")
            click.echo("=" * 70)
            click.echo(f"Total: {results['total']}")
            click.echo(f"Analyzed: {results['analyzed']}")
            click.echo(f"Failed: {results['failed']}")
            click.echo("=" * 70)

            if results["failures"]:
                click.echo("\nFailures:")
                for failure in results["failures"]:
                    click.echo(f"  ✗ {failure['anchor_id']}: {failure['error']}")

            if results["failed"] > 0:
                sys.exit(1)

        except Exception as e:
            click.echo(f"✗ Analysis failed: {e}", err=True)
            logger.error("Analysis error", exc_info=True)
            sys.exit(1)

    try:
        asyncio.run(run_analysis())
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        logger.error("Analysis error", exc_info=True)
        sys.exit(1)


@main.command()
def config_info():
    """Display current configuration."""
    click.echo(
        dedent(f"""
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
        """)
    )


@main.command()
@click.option(
    "--text",
    default="Hello world, this is a test of the text to speech system.",
    help="Text to synthesize",
)
@click.option(
    "--voice-id",
    required=True,
    help="Voice ID to use for synthesis (required)",
)
@click.option(
    "--output-dir", default="./test_samples", help="Directory to save test files"
)
@click.option("--turbo", is_flag=True, help="Use turbo model (Chatterbox only)")
@click.option(
    "--temperature",
    default=None,
    type=float,
    help="Sampling temperature for variability (default: 0.9 for Qwen, 0.8 for Chatterbox)",
)
@click.option(
    "--top-p",
    default=None,
    type=float,
    help="Top-p sampling parameter (Qwen: default 1.0)",
)
@click.option(
    "--top-k",
    default=None,
    type=int,
    help="Top-k sampling parameter (Qwen: default 50)",
)
@click.option(
   "--repetition-penalty",
    default=None,
    type=float,
    help="Repetition penalty (default: 1.05 for Qwen, 1.2 for Chatterbox)",
)
def test_gen(text, voice_id, output_dir, turbo, temperature, top_p, top_k, repetition_penalty):
    """Generate test audio files in all formats for debugging.
    
    Requires a voice ID from the database for voice cloning.
    
    For more expressive output, try higher temperature (e.g., 1.2-1.5).
    """
    setup_logging("INFO")
    logger = logging.getLogger(__name__)

    click.echo(
        dedent(f"""
        Generating test samples...
        Text: {text}
        Output directory: {output_dir}
        Turbo mode: {turbo}
        """)
    )

    async def generate():

        try:
            results = await TTSService.generate_test_samples(
                text=text,
                voice_id=voice_id,
                output_dir=output_dir,
                use_turbo=turbo,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                repetition_penalty=repetition_penalty
            )

            click.echo(
                dedent(f"""
                ✓ Generated {results["samples"]} samples at {results["sample_rate"]}Hz
                  Duration: {results["duration"]:.2f} seconds
                """)
            )

            for _, info in results["files"].items():
                click.echo(f"✓ Saved {info['path']} ({info['size']:,} bytes)")

            click.echo(
                dedent(f"""
                
                Done! Check the files with:
                  file {output_dir}/*
                  ffplay {output_dir}/test.wav
                """)
            )

        except Exception as e:
            click.echo(f"✗ Generation failed: {e}", err=True)
            logger.error("Test generation error", exc_info=True)
            sys.exit(1)

    try:
        asyncio.run(generate())
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        logger.error("Test generation failed", exc_info=True)
        sys.exit(1)


async def run_list_anchors(base_voice_id):
    service = EmotionalAnchorService(db_path=CONFIG.database_path)
    anchors = await service.list_anchors(base_voice_id=base_voice_id)

    if not anchors:
        click.echo(f"No anchors found for voice: {base_voice_id}")
        return

    click.echo(
        dedent(f"""
        Emotional Anchors for: {base_voice_id}
        ================================================================================
        {"Emotion":<20} {"Valence":>8} {"Arousal":>8} {"Tension":>8} {"Stability":>8} {"Duration":>8}
        --------------------------------------------------------------------------------
        """).rstrip()
    )

    for anchor in anchors:
        template_id = anchor["template_id"]
        valence = anchor["valence"]
        arousal = anchor["arousal"]
        tension = anchor["tension"]
        stability = anchor["stability"]
        duration = anchor.get("duration_seconds", 0)

        # Get emotion label from template ID
        emotion = template_id.replace("_01", "").replace("_02", "").replace("_", " ")

        click.echo(
            f"{emotion:<20} {valence:>8.2f} {arousal:>8.2f} {tension:>8.2f} {stability:>8.2f} {duration:>7.1f}s"
        )

    click.echo(
        dedent(f"""
        ================================================================================
        Total: {len(anchors)} anchors
        """)
    )
