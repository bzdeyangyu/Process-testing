import asyncio
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_runtime.storage import FileBlobStore, FileSessionStore
from agent_runtime.types import Checkpoint, Message, RuntimeState


def test_file_blob_store_persists_and_reads_content() -> None:
    with TemporaryDirectory() as temp_dir:
        store = FileBlobStore(Path(temp_dir))

        ref = asyncio.run(store.write("hello world"))

        assert store.read(ref) == "hello world"
        assert (Path(temp_dir) / "blobs" / f"{ref}.txt").exists()


def test_file_session_store_round_trips_checkpoint_and_snapshot() -> None:
    with TemporaryDirectory() as temp_dir:
        store = FileSessionStore(Path(temp_dir))
        messages = [Message.system("sys"), Message.user("hi")]
        checkpoint = Checkpoint(
            session_id="session-1",
            state=RuntimeState.RUNNING,
            messages=messages,
        )

        store.save_checkpoint(checkpoint)
        store.save_session_snapshot(
            "session-1",
            messages=messages,
            state=RuntimeState.WAITING_FOR_USER,
            is_running=False,
        )

        restored_checkpoint = store.load_checkpoint("session-1")
        restored_snapshot = store.load_session_snapshot("session-1")

        assert restored_checkpoint is not None
        assert restored_checkpoint.state is RuntimeState.RUNNING
        assert [message.content for message in restored_checkpoint.messages] == ["sys", "hi"]
        assert restored_snapshot is not None
        assert restored_snapshot.state is RuntimeState.WAITING_FOR_USER
        assert restored_snapshot.is_running is False

        checkpoint_path = Path(temp_dir) / "checkpoints" / "session-1.json"
        snapshot_path = Path(temp_dir) / "sessions" / "session-1.json"
        assert json.loads(checkpoint_path.read_text(encoding="utf-8"))["state"] == "running"
        assert json.loads(snapshot_path.read_text(encoding="utf-8"))["is_running"] is False
