import pytest
from sqlmodel import Session, create_engine, SQLModel
from backstop.models import LedgerEntry
from backstop.ledger.chain import append, verify_chain, tamper_entry, GENESIS


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_empty_ledger_verifies_successfully(session):
    is_valid, bad_seq, details = verify_chain(session)
    assert is_valid is True
    assert bad_seq is None


def test_hash_chain_appends_and_verifies_integrity(session):
    e1 = append(
        session=session,
        case_id="case_1",
        payment_id="pay_1",
        actor="classifier",
        stage="diagnose",
        payload={"root_cause": "transient_infra"},
        policy_version="2026.09.01",
    )
    assert e1.seq == 1
    assert e1.prev_hash == GENESIS

    e2 = append(
        session=session,
        case_id="case_1",
        payment_id="pay_1",
        actor="policy_engine",
        stage="pregate",
        payload={"permitted": ["retry_same_rail"]},
        policy_version="2026.09.01",
    )
    assert e2.seq == 2
    assert e2.prev_hash == e1.hash

    is_valid, bad_seq, details = verify_chain(session)
    assert is_valid is True
    assert bad_seq is None


def test_tampering_entry_is_detected_with_exact_sequence_number(session):
    # Append 5 valid blocks
    for i in range(1, 6):
        append(
            session=session,
            case_id=f"case_{i}",
            payment_id=f"pay_{i}",
            actor="executor",
            stage="execute",
            payload={"recovered_paise": 100000 * i},
            policy_version="2026.09.01",
        )

    # Validate pristine chain
    is_valid, bad_seq, _ = verify_chain(session)
    assert is_valid is True

    # Maliciously mutate block #3 in database
    tamper_entry(session, seq=3, fake_decision={"recovered_paise": 99999999})

    # Chain verification MUST fail and name sequence #3
    is_valid, bad_seq, details = verify_chain(session)
    assert is_valid is False
    assert bad_seq == 3
    assert "Tampered record at seq #3" in details
