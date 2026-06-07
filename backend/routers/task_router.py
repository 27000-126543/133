from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from datetime import date

from database import get_db_session
from models import Employee, Task
from auth import User, UserRole
from security import get_current_active_user, require_role
from audit_logger import get_audit_logger
from task_manager import get_task_manager

router = APIRouter(prefix="/tasks", tags=["任务管理"])
audit_logger = get_audit_logger()
task_manager = get_task_manager()


@router.get("/")
async def get_tasks(
    assignee_id: Optional[int] = None,
    employee_id: Optional[int] = None,
    department_id: Optional[int] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    task_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user)
):
    """获取任务列表"""
    if current_user.role == UserRole.EMPLOYEE.value:
        assignee_id = current_user.employee_id
    elif department_id and current_user.role == UserRole.MANAGER.value:
        with get_db_session() as session:
            emp = session.query(Employee).filter(Employee.id == current_user.employee_id).first()
            if emp and emp.department_id and emp.department.manager_id == current_user.employee_id:
                pass
            else:
                department_id = None
    
    tasks = task_manager.get_pending_tasks(assignee_id, department_id)
    
    if status:
        tasks = [t for t in tasks if t.status == status]
    if priority:
        tasks = [t for t in tasks if t.priority == priority]
    if task_type:
        tasks = [t for t in tasks if t.task_type == task_type]
    if employee_id:
        tasks = [t for t in tasks if t.employee_id == employee_id]
    
    total = len(tasks)
    paginated = tasks[skip:skip + limit]
    
    return {
        "total": total,
        "items": [
            {
                "id": t.id,
                "task_type": t.task_type,
                "title": t.title,
                "description": t.description,
                "employee_id": t.employee_id,
                "employee_name": t.employee.name if t.employee else None,
                "assignee_id": t.assignee_id,
                "assignee_name": t.assignee.name if t.assignee else None,
                "certificate_id": t.certificate_id,
                "cert_name": t.certificate.cert_name if t.certificate else None,
                "deadline": t.deadline.isoformat() if t.deadline else None,
                "status": t.status,
                "priority": t.priority,
                "escalation_level": t.escalation_level,
                "reminder_count": t.reminder_count,
                "last_reminder_at": t.last_reminder_at.isoformat() if t.last_reminder_at else None,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "days_overdue": (date.today() - t.deadline).days if t.deadline and t.deadline < date.today() else None,
                "created_at": t.created_at.isoformat(),
            }
            for t in paginated
        ]
    }


@router.get("/{task_id}")
async def get_task(task_id: int, current_user: User = Depends(get_current_active_user)):
    """获取任务详情"""
    with get_db_session() as session:
        task = session.query(Task).filter(Task.id == task_id).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        if current_user.role == UserRole.EMPLOYEE.value:
            if task.assignee_id != current_user.employee_id and task.employee_id != current_user.employee_id:
                raise HTTPException(status_code=403, detail="无权查看此任务")
        
        return {
            "id": task.id,
            "task_type": task.task_type,
            "title": task.title,
            "description": task.description,
            "employee_id": task.employee_id,
            "employee_name": task.employee.name if task.employee else None,
            "assignee_id": task.assignee_id,
            "assignee_name": task.assignee.name if task.assignee else None,
            "certificate_id": task.certificate_id,
            "cert_name": task.certificate.cert_name if task.certificate else None,
            "deadline": task.deadline.isoformat() if task.deadline else None,
            "status": task.status,
            "priority": task.priority,
            "escalation_level": task.escalation_level,
            "reminder_count": task.reminder_count,
            "last_reminder_at": task.last_reminder_at.isoformat() if task.last_reminder_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "completed_notes": task.completed_notes,
            "created_at": task.created_at.isoformat(),
        }


@router.post("/{task_id}/complete")
async def complete_task(
    task_id: int,
    completion_notes: str,
    current_user: User = Depends(get_current_active_user)
):
    """完成任务"""
    with get_db_session() as session:
        task = session.query(Task).filter(Task.id == task_id).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        if current_user.role == UserRole.EMPLOYEE.value:
            if task.assignee_id != current_user.employee_id:
                raise HTTPException(status_code=403, detail="无权处理此任务")
        
        result = task_manager.complete_task(task_id, completion_notes, current_user.employee_id)
        
        if not result:
            raise HTTPException(status_code=400, detail="任务完成失败")
        
        audit_logger.log_task_completion(
            task_id=task_id,
            completer_id=current_user.employee_id,
            completer_name=current_user.full_name,
            notes=completion_notes,
        )
        
        return {
            "success": True,
            "message": "任务已完成",
            "task_id": task_id,
        }


@router.post("/{task_id}/approve")
async def approve_task(
    task_id: int,
    approval_notes: str = "",
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER]))
):
    """审批任务（管理员/经理）"""
    result = task_manager.complete_task(task_id, f"审批通过: {approval_notes}", current_user.employee_id)
    
    if not result:
        raise HTTPException(status_code=400, detail="任务审批失败")
    
    audit_logger.log(
        action="task_approve",
        user_id=current_user.id,
        user_name=current_user.full_name,
        resource_type="task",
        resource_id=task_id,
        details={"notes": approval_notes},
    )
    
    return {
        "success": True,
        "message": "任务已审批通过",
        "task_id": task_id,
    }


@router.post("/{task_id}/reject")
async def reject_task(
    task_id: int,
    reject_reason: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER]))
):
    """驳回任务（管理员/经理）"""
    with get_db_session() as session:
        task = session.query(Task).filter(Task.id == task_id).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        task.description += f"\n\n【已驳回】{reject_reason}"
        task.status = "rejected" if hasattr(task, 'status') else task.status
        
        audit_logger.log(
            action="task_reject",
            user_id=current_user.id,
            user_name=current_user.full_name,
            resource_type="task",
            resource_id=task_id,
            details={"reason": reject_reason},
        )
        
        return {
            "success": True,
            "message": "任务已驳回",
            "task_id": task_id,
        }


@router.get("/statistics/summary")
async def get_task_statistics(current_user: User = Depends(get_current_active_user)):
    """获取任务统计"""
    stats = task_manager.get_task_statistics()
    return stats


@router.post("/run-daily-check")
async def run_daily_check(current_user: User = Depends(require_role([UserRole.ADMIN]))):
    """手动执行每日合规检查"""
    from scheduler import get_scheduler
    scheduler = get_scheduler()
    result = scheduler.daily_compliance_check()
    
    return {
        "success": result.success,
        "task_name": result.task_name,
        "start_time": result.start_time.isoformat(),
        "end_time": result.end_time.isoformat() if result.end_time else None,
        "error_message": result.error_message,
        "details": result.details,
    }
