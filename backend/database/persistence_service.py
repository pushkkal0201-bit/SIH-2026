from __future__ import annotations

import asyncio

from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Deque, Dict, Optional
from uuid import UUID

from backend.database.database import database_session
from backend.database.repository import add_telemetry_batch


PERSISTENCE_SERVICE_VERSION = "1.1.0"

DEFAULT_BATCH_SIZE = 50
DEFAULT_FLUSH_INTERVAL_SEC = 2.0
MAX_BUFFER_SIZE = 10_000


class PersistenceItem:

    def __init__(
        self,
        *,
        mission_id: UUID,
        telemetry: Dict[str, Any],
    ) -> None:

        self.mission_id = mission_id
        self.telemetry = telemetry


class TelemetryPersistenceService:

    def __init__(
        self,
        *,
        batch_size: int = DEFAULT_BATCH_SIZE,
        flush_interval_sec: float = DEFAULT_FLUSH_INTERVAL_SEC,
        max_buffer_size: int = MAX_BUFFER_SIZE,
    ) -> None:

        self.batch_size = max(
            1,
            int(batch_size),
        )

        self.flush_interval_sec = max(
            0.1,
            float(flush_interval_sec),
        )

        self.max_buffer_size = max(
            self.batch_size,
            int(max_buffer_size),
        )

        self._buffer: Deque[
            PersistenceItem
        ] = deque()

        self._lock = Lock()

        self._flush_lock: Optional[
            asyncio.Lock
        ] = None

        self._worker_task: Optional[
            asyncio.Task
        ] = None

        self._running = False

        self._queued_frames = 0
        self._persisted_frames = 0
        self._failed_frames = 0
        self._dropped_frames = 0

        self._flush_count = 0
        self._failed_flushes = 0

        self._last_flush_at: Optional[
            datetime
        ] = None

        self._last_error: Optional[
            str
        ] = None


    def _get_flush_lock(
        self,
    ) -> asyncio.Lock:

        if self._flush_lock is None:
            self._flush_lock = asyncio.Lock()

        return self._flush_lock


    async def start(
        self,
    ) -> None:

        if self._running:
            return

        self._running = True

        self._worker_task = asyncio.create_task(
            self._worker_loop(),
            name="pratirup-postgresql-persistence",
        )


    async def stop(
        self,
    ) -> None:

        self._running = False

        task = self._worker_task

        if task is not None:

            try:
                await task

            except asyncio.CancelledError:
                pass

        self._worker_task = None

        await self.flush_all()


    def enqueue(
        self,
        *,
        mission_id: UUID,
        telemetry: Dict[str, Any],
    ) -> bool:

        if not isinstance(
            telemetry,
            dict,
        ):
            return False

        item = PersistenceItem(
            mission_id=mission_id,
            telemetry=telemetry,
        )

        with self._lock:

            if (
                len(self._buffer)
                >= self.max_buffer_size
            ):

                self._dropped_frames += 1

                self._last_error = (
                    "Persistence buffer capacity exceeded."
                )

                return False

            self._buffer.append(
                item
            )

            self._queued_frames += 1

        return True


    def _buffer_size(
        self,
    ) -> int:

        with self._lock:
            return len(
                self._buffer
            )


    def _take_batch(
        self,
    ) -> list[PersistenceItem]:

        batch: list[
            PersistenceItem
        ] = []

        with self._lock:

            while (
                self._buffer
                and
                len(batch)
                < self.batch_size
            ):

                batch.append(
                    self._buffer.popleft()
                )

        return batch


    def _restore_batch(
        self,
        batch: list[PersistenceItem],
    ) -> None:

        with self._lock:

            for item in reversed(
                batch
            ):

                if (
                    len(self._buffer)
                    >= self.max_buffer_size
                ):

                    self._dropped_frames += 1

                    continue

                self._buffer.appendleft(
                    item
                )


    @staticmethod
    def _write_batch_sync(
        batch: list[PersistenceItem],
    ) -> int:

        if not batch:
            return 0

        grouped: dict[
            UUID,
            list[Dict[str, Any]],
        ] = {}

        for item in batch:

            grouped.setdefault(
                item.mission_id,
                [],
            ).append(
                item.telemetry
            )

        inserted = 0

        with database_session() as db:

            for (
                mission_id,
                telemetry_frames,
            ) in grouped.items():

                inserted += (
                    add_telemetry_batch(
                        db,
                        mission_id=mission_id,
                        telemetry_frames=
                            telemetry_frames,
                    )
                )

        return inserted


    async def _flush_one_locked(
        self,
    ) -> tuple[int, bool]:

        batch = self._take_batch()

        if not batch:
            return 0, True

        try:

            inserted = await asyncio.to_thread(
                self._write_batch_sync,
                batch,
            )

            if inserted != len(batch):

                raise RuntimeError(
                    "Persistence batch count mismatch: "
                    f"attempted={len(batch)}, "
                    f"reported_inserted={inserted}"
                )

            self._persisted_frames += (
                inserted
            )

            self._flush_count += 1

            self._last_flush_at = (
                datetime.now(
                    timezone.utc
                )
            )

            self._last_error = None

            return inserted, True

        except Exception as exc:

            self._failed_flushes += 1

            self._failed_frames += len(
                batch
            )

            self._last_error = str(
                exc
            )

            self._restore_batch(
                batch
            )

            return 0, False


    async def flush(
        self,
    ) -> int:

        flush_lock = self._get_flush_lock()

        async with flush_lock:

            inserted, _ = (
                await self._flush_one_locked()
            )

            return inserted


    async def flush_all(
        self,
    ) -> int:

        flush_lock = self._get_flush_lock()

        total_inserted = 0

        async with flush_lock:

            while True:

                if self._buffer_size() == 0:
                    break

                inserted, success = (
                    await self._flush_one_locked()
                )

                total_inserted += (
                    inserted
                )

                if not success:
                    break

        return total_inserted


    async def _worker_loop(
        self,
    ) -> None:

        while self._running:

            try:

                await asyncio.sleep(
                    self.flush_interval_sec
                )

                if not self._running:
                    break

                await self.flush_all()

            except asyncio.CancelledError:
                break

            except Exception as exc:

                self._last_error = str(
                    exc
                )

                await asyncio.sleep(
                    self.flush_interval_sec
                )


    def get_status(
        self,
    ) -> Dict[str, Any]:

        with self._lock:

            buffer_size = len(
                self._buffer
            )

        return {

            "service":
                "postgresql_persistence",

            "version":
                PERSISTENCE_SERVICE_VERSION,

            "running":
                self._running,

            "batch_size":
                self.batch_size,

            "flush_interval_sec":
                self.flush_interval_sec,

            "buffer_size":
                buffer_size,

            "max_buffer_size":
                self.max_buffer_size,

            "queued_frames":
                self._queued_frames,

            "persisted_frames":
                self._persisted_frames,

            "failed_frames":
                self._failed_frames,

            "dropped_frames":
                self._dropped_frames,

            "flush_count":
                self._flush_count,

            "failed_flushes":
                self._failed_flushes,

            "last_flush_at":
                (
                    self._last_flush_at.isoformat()
                    if self._last_flush_at
                    else None
                ),

            "last_error":
                self._last_error,
        }


telemetry_persistence_service = (
    TelemetryPersistenceService()
)
