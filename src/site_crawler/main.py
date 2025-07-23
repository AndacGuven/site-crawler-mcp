"""Main entry point for the Site Crawler MCP server."""

import asyncio
import logging
import os
import signal

from .server import SiteCrawlerServer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def async_main():
    """Async main function to handle graceful shutdown."""
    shutdown_event = asyncio.Event()
    shutdown_initiated = False

    def signal_handler(signum, frame):
        nonlocal shutdown_initiated
        if not shutdown_initiated:
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            shutdown_initiated = True
            shutdown_event.set()
        else:
            # Force shutdown by terminating the process
            logger.info("Force shutdown requested, terminating process...")
            os._exit(0)

    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Starting Site Crawler MCP Server v0.1.0")
    logger.info("Available tools: site_crawlAssets")
    logger.info(
        "Supported modes: images, meta, brand, seo, performance, security, compliance, infrastructure, legal, careers, references, contact"
    )
    logger.info("Server ready - waiting for MCP client connection...")

    server = SiteCrawlerServer()
    server_task = asyncio.create_task(server.run())
    shutdown_task = asyncio.create_task(shutdown_event.wait())

    try:
        # Wait for server completion or shutdown signal
        done, pending = await asyncio.wait(
            [server_task, shutdown_task], return_when=asyncio.FIRST_COMPLETED
        )

        if shutdown_task in done:
            logger.info("Shutdown signal received, stopping server...")
            server_task.cancel()

            # Wait for server task to finish with timeout
            try:
                await asyncio.wait_for(server_task, timeout=2.0)
            except asyncio.TimeoutError:
                logger.warning("Server shutdown timed out")
                # Don't call sys.exit here, just return
                return
            except asyncio.CancelledError:
                logger.info("Server task cancelled successfully")

        # Cancel any remaining tasks
        for task in pending:
            task.cancel()
            try:
                await asyncio.wait_for(task, timeout=1.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

        # Check for exceptions in completed tasks
        for task in done:
            if task != shutdown_task and task.exception():
                raise task.exception()

    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        logger.info("Server shutdown complete")


def main():
    """Main entry point for the MCP server."""
    try:
        asyncio.run(async_main())
        logger.info("Server exited cleanly")
    except KeyboardInterrupt:
        logger.info("Server shutdown requested by user")
    except Exception as e:
        logger.error(f"Server startup failed: {e}")
        return 1
    return 0


if __name__ == "__main__":
    main()
