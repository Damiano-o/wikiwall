from pathlib import Path

import pytest

from wikiwall.single_instance import InstanceLock


def test_only_one_instance_holds_the_lock(tmp_path: Path):
    first = InstanceLock(tmp_path / "wikiwall.lock")
    second = InstanceLock(tmp_path / "wikiwall.lock")

    assert first.acquire() is True
    assert first.held is True
    assert second.acquire() is False
    assert second.held is False

    first.release()
    assert first.held is False
    assert second.acquire() is True
    second.release()


def test_lock_is_released_and_reacquirable(tmp_path: Path):
    lock = InstanceLock(tmp_path / "wikiwall.lock")
    assert lock.acquire()
    lock.release()
    assert lock.acquire()
    lock.release()


def test_acquire_is_idempotent(tmp_path: Path):
    lock = InstanceLock(tmp_path / "wikiwall.lock")
    assert lock.acquire()
    assert lock.acquire()
    lock.release()


def test_context_manager_refuses_a_second_instance(tmp_path: Path):
    path = tmp_path / "wikiwall.lock"
    holder = InstanceLock(path)
    assert holder.acquire()
    with pytest.raises(RuntimeError):
        with InstanceLock(path):
            pass
    holder.release()


def test_lock_file_records_the_owner(tmp_path: Path):
    path = tmp_path / "wikiwall.lock"
    with InstanceLock(path):
        pass
    assert path.read_text(encoding="utf-8").strip().isdigit()
