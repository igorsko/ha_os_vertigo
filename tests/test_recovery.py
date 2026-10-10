"""Recovery utility tests use synthetic memory only."""

import json
import os

import pytest

from tools.recover_key import collect_candidates, save_credentials


def test_find_ascii_key_near_requested_id():
    memory = b'padding{"key":"test-device","localKey":"0123456789abcdef"}end'
    assert collect_candidates(memory, "test-device") == ["0123456789abcdef"]
    assert collect_candidates(memory, "another-device") == []


def test_find_utf16_key():
    memory = '{"key":"test-device","localKey":"0123456789abcdef"}'.encode("utf-16-le")
    assert collect_candidates(memory, "test-device") == ["0123456789abcdef"]


def test_find_utf16_key_at_odd_offset():
    memory = b"x" + '{"key":"test-device","localKey":"0123456789abcdef"}'.encode("utf-16-le")
    assert collect_candidates(memory, "test-device") == ["0123456789abcdef"]


def test_does_not_search_distant_key():
    memory = b"test-device" + b"x" * 1024 + b'"localKey":"0123456789abcdef"'
    assert collect_candidates(memory, "test-device") == []


def test_private_file_never_overwritten(tmp_path):
    output = tmp_path / "test-credentials.json"
    save_credentials(output, "test-device", "192.0.2.10", "0123456789abcdef")
    assert json.loads(output.read_text())["local_key"] == "0123456789abcdef"
    if os.name == "posix":
        assert output.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        save_credentials(output, "another", "192.0.2.11", "fedcba9876543210")
