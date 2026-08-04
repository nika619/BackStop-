"""
BackStop — Background queue entry point (legacy shim).
The actual processing logic lives in backstop.ingest.queue_worker.
This module is kept for any legacy imports.
"""
from backstop.ingest.queue_worker import process_job_by_event_id


def process_payment_event_async(event_id: str):
    """
    Legacy shim — calls the new persistent queue worker.
    Kept for backward compatibility with any existing imports.
    """
    process_job_by_event_id(event_id)
