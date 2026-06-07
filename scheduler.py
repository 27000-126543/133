import time
import threading
from datetime import datetime, date
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass, field
import calendar

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False

from compliance_engine import get_compliance_engine
from task_manager import get_task_manager
from certificate_validator import get_certificate_validator
from report_generator import get_report_generator
from training_engine import get_training_engine
from audit_logger import get_audit_logger
from config import Config


@dataclass
class ScheduledTaskResult:
    task_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    success: bool = False
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


class TaskScheduler:
    def __init__(self):
        self.use_apscheduler = APSCHEDULER_AVAILABLE
        self.scheduler = None
        self._custom_thread = None
        self._shutdown = False
        self._last_execution = {}
        self.audit_logger = get_audit_logger()
        
        if self.use_apscheduler:
            self._init_apscheduler()
        else:
            print("Warning: APScheduler not available, using simple scheduler")
    
    def _init_apscheduler(self):
        self.scheduler = BackgroundScheduler(timezone=Config.SCHEDULER_TIMEZONE)
        
        hour, minute = Config.DAILY_CHECK_TIME.split(":")
        self.scheduler.add_job(
            self.daily_compliance_check,
            trigger=CronTrigger(
                hour=int(hour),
                minute=int(minute),
                timezone=Config.SCHEDULER_TIMEZONE
            ),
            id="daily_compliance_check",
            name="每日合规检查",
            replace_existing=True,
        )
        
        hour, minute = Config.MONTHLY_REPORT_TIME.split(":")
        self.scheduler.add_job(
            self.monthly_report_generation,
            trigger=CronTrigger(
                day=Config.MONTHLY_REPORT_DAY,
                hour=int(hour),
                minute=int(minute),
                timezone=Config.SCHEDULER_TIMEZONE
            ),
            id="monthly_report_generation",
            name="月度报告生成",
            replace_existing=True,
        )
        
        self.scheduler.add_job(
            self.hourly_task_reminder,
            trigger=IntervalTrigger(
                hours=24,
                timezone=Config.SCHEDULER_TIMEZONE
            ),
            id="hourly_task_reminder",
            name="任务催办检查",
            replace_existing=True,
        )
    
    def _run_custom_scheduler(self):
        while not self._shutdown:
            try:
                now = datetime.now()
                
                if self._should_run_daily(now):
                    self.daily_compliance_check()
                    self._last_execution["daily"] = now.date()
                
                if self._should_run_monthly(now):
                    self.monthly_report_generation()
                    self._last_execution["monthly"] = now.date()
                
                if self._should_run_reminder(now):
                    self.hourly_task_reminder()
                    self._last_execution["reminder"] = now
                
                time.sleep(60)
            except Exception as e:
                self.audit_logger.logger.error(f"Scheduler error: {e}")
                time.sleep(60)
    
    def _should_run_daily(self, now: datetime) -> bool:
        last_run = self._last_execution.get("daily")
        if last_run and last_run >= now.date():
            return False
        
        hour, minute = Config.DAILY_CHECK_TIME.split(":")
        target_time = now.replace(hour=int(hour), minute=int(minute), second=0, microsecond=0)
        
        return now >= target_time
    
    def _should_run_monthly(self, now: datetime) -> bool:
        last_run = self._last_execution.get("monthly")
        if last_run and last_run >= now.date():
            return False
        
        if now.day != Config.MONTHLY_REPORT_DAY:
            return False
        
        hour, minute = Config.MONTHLY_REPORT_TIME.split(":")
        target_time = now.replace(hour=int(hour), minute=int(minute), second=0, microsecond=0)
        
        return now >= target_time
    
    def _should_run_reminder(self, now: datetime) -> bool:
        last_run = self._last_execution.get("reminder")
        if not last_run:
            return True
        
        delta = now - last_run
        return delta.total_seconds() >= 24 * 3600
    
    def start(self):
        if self.use_apscheduler and self.scheduler:
            if not self.scheduler.running:
                self.scheduler.start()
                self.audit_logger.logger.info("APScheduler started successfully")
        else:
            if not self._custom_thread:
                self._custom_thread = threading.Thread(
                    target=self._run_custom_scheduler,
                    daemon=True,
                    name="CustomScheduler"
                )
                self._custom_thread.start()
                self.audit_logger.logger.info("Custom scheduler started successfully")
    
    def shutdown(self):
        self._shutdown = True
        
        if self.use_apscheduler and self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            self.audit_logger.logger.info("APScheduler shutdown successfully")
        
        if self._custom_thread:
            self._custom_thread.join(timeout=10)
            self.audit_logger.logger.info("Custom scheduler shutdown successfully")
    
    def daily_compliance_check(self) -> ScheduledTaskResult:
        start_time = datetime.now()
        result = ScheduledTaskResult(
            task_name="daily_compliance_check",
            start_time=start_time,
        )
        
        try:
            compliance_engine = get_compliance_engine()
            task_manager = get_task_manager()
            certificate_validator = get_certificate_validator()
            training_engine = get_training_engine()
            
            expiry_stats = certificate_validator.check_and_update_expired_certificates()
            result.details["expiry_stats"] = expiry_stats
            
            tasks_created, issues_count = task_manager.generate_tasks_from_daily_check()
            result.details["tasks_created"] = len(tasks_created)
            result.details["issues_count"] = issues_count
            
            for task in tasks_created:
                self.audit_logger.log_task_creation(
                    task_id=task.id,
                    creator_id=None,
                    creator_name="SYSTEM",
                    employee_id=task.employee_id,
                    task_type=task.task_type,
                    title=task.title,
                )
            
            escalated_tasks = task_manager.escalate_overdue_tasks()
            result.details["escalated_tasks"] = len(escalated_tasks)
            
            for task in escalated_tasks:
                old_assignee = task.assignee.name if task.assignee else "Unknown"
                self.audit_logger.log_task_escalation(
                    task_id=task.id,
                    old_assignee=old_assignee,
                    new_assignee=task.assignee.name if task.assignee else "Unknown",
                    escalation_level=task.escalation_level,
                )
            
            training_plans = training_engine.auto_generate_training_plans()
            result.details["training_plans_created"] = len(training_plans)
            
            for plan in training_plans:
                self.audit_logger.log_training_plan(
                    plan_id=plan.id,
                    department_id=plan.department_id,
                    plan_code=plan.plan_code,
                    plan_name=plan.name,
                )
            
            result.success = True
            result.end_time = datetime.now()
            
            self.audit_logger.log_scheduled_task(
                task_name="compliance_check",
                start_time=start_time,
                end_time=result.end_time,
                success=True,
                **result.details,
            )
            
        except Exception as e:
            result.success = False
            result.error_message = str(e)
            result.end_time = datetime.now()
            
            self.audit_logger.log_scheduled_task(
                task_name="compliance_check",
                start_time=start_time,
                end_time=result.end_time,
                success=False,
                error_msg=str(e),
            )
            self.audit_logger.logger.error(f"Daily compliance check failed: {e}")
        
        return result
    
    def hourly_task_reminder(self) -> ScheduledTaskResult:
        start_time = datetime.now()
        result = ScheduledTaskResult(
            task_name="hourly_task_reminder",
            start_time=start_time,
        )
        
        try:
            task_manager = get_task_manager()
            reminded_tasks = task_manager.send_reminders()
            
            result.details["reminded_tasks"] = len(reminded_tasks)
            result.success = True
            result.end_time = datetime.now()
            
            self.audit_logger.log_scheduled_task(
                task_name="task_reminder",
                start_time=start_time,
                end_time=result.end_time,
                success=True,
                **result.details,
            )
            
        except Exception as e:
            result.success = False
            result.error_message = str(e)
            result.end_time = datetime.now()
            
            self.audit_logger.log_scheduled_task(
                task_name="task_reminder",
                start_time=start_time,
                end_time=result.end_time,
                success=False,
                error_msg=str(e),
            )
        
        return result
    
    def monthly_report_generation(self) -> ScheduledTaskResult:
        start_time = datetime.now()
        result = ScheduledTaskResult(
            task_name="monthly_report_generation",
            start_time=start_time,
        )
        
        try:
            report_generator = get_report_generator()
            report_data = report_generator.generate_monthly_report()
            
            result.details["report_month"] = report_data["report_month"]
            result.details["excel_path"] = report_data["reports"]["excel"]
            result.details["pdf_path"] = report_data["reports"]["pdf"]
            result.details["departments_count"] = len(report_data["departments"])
            
            result.success = True
            result.end_time = datetime.now()
            
            self.audit_logger.log_report_generation(
                report_month=report_data["report_month"],
                excel_path=report_data["reports"]["excel"],
                pdf_path=report_data["reports"]["pdf"],
                departments_count=len(report_data["departments"]),
            )
            
            self.audit_logger.log_scheduled_task(
                task_name="report_generation",
                start_time=start_time,
                end_time=result.end_time,
                success=True,
                **result.details,
            )
            
        except Exception as e:
            result.success = False
            result.error_message = str(e)
            result.end_time = datetime.now()
            
            self.audit_logger.log_scheduled_task(
                task_name="report_generation",
                start_time=start_time,
                end_time=result.end_time,
                success=False,
                error_msg=str(e),
            )
            self.audit_logger.logger.error(f"Monthly report generation failed: {e}")
        
        return result
    
    def run_manual_task(self, task_name: str) -> ScheduledTaskResult:
        tasks = {
            "daily_compliance_check": self.daily_compliance_check,
            "monthly_report_generation": self.monthly_report_generation,
            "hourly_task_reminder": self.hourly_task_reminder,
        }
        
        if task_name not in tasks:
            raise ValueError(f"Unknown task: {task_name}. Available tasks: {list(tasks.keys())}")
        
        return tasks[task_name]()
    
    def get_scheduled_jobs(self) -> list:
        if self.use_apscheduler and self.scheduler:
            jobs = []
            for job in self.scheduler.get_jobs():
                next_run = getattr(job, 'next_run_time', None)
                jobs.append({
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": next_run.isoformat() if next_run else None,
                    "trigger": str(job.trigger),
                })
            return jobs
        else:
            return [
                {
                    "id": "daily_compliance_check",
                    "name": "每日合规检查",
                    "schedule": f"每天 {Config.DAILY_CHECK_TIME}",
                    "last_run": self._last_execution.get("daily"),
                },
                {
                    "id": "monthly_report_generation",
                    "name": "月度报告生成",
                    "schedule": f"每月 {Config.MONTHLY_REPORT_DAY}号 {Config.MONTHLY_REPORT_TIME}",
                    "last_run": self._last_execution.get("monthly"),
                },
                {
                    "id": "hourly_task_reminder",
                    "name": "任务催办检查",
                    "schedule": "每24小时",
                    "last_run": self._last_execution.get("reminder"),
                },
            ]


_scheduler_singleton = None


def get_scheduler() -> TaskScheduler:
    global _scheduler_singleton
    if _scheduler_singleton is None:
        _scheduler_singleton = TaskScheduler()
    return _scheduler_singleton
