from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from enum import Enum

from sqlalchemy import and_, or_

from database import get_db_session
from models import Employee, Task, Certificate, Department
from config import Config
from compliance_engine import ComplianceIssue, ComplianceStatus, get_compliance_engine


class TaskType(str, Enum):
    RENEWAL = "renewal"
    SUPPLEMENT = "supplement"
    VERIFICATION = "verification"
    CORRECTION = "correction"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ESCALATED = "escalated"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskManager:
    def __init__(self):
        self.task_deadline_days = Config.TASK_DEADLINE_DAYS
        self.escalation_days = Config.ESCALATION_DAYS
        self.reminder_interval_days = Config.REMINDER_INTERVAL_DAYS
        self.compliance_engine = get_compliance_engine()
    
    def _get_department_manager(self, department_id: int) -> Optional[Employee]:
        with get_db_session() as session:
            dept = session.query(Department).filter(Department.id == department_id).first()
            if dept and dept.manager:
                return dept.manager
            return None
    
    def _determine_priority(self, issue: ComplianceIssue) -> TaskPriority:
        if issue.status == ComplianceStatus.EXPIRED:
            return TaskPriority.URGENT
        elif issue.status == ComplianceStatus.EXPIRING_SOON:
            if issue.days_to_expiry and issue.days_to_expiry <= 30:
                return TaskPriority.HIGH
            return TaskPriority.MEDIUM
        elif issue.status == ComplianceStatus.MISSING:
            if issue.requirement_level == "required":
                return TaskPriority.HIGH
            return TaskPriority.MEDIUM
        elif issue.status == ComplianceStatus.INSUFFICIENT_SCORE:
            return TaskPriority.MEDIUM
        else:
            return TaskPriority.LOW
    
    def _determine_task_type(self, issue: ComplianceIssue) -> TaskType:
        if issue.status in [ComplianceStatus.EXPIRED, ComplianceStatus.EXPIRING_SOON]:
            return TaskType.RENEWAL
        elif issue.status == ComplianceStatus.MISSING:
            return TaskType.SUPPLEMENT
        elif issue.status == ComplianceStatus.UNVERIFIED:
            return TaskType.VERIFICATION
        else:
            return TaskType.CORRECTION
    
    def _generate_task_title(self, issue: ComplianceIssue, task_type: TaskType) -> str:
        title_templates = {
            TaskType.RENEWAL: f"证书续期：{issue.cert_type_name}",
            TaskType.SUPPLEMENT: f"补办证书：{issue.cert_type_name}",
            TaskType.VERIFICATION: f"证书验证：{issue.cert_type_name}",
            TaskType.CORRECTION: f"证书更新：{issue.cert_type_name}",
        }
        return title_templates.get(task_type, f"证书处理：{issue.cert_type_name}")
    
    def _generate_task_description(self, issue: ComplianceIssue, task_type: TaskType, deadline: date) -> str:
        desc_parts = [
            f"员工：{issue.employee_name}（工号：{issue.employee_no}）",
            f"岗位：{issue.position}",
            f"问题：{issue.issue_description}",
        ]
        
        if task_type == TaskType.RENEWAL:
            desc_parts.append(f"当前证书到期时间：{issue.expiry_date}")
            desc_parts.append("请及时办理续期手续并上传新证书。")
        elif task_type == TaskType.SUPPLEMENT:
            desc_parts.append("此证书为岗位必需资质，请尽快获取并上传。")
        elif task_type == TaskType.VERIFICATION:
            desc_parts.append("您上传的证书正在等待验证，请配合提供相关证明材料。")
        
        desc_parts.append(f"任务截止日期：{deadline.strftime('%Y-%m-%d')}")
        
        return "\n".join(desc_parts)
    
    def _task_exists(self, employee_id: int, cert_type_id: int, task_type: TaskType, statuses: List[str]) -> bool:
        with get_db_session() as session:
            existing = session.query(Task).filter(
                Task.employee_id == employee_id,
                Task.certificate_id.isnot(None) if cert_type_id else True,
                Task.task_type == task_type.value,
                Task.status.in_(statuses)
            ).first()
            
            if existing and existing.certificate:
                return existing.certificate.cert_type_id == cert_type_id
            return existing is not None
    
    def create_task_from_issue(self, issue: ComplianceIssue) -> Optional[Task]:
        task_type = self._determine_task_type(issue)
        priority = self._determine_priority(issue)
        
        active_statuses = [TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value, TaskStatus.ESCALATED.value]
        if self._task_exists(issue.employee_id, issue.cert_type_id, task_type, active_statuses):
            return None
        
        deadline = date.today() + timedelta(days=self.task_deadline_days)
        
        with get_db_session() as session:
            assignee_id = issue.employee_id
            
            task = Task(
                task_type=task_type.value,
                title=self._generate_task_title(issue, task_type),
                description=self._generate_task_description(issue, task_type, deadline),
                employee_id=issue.employee_id,
                assignee_id=assignee_id,
                certificate_id=issue.certificate_id,
                deadline=deadline,
                status=TaskStatus.PENDING.value,
                priority=priority.value,
                escalation_level=0,
                reminder_count=0,
            )
            
            session.add(task)
            session.flush()
            task_id = task.id
        
        with get_db_session() as session:
            return session.query(Task).filter(Task.id == task_id).first()
    
    def create_tasks_from_compliance_issues(self, issues: List[ComplianceIssue]) -> List[Task]:
        tasks = []
        for issue in issues:
            task = self.create_task_from_issue(issue)
            if task:
                tasks.append(task)
        return tasks
    
    def generate_tasks_from_daily_check(self) -> Tuple[List[Task], int]:
        reports = self.compliance_engine.check_all_employees_compliance()
        
        all_issues = []
        for report in reports:
            all_issues.extend(report.issues)
        
        tasks = self.create_tasks_from_compliance_issues(all_issues)
        
        return tasks, len(all_issues)
    
    def escalate_overdue_tasks(self) -> List[Task]:
        today = date.today()
        escalated_tasks = []
        
        with get_db_session() as session:
            overdue_tasks = session.query(Task).filter(
                Task.status.in_([TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value]),
                Task.deadline < today
            ).all()
            
            for task in overdue_tasks:
                days_overdue = (today - task.deadline).days
                
                if days_overdue >= self.escalation_days and task.escalation_level == 0:
                    employee = session.query(Employee).filter(Employee.id == task.employee_id).first()
                    if employee and employee.department:
                        manager = employee.department.manager
                        if manager and manager.id != task.assignee_id:
                            task.escalation_level = 1
                            task.status = TaskStatus.ESCALATED.value
                            task.assignee_id = manager.id
                            task.description += f"\n\n【已升级】任务超期{days_overdue}天，已升级至部门主管{manager.name}处理。"
                            
                            escalated_tasks.append(task)
                            print(f"Task {task.id} escalated to manager {manager.name}")
        
        return escalated_tasks
    
    def send_reminders(self) -> List[Task]:
        today = date.today()
        reminded_tasks = []
        
        with get_db_session() as session:
            active_tasks = session.query(Task).filter(
                Task.status.in_([
                    TaskStatus.PENDING.value,
                    TaskStatus.IN_PROGRESS.value,
                    TaskStatus.ESCALATED.value
                ])
            ).all()
            
            for task in active_tasks:
                should_remind = False
                
                if task.last_reminder_at is None:
                    should_remind = True
                else:
                    days_since_reminder = (today - task.last_reminder_at.date()).days
                    if days_since_reminder >= self.reminder_interval_days:
                        should_remind = True
                
                if should_remind:
                    days_to_deadline = (task.deadline - today).days
                    
                    if days_to_deadline >= 0:
                        reminder_msg = f"【催办提醒】任务还剩{days_to_deadline}天截止，请尽快处理。"
                    else:
                        reminder_msg = f"【超期催办】任务已超期{abs(days_to_deadline)}天，请立即处理！"
                    
                    task.description += f"\n\n{reminder_msg} (第{task.reminder_count + 1}次催办)"
                    task.last_reminder_at = datetime.now()
                    task.reminder_count += 1
                    
                    reminded_tasks.append(task)
        
        return reminded_tasks
    
    def complete_task(self, task_id: int, completion_notes: str, completed_by: Optional[int] = None) -> Optional[Task]:
        with get_db_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            
            if not task:
                return None
            
            task.status = TaskStatus.COMPLETED.value
            task.completed_at = datetime.now()
            task.completed_notes = completion_notes
            
            if completed_by:
                task.assignee_id = completed_by
            
            return task
    
    def cancel_task(self, task_id: int, reason: str, cancelled_by: Optional[int] = None) -> Optional[Task]:
        with get_db_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            
            if not task:
                return None
            
            task.status = TaskStatus.CANCELLED.value
            task.completed_at = datetime.now()
            task.completed_notes = f"任务已取消，原因：{reason}"
            
            return task
    
    def get_pending_tasks(self, assignee_id: Optional[int] = None, department_id: Optional[int] = None) -> List[Task]:
        with get_db_session() as session:
            query = session.query(Task).filter(
                Task.status.in_([
                    TaskStatus.PENDING.value,
                    TaskStatus.IN_PROGRESS.value,
                    TaskStatus.ESCALATED.value
                ])
            )
            
            if assignee_id:
                query = query.filter(Task.assignee_id == assignee_id)
            
            if department_id:
                query = query.join(Employee, Task.employee_id == Employee.id).filter(
                    Employee.department_id == department_id
                )
            
            query = query.order_by(Task.deadline.asc(), Task.priority.desc())
            
            return query.all()
    
    def get_task_statistics(self) -> Dict:
        today = date.today()
        
        with get_db_session() as session:
            total = session.query(Task).count()
            pending = session.query(Task).filter(Task.status == TaskStatus.PENDING.value).count()
            in_progress = session.query(Task).filter(Task.status == TaskStatus.IN_PROGRESS.value).count()
            escalated = session.query(Task).filter(Task.status == TaskStatus.ESCALATED.value).count()
            completed = session.query(Task).filter(Task.status == TaskStatus.COMPLETED.value).count()
            cancelled = session.query(Task).filter(Task.status == TaskStatus.CANCELLED.value).count()
            
            overdue = session.query(Task).filter(
                Task.status.in_([TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value, TaskStatus.ESCALATED.value]),
                Task.deadline < today
            ).count()
            
            due_soon = session.query(Task).filter(
                Task.status.in_([TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value, TaskStatus.ESCALATED.value]),
                Task.deadline >= today,
                Task.deadline <= today + timedelta(days=7)
            ).count()
        
        return {
            "total": total,
            "pending": pending,
            "in_progress": in_progress,
            "escalated": escalated,
            "completed": completed,
            "cancelled": cancelled,
            "overdue": overdue,
            "due_soon": due_soon,
        }


_task_manager_singleton = None


def get_task_manager() -> TaskManager:
    global _task_manager_singleton
    if _task_manager_singleton is None:
        _task_manager_singleton = TaskManager()
    return _task_manager_singleton
