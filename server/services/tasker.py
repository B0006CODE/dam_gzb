import asyncio
import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from collections.abc import Awaitable, Callable

from src.config import config
from src.utils.logging_config import logger
from src.utils.datetime_utils import utc_isoformat

TaskCoroutine = Callable[["TaskContext"], Awaitable[Any]]
TERMINAL_STATUSES = {"success", "failed", "cancelled"}


def _utc_timestamp() -> str:
    return utc_isoformat()


@dataclass
class Task:
    id: str
    name: str
    type: str
    status: str = "pending"
    progress: float = 0.0
    message: str = ""
    created_at: str = field(default_factory=_utc_timestamp)
    updated_at: str = field(default_factory=_utc_timestamp)
    started_at: str | None = None
    completed_at: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    result: Any | None = None
    error: str | None = None
    cancel_requested: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        return cls(
            id=data["id"],
            name=data.get("name", "Unnamed Task"),
            type=data.get("type", "general"),
            status=data.get("status", "pending"),
            progress=data.get("progress", 0.0),
            message=data.get("message", ""),
            created_at=data.get("created_at", _utc_timestamp()),
            updated_at=data.get("updated_at", _utc_timestamp()),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            payload=data.get("payload", {}),
            result=data.get("result"),
            error=data.get("error"),
            cancel_requested=data.get("cancel_requested", False),
        )


class TaskContext:
    def __init__(self, tasker: "Tasker", task_id: str):
        self._tasker = tasker
        self.task_id = task_id

    async def set_progress(self, progress: float, message: str | None = None) -> None:
        await self._tasker._update_task(
            self.task_id,
            progress=max(0.0, min(progress, 100.0)),
            message=message,
        )

    async def set_message(self, message: str) -> None:
        await self._tasker._update_task(self.task_id, message=message)

    async def set_result(self, result: Any) -> None:
        await self._tasker._update_task(self.task_id, result=result)

    def is_cancel_requested(self) -> bool:
        return self._tasker._is_cancel_requested(self.task_id)

    async def raise_if_cancelled(self) -> None:
        if self.is_cancel_requested():
            raise asyncio.CancelledError("Task was cancelled")


class Tasker:
    def __init__(self, worker_count: int = 2):
        self.worker_count = max(1, worker_count)
        self._queue: asyncio.Queue[tuple[str, TaskCoroutine]] = asyncio.Queue()
        self._tasks: dict[str, Task] = {}
        self._lock = asyncio.Lock()
        self._workers: list[asyncio.Task[Any]] = []
        self._storage_path = Path(config.save_dir) / "tasks" / "tasks.json"
        os.makedirs(self._storage_path.parent, exist_ok=True)
        self._started = False

    async def start(self) -> None:
        async with self._lock:
            if self._started:
                return
            await self._load_state()
            for _ in range(self.worker_count):
                worker = asyncio.create_task(self._worker_loop(), name="tasker-worker")
                self._workers.append(worker)
            self._started = True
            logger.info("Tasker started with {} workers", self.worker_count)

    async def shutdown(self) -> None:
        async with self._lock:
            if not self._started:
                return
            for worker in self._workers:
                worker.cancel()
            await asyncio.gather(*self._workers, return_exceptions=True)
            self._workers.clear()
            await self._persist_state()
            self._started = False
            logger.info("Tasker shutdown complete")

    async def enqueue(
        self,
        *,
        name: str,
        task_type: str,
        payload: dict[str, Any] | None = None,
        coroutine: TaskCoroutine,
    ) -> Task:
        task_id = uuid.uuid4().hex
        task = Task(id=task_id, name=name, type=task_type, payload=payload or {})
        async with self._lock:
            self._tasks[task_id] = task
            await self._persist_state()
            await self._queue.put((task_id, coroutine))
        logger.info("Enqueued task {} ({})", task_id, name)
        return task

    async def list_tasks(self, status: str | None = None) -> list[dict[str, Any]]:
        async with self._lock:
            tasks = list(self._tasks.values())
        if status:
            tasks = [task for task in tasks if task.status == status]
        tasks.sort(key=lambda item: item.created_at or utc_isoformat(), reverse=True)
        return [task.to_dict() for task in tasks]

    async def get_task(self, task_id: str) -> dict[str, Any] | None:
        async with self._lock:
            task = self._tasks.get(task_id)
        return task.to_dict() if task else None

    async def cancel_task(self, task_id: str) -> bool:
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            if task.status in {"success", "failed", "cancelled"}:
                return False
            task.cancel_requested = True
            task.updated_at = _utc_timestamp()
            await self._persist_state()
        logger.info("Cancellation requested for task {}", task_id)
        return True

    async def delete_task(self, task_id: str) -> bool:
        """Delete a single task by ID. If task is running, it will be cancelled first."""
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                logger.warning("Task {} not found for deletion", task_id)
                return False

            logger.info("Deleting task: {} ({}), status: {}", task_id, task.name, task.status)

            # If task is running, cancel it first
            if task.status not in TERMINAL_STATUSES:
                task.cancel_requested = True
                task.updated_at = _utc_timestamp()
                logger.info("Task {} will be cancelled before deletion", task_id)

            # Remove task from storage
            del self._tasks[task_id]
            await self._persist_state()
        logger.info("Task {} deleted successfully", task_id)
        return True

    async def delete_tasks_batch(self, task_ids: list[str]) -> dict[str, bool]:
        """Delete multiple tasks. Returns dict of task_id -> success status."""
        logger.info("Starting batch delete for {} tasks: {}", len(task_ids), task_ids)
        results = {}
        successful_deletions = 0
        failed_deletions = []

        for task_id in task_ids:
            success = await self.delete_task(task_id)
            results[task_id] = success
            if success:
                successful_deletions += 1
            else:
                failed_deletions.append(task_id)

        logger.info("Batch delete completed: {} successful, {} failed",
                   successful_deletions, len(failed_deletions))
        if failed_deletions:
            logger.warning("Failed to delete tasks: {}", failed_deletions)

        return results

    async def cleanup_tasks(
        self,
        *,
        status: str | None = None,
        older_than: str | None = None,
        keep_count: int | None = None
    ) -> int:
        """
        Clean up tasks based on criteria.

        Args:
            status: Only delete tasks with this status
            older_than: Delete tasks older than this ISO timestamp
            keep_count: Keep only the most recent N tasks per status

        Returns:
            Number of deleted tasks
        """
        async with self._lock:
            total_tasks = len(self._tasks)
            logger.info("Starting cleanup with criteria: status={}, older_than={}, keep_count={}, total_tasks={}",
                       status, older_than, keep_count, total_tasks)

            tasks_to_delete = []
            tasks_by_status = {}

            for task in self._tasks.values():
                should_delete = True

                # Track tasks by status for debugging
                if task.status not in tasks_by_status:
                    tasks_by_status[task.status] = []
                tasks_by_status[task.status].append(task.id)

                # Filter by status
                if status and task.status != status:
                    should_delete = False
                    logger.debug("Task {} excluded by status filter: {} != {}",
                               task.id, task.status, status)

                # Filter by age - keep tasks newer than the specified time, delete older ones
                if older_than and task.created_at >= older_than:
                    should_delete = False
                    logger.debug("Task {} excluded by age filter: {} >= {}",
                               task.id, task.created_at, older_than)

                if should_delete:
                    tasks_to_delete.append(task.id)
                    logger.debug("Task {} marked for deletion: status={}, created_at={}",
                               task.id, task.status, task.created_at)

            logger.info("Tasks marked for deletion: {}", len(tasks_to_delete))
            logger.debug("Tasks by status: {}", {k: len(v) for k, v in tasks_by_status.items()})

            # Apply keep_count limit if specified
            if keep_count is not None:
                logger.debug("Applying keep_count limit: {}", keep_count)
                # Group tasks by status and keep most recent N per status
                status_groups = {}
                for task in self._tasks.values():
                    if task.status not in status_groups:
                        status_groups[task.status] = []
                    status_groups[task.status].append(task)

                # Determine tasks to keep
                tasks_to_keep = set()
                for status, status_tasks in status_groups.items():
                    status_tasks.sort(key=lambda t: t.created_at or "", reverse=True)
                    keep_tasks = status_tasks[:keep_count]
                    for task in keep_tasks:
                        tasks_to_keep.add(task.id)
                    logger.debug("Status {}: keeping {} most recent tasks", status, len(keep_tasks))

                # Remove tasks that should be kept from deletion list
                original_count = len(tasks_to_delete)
                tasks_to_delete = [tid for tid in tasks_to_delete if tid not in tasks_to_keep]
                logger.debug("Removed {} tasks from deletion list due to keep_count limit",
                           original_count - len(tasks_to_delete))

            # Delete the tasks
            deleted_count = 0
            failed_deletions = []

            for task_id in tasks_to_delete:
                if task_id in self._tasks:
                    task = self._tasks[task_id]
                    logger.debug("Deleting task: {} ({})", task_id, task.name)
                    del self._tasks[task_id]
                    deleted_count += 1
                else:
                    failed_deletions.append(task_id)
                    logger.warning("Task {} not found during cleanup, may have been deleted already", task_id)

            if failed_deletions:
                logger.warning("Failed to delete {} tasks (not found): {}",
                             len(failed_deletions), failed_deletions)

            if deleted_count > 0:
                await self._persist_state()
                logger.info("Successfully deleted {} tasks and persisted state", deleted_count)

        logger.info("Cleanup completed: {} tasks deleted out of {} total tasks",
                   deleted_count, total_tasks)
        return deleted_count

    async def _worker_loop(self) -> None:
        while True:
            try:
                task_id, coroutine = await self._queue.get()
                try:
                    task = await self._get_task_instance(task_id)
                    if not task:
                        continue
                    if task.cancel_requested:
                        await self._mark_cancelled(task_id, "Task was cancelled before execution")
                        continue
                    await self._update_task(
                        task_id, status="running", progress=0.0, message="任务开始执行", started_at=_utc_timestamp()
                    )
                    context = TaskContext(self, task_id)
                    try:
                        result = await coroutine(context)
                        if task.cancel_requested:
                            await self._mark_cancelled(task_id, "Task cancelled during execution")
                            continue
                        await self._update_task(
                            task_id,
                            status="success",
                            progress=100.0,
                            message="任务已完成",
                            result=result,
                            completed_at=_utc_timestamp(),
                        )
                    except asyncio.CancelledError:
                        await self._mark_cancelled(task_id, "任务被取消")
                    except Exception as exc:  # noqa: BLE001
                        logger.exception("Task {} failed: {}", task_id, exc)
                        await self._update_task(
                            task_id,
                            status="failed",
                            progress=100.0,
                            message="任务执行失败",
                            error=str(exc),
                            completed_at=_utc_timestamp(),
                        )
                finally:
                    self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as exc:  # noqa: BLE001
                logger.exception("Tasker worker error: {}", exc)

    async def _get_task_instance(self, task_id: str) -> Task | None:
        async with self._lock:
            return self._tasks.get(task_id)

    async def _mark_cancelled(self, task_id: str, message: str) -> None:
        await self._update_task(
            task_id,
            status="cancelled",
            progress=100.0,
            message=message,
            completed_at=_utc_timestamp(),
        )

    async def _update_task(
        self,
        task_id: str,
        *,
        status: str | None = None,
        progress: float | None = None,
        message: str | None = None,
        result: Any = None,
        error: str | None = None,
        started_at: str | None = None,
        completed_at: str | None = None,
    ) -> None:
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return
            if status:
                task.status = status
            if progress is not None:
                task.progress = max(0.0, min(progress, 100.0))
            if message is not None:
                task.message = message
            if result is not None:
                task.result = result
            if error is not None:
                task.error = error
            if started_at is not None:
                task.started_at = started_at
            if completed_at is not None:
                task.completed_at = completed_at
            task.updated_at = _utc_timestamp()
            await self._persist_state()

    def _is_cancel_requested(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        return bool(task and task.cancel_requested)

    async def _load_state(self) -> None:
        if not self._storage_path.exists():
            return
        try:
            content = await asyncio.to_thread(self._storage_path.read_text, encoding="utf-8")
            if not content.strip():
                return
            data = json.loads(content)
            tasks = data.get("tasks", [])
            for item in tasks:
                task = Task.from_dict(item)
                if task.status == "running":
                    task.status = "failed"
                    task.message = "服务重启时任务中断"
                    task.updated_at = _utc_timestamp()
                elif task.status not in TERMINAL_STATUSES:
                    task.status = "failed"
                    task.message = "服务重启时任务未继续执行"
                    task.updated_at = _utc_timestamp()
                self._tasks[task.id] = task
            logger.info("Loaded {} task records from storage", len(tasks))
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to load task state: {}", exc)

    async def _persist_state(self) -> None:
        tasks = [task.to_dict() for task in self._tasks.values()]
        payload = {"tasks": tasks, "updated_at": _utc_timestamp()}

        def _write() -> None:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self._storage_path.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self._storage_path)

        await asyncio.to_thread(_write)


tasker = Tasker()


__all__ = ["tasker", "TaskContext", "Tasker"]
