from backstop.execute.razorpay_client import RazorpayEnterpriseClient


def test_razorpay_client_cancel_order_and_idempotency_headers():
    client = RazorpayEnterpriseClient(key_id="rzp_test_mock", key_secret="secret_mock")

    # Test headers inclusion
    headers = client._get_headers(idempotency_key="idempotency_hash_12345")
    assert headers["X-Razorpay-Idempotency-Header"] == "idempotency_hash_12345"

    # Test order cancellation for simulated/test mode
    cancel_res = client.cancel_order("order_SYN000001", idempotency_key="idempotency_hash_12345")
    assert cancel_res["status"] == "cancelled"
    assert cancel_res["id"] == "order_SYN000001"

    # Test payment link creation with expire_by timestamp
    plink_res = client.create_payment_link(
        amount_paise=99900,
        currency="INR",
        customer_ref="cust_12345",
        expire_in_minutes=30,
        idempotency_key="idempotency_hash_12345",
    )
    assert plink_res["status"] == "created"
    assert plink_res["amount"] == 99900
    assert "expire_by" in plink_res
