from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.storage.db.models import User
from server.services.tasker import tasker
from server.utils.auth_middleware import get_admin_user

tasks = APIRouter(prefix="/tasks", tags=["tasks"])


class BatchDeleteRequest(BaseModel):
    task_ids: list[str]


class CleanupRequest(BaseModel):
    status: str | None = None
    older_than: str | None = None
    keep_count: int | None = None


@tasks.get("")
async def list_tasks(
    status: str | None = Query(default=None),
    current_user: User = Depends(get_admin_user),
):
    """List tasks, optionally filtered by status."""
    task_list = await tasker.list_tasks(status=status)
    return {"tasks": task_list}


@tasks.get("/{task_id}")
async def get_task(task_id: str, current_user: User = Depends(get_admin_user)):
    """Retrieve a single task by id."""
    task = await tasker.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task": task}


@tasks.delete("/batch")
async def delete_tasks_batch(
    request: BatchDeleteRequest,
    current_user: User = Depends(get_admin_user)
):
    """Delete multiple tasks."""
    if not request.task_ids:
        raise HTTPException(status_code=400, detail="No task IDs provided")

    results = await tasker.delete_tasks_batch(request.task_ids)
    successful_count = sum(results.values())

    return {
        "total": len(request.task_ids),
        "successful": successful_count,
        "failed": len(request.task_ids) - successful_count,
        "results": results
    }


@tasks.delete("/cleanup")
async def cleanup_tasks(
    request: CleanupRequest,
    current_user: User = Depends(get_admin_user)
):
    """Clean up tasks based on criteria."""
    deleted_count = await tasker.cleanup_tasks(
        status=request.status,
        older_than=request.older_than,
        keep_count=request.keep_count
    )

    return {
        "deleted_count": deleted_count,
        "criteria": {
            "status": request.status,
            "older_than": request.older_than,
            "keep_count": request.keep_count
        }
    }


@tasks.post("/{task_id}/cancel")
async def cancel_task(task_id: str, current_user: User = Depends(get_admin_user)):
    """Request cancellation of a task."""
    success = await tasker.cancel_task(task_id)
    if not success:
        raise HTTPException(status_code=400, detail="Task cannot be cancelled")
    return {"task_id": task_id, "status": "cancelled"}


@tasks.delete("/{task_id}")
async def delete_task(task_id: str, current_user: User = Depends(get_admin_user)):
    """Delete a task by ID. If task is running, it will be cancelled first."""
    success = await tasker.delete_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": task_id, "deleted": True}
