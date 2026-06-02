"""Tests du chiffrement Fernet des tokens OAuth (cf ADR-014 §5)."""

import pytest

from app.auth.oauth_crypto import decrypt_token, encrypt_token


def test_encrypt_decrypt_roundtrip():
    plaintext = "ya29.a0AfH6SMC_FAKE_GOOGLE_ACCESS_TOKEN_xxxxxxxxx"
    ciphertext = encrypt_token(plaintext)
    assert ciphertext is not None
    assert isinstance(ciphertext, bytes)
    assert ciphertext != plaintext.encode()  # vraiment chiffré
    assert decrypt_token(ciphertext) == plaintext


def test_encrypt_none_passthrough():
    assert encrypt_token(None) is None


def test_decrypt_none_passthrough():
    assert decrypt_token(None) is None


def test_decrypt_tampered_raises():
    ciphertext = encrypt_token("valid_token")
    assert ciphertext is not None
    tampered = ciphertext[:-1] + b"X"
    with pytest.raises(RuntimeError, match="corrompu"):
        decrypt_token(tampered)


def test_two_encryptions_differ():
    """Fernet inclut un nonce → deux encryptions du même plaintext diffèrent."""
    a = encrypt_token("same")
    b = encrypt_token("same")
    assert a != b
    assert decrypt_token(a) == decrypt_token(b) == "same"
