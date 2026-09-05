from backstop.execute.lock import acquire_idempotency_lock, release_idempotency_lock


def test_redis_distributed_idempotency_lock():
    mid = "merch_ecommerce_01"
    pid = "pay_test_idempotency_lock_99"
    attempt = 1

    # Clean up lock key first
    release_idempotency_lock(mid, pid, attempt)

    # First acquisition must succeed
    lock1 = acquire_idempotency_lock(mid, pid, attempt, ttl_seconds=60)
    assert lock1 is True

    # Duplicate acquisition for same merchant, payment, and attempt must fail
    lock2 = acquire_idempotency_lock(mid, pid, attempt, ttl_seconds=60)
    assert lock2 is False

    # Acquisition for different attempt must succeed
    lock3 = acquire_idempotency_lock(mid, pid, 2, ttl_seconds=60)
    assert lock3 is True
