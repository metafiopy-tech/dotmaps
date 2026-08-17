"""H4 (HARDENING_BRIEF): concurrency-safe evidence journals. The audit's P1
finding — trips.emit()/chat.emit_chat() did read-tail -> compute -> append
with no lock, so concurrent writers could fork the hash chain or duplicate
sequence numbers. Real OS processes (not threads — the GIL would mask the
race) append 1,000 events to the same journal; the chain must stay linear,
unique, and complete."""
import multiprocessing
from pathlib import Path

from dotmaps.queen import chat as chat_mod
from dotmaps.queen import trips as trips_mod

N_PER_PROCESS = 500
N_PROCESSES = 2


def _append_trips(path_str: str, n: int, worker: int) -> None:
    path = Path(path_str)
    for i in range(n):
        trips_mod.emit("SLEEP", path=path, worker=worker, i=i)


def _append_chat(path_str: str, n: int, worker: int) -> None:
    path = Path(path_str)
    for i in range(n):
        chat_mod.emit_chat("user", f"worker {worker} message {i}", path=path)


def test_two_processes_append_1000_trips_chain_stays_linear_unique_complete(tmp_path):
    path = tmp_path / "trips.jsonl"
    procs = [multiprocessing.Process(target=_append_trips, args=(str(path), N_PER_PROCESS, w))
            for w in range(N_PROCESSES)]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=120)
        assert p.exitcode == 0

    records = trips_mod.read_all(path)
    assert len(records) == N_PER_PROCESS * N_PROCESSES

    seqs = [r["seq"] for r in records]
    assert sorted(seqs) == list(range(1, N_PER_PROCESS * N_PROCESSES + 1)), \
        "seq values must be a contiguous, unique 1..N run — a race would " \
        "produce duplicates or gaps"

    ok, reason = trips_mod.verify_integrity(path)
    assert ok, f"chain broke: {reason}"


def test_two_processes_append_1000_chat_messages_chain_stays_linear_unique_complete(tmp_path):
    path = tmp_path / "chat.jsonl"
    procs = [multiprocessing.Process(target=_append_chat, args=(str(path), N_PER_PROCESS, w))
            for w in range(N_PROCESSES)]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=120)
        assert p.exitcode == 0

    records = chat_mod.read_chat(path)
    assert len(records) == N_PER_PROCESS * N_PROCESSES

    seqs = [r["seq"] for r in records]
    assert sorted(seqs) == list(range(1, N_PER_PROCESS * N_PROCESSES + 1))

    ok, reason = chat_mod.verify_chat_integrity(path)
    assert ok, f"chain broke: {reason}"
