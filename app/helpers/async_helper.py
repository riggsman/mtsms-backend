"""
Helper functions for running async code from synchronous contexts
"""
import asyncio
import threading
from typing import Callable, Coroutine
import logging

logger = logging.getLogger(__name__)


def run_async_in_thread(coro: Coroutine):
    """
    Run an async coroutine in a new thread with its own event loop.
    This allows running async code from synchronous contexts.
    """
    def run_in_thread():
        try:
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(coro)
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Error running async task in thread: {e}")
    
    # Start the thread (daemon thread so it doesn't block shutdown)
    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()


def run_async_safe(coro: Coroutine):
    """
    Safely run an async coroutine, handling both sync and async contexts.
    If there's a running event loop, schedule the task.
    Otherwise, run in a new thread.
    """
    try:
        # Try to get the current event loop
        loop = asyncio.get_running_loop()
        # If we get here, there's a running loop, so we can create a task
        asyncio.create_task(coro)
    except RuntimeError:
        # No running loop, run in a new thread
        run_async_in_thread(coro)
