from src.core.nodes import compute_fingerprint


def test_compute_fingerprint_is_stable() -> None:
    a = compute_fingerprint("DHL EXPRESS INVOICE 123")
    b = compute_fingerprint("  DHL   EXPRESS  INVOICE   123  ")
    assert a == b

