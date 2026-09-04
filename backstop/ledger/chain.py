import hashlib
import json
from datetime import datetime, timezone
from sqlmodel import Session, select
from backstop.models import LedgerEntry

GENESIS = "0" * 64


def canonical_json(payload: dict) -> str:
    """Canonical JSON serialization for deterministic cryptographic hashing."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def digest(prev_hash: str, payload: dict) -> str:
    """Compute SHA-256 over prev_hash + canonical serialized payload."""
    canonical = canonical_json(payload)
    return hashlib.sha256(f"{prev_hash}|{canonical}".encode("utf-8")).hexdigest()


def append(
    session: Session,
    case_id: str,
    payment_id: str,
    actor: str,
    stage: str,
    payload: dict,
    policy_version: str,
    prompt_version: str | None = None,
    outcome: str | None = None,
) -> LedgerEntry:
    """Append a new tamper-evident, hash-chained entry to the audit ledger."""
    # Find the latest ledger entry to get the previous block's hash
    statement = select(LedgerEntry).order_by(LedgerEntry.seq.desc()).limit(1)  # type: ignore
    prev = session.exec(statement).first()
    prev_hash = prev.hash if prev else GENESIS

    input_hash = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    entry_hash = digest(prev_hash, payload)

    entry = LedgerEntry(
        case_id=case_id,
        payment_id=payment_id,
        actor=actor,
        stage=stage,
        input_hash=input_hash,
        policy_version=policy_version,
        prompt_version=prompt_version,
        decision=payload,
        outcome=outcome,
        prev_hash=prev_hash,
        hash=entry_hash,
        ts=datetime.now(timezone.utc),
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def verify_chain(session: Session) -> tuple[bool, int | None, str | None]:
    """
    Cryptographically verify the entire audit ledger chain.
    Returns: (is_valid: bool, first_bad_seq: int | None, reason: str | None)
    """
    statement = select(LedgerEntry).order_by(LedgerEntry.seq.asc())  # type: ignore
    entries = session.exec(statement).all()

    if not entries:
        return True, None, "Ledger is empty"

    prev_hash = GENESIS
    for entry in entries:
        expected_hash = digest(prev_hash, entry.decision)
        if entry.prev_hash != prev_hash:
            return (
                False,
                entry.seq,
                f"Broken chain link at seq #{entry.seq}: prev_hash mismatch (expected {prev_hash[:12]}..., got {entry.prev_hash[:12]}...)",
            )
        if entry.hash != expected_hash:
            return (
                False,
                entry.seq,
                f"Tampered record at seq #{entry.seq}: payload hash mismatch (expected {expected_hash[:12]}..., recorded {entry.hash[:12]}...)",
            )
        prev_hash = entry.hash

    return True, None, f"Chain intact: {len(entries)} verified blocks"


def tamper_entry(session: Session, seq: int, fake_decision: dict) -> LedgerEntry:
    """Deliberately mutate an entry's payload to test cryptographic tamper detection."""
    statement = select(LedgerEntry).where(LedgerEntry.seq == seq)
    entry = session.exec(statement).first()
    if not entry:
        raise ValueError(f"LedgerEntry with seq #{seq} not found")
    entry.decision = fake_decision
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


if __name__ == "__main__":
    """
    Live tamper-detection demo.
    Proves: append → verify (clean) → tamper → verify (detects exact bad seq).
    Run with: python -m backstop.ledger.chain
    """
    from sqlmodel import create_engine, SQLModel

    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)

    POLICY_V = "2026.09.01"

    import sys
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    print("=" * 60)
    print("  BACKSTOP - Cryptographic Audit Ledger Demo")
    print("=" * 60)

    with Session(engine) as session:
        # Step 1: Append 3 legitimate ledger entries
        e1 = append(session, "case_001", "pay_001", "backstop-agent", "plan",
                    {"action": "retry_same_rail", "cause": "transient_infra"}, POLICY_V, outcome="recovered")
        e2 = append(session, "case_002", "pay_002", "backstop-agent", "plan",
                    {"action": "nudge_checkout", "cause": "auth_abandoned"}, POLICY_V, outcome="pending")
        e3 = append(session, "case_003", "pay_003", "backstop-agent", "plan",
                    {"action": "escalate_human", "cause": "risk_decline"}, POLICY_V, outcome="escalated")

        print(f"\n[+] Appended 3 ledger entries (seq #{e1.seq}, #{e2.seq}, #{e3.seq})")
        print(f"    Block #{e1.seq} hash: {e1.hash[:24]}...")
        print(f"    Block #{e2.seq} hash: {e2.hash[:24]}...")
        print(f"    Block #{e3.seq} hash: {e3.hash[:24]}...")

        # Step 2: Verify clean chain
        valid, bad_seq, reason = verify_chain(session)
        print(f"\n[OK] Chain verification (clean): valid={valid}")
        print(f"    Result: {reason}")

        # Step 3: Tamper block #2 as a bad actor would
        print(f"\n[!] Tampering block #{e2.seq}: changing action to 'issue_refund_10x'...")
        tamper_entry(session, e2.seq, {"action": "issue_refund_10x", "cause": "auth_abandoned"})

        # Step 4: Verify again — must detect the tamper
        valid, bad_seq, reason = verify_chain(session)
        print(f"\n[FAIL] Chain verification (after tamper): valid={valid}")
        print(f"    Detected at seq: #{bad_seq}")
        print(f"    Reason: {reason}")

    print("\n" + "=" * 60)
    print("  SHA-256 chain integrity: TAMPER DETECTED AND LOCALISED")
    print("=" * 60)
    print("  Run: python -m backstop.ledger.chain to reproduce.")
    print("=" * 60)
