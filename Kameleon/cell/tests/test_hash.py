from pathlib import Path

from system.kameleon import hash_model_file


def test_hash_consistency():
    dummy = Path("requirements-dev.txt")
    h1 = hash_model_file(dummy)
    h2 = hash_model_file(dummy)
    assert h1 == h2, "Hash funkcija ni deterministična"
