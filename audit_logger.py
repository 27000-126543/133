import os
import logging
import json
import time
import threading
import queue
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from functools import wraps
from contextlib import contextmanager

from database import get_db_session
from models import AuditLog
from config import Config


Config.ensure_dirs()


class AuditLogger:
    def __init__(self):
        self.log_file = Config.LOG_FILE
        self.log_level = getattr(logging, Config.LOG_LEVEL, logging.INFO)
        self._setup_logger()
        self._async_queue = queue.Queue(maxsize=10000)
        self._async_thread = None
        self._start_async_writer()
    
    def _setup_logger(self):
        self.logger = logging.getLogger("cert_management")
        self.logger.setLevel(self.log_level)
        self.logger.propagate = False
        
        if not self.logger.handlers:
            file_handler = logging.FileHandler(self.log_file, encoding="utf-8")
            file_handler.setLevel(self.log_level)
            
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.WARNING)
            
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
    
    def _start_async_writer(self):
        def writer():
            while True:
                try:
                    log_entry = self._async_queue.get(timeout=1)
                    if log_entry is None:
                        break
                    self._write_audit_log(**log_entry)
                except queue.Empty:
                    continue
                except Exception as e:
                    self.logger.error(f"Error writing audit log: {e}")
        
        self._async_thread = threading.Thread(target=writer, daemon=True)
        self._async_thread.start()
    
    def _write_audit_log(self,
                         action: str,
                         user_id: Optional[int] = None,
                         user_name: Optional[str] = None,
                         resource_type: Optional[str] = None,
                         resource_id: Optional[int] = None,
                         details: Optional[Dict] = None,
                         ip_address: Optional[str] = None,
                         user_agent: Optional[str] = None,
                         status: str = "success"):
        try:
            with get_db_session() as session:
                audit_log = AuditLog(
                    timestamp=datetime.now(),
                    user_id=user_id,
                    user_name=user_name,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    details=details,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    status=status,
                )
                session.add(audit_log)
        except Exception as e:
            self.logger.error(f"Failed to write audit log to DB: {e}")
    
    def log(self,
            action: str,
            user_id: Optional[int] = None,
            user_name: Optional[str] = None,
            resource_type: Optional[str] = None,
            resource_id: Optional[int] = None,
            details: Optional[Dict] = None,
            ip_address: Optional[str] = None,
            user_agent: Optional[str] = None,
            status: str = "success",
            sync: bool = False):
        log_entry = {
            "action": action,
            "user_id": user_id,
            "user_name": user_name,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "status": status,
        }
        
        log_msg = f"Action: {action}, User: {user_name}({user_id}), " \
                  f"Resource: {resource_type}({resource_id}), Status: {status}"
        if status == "success":
            self.logger.info(log_msg)
        else:
            self.logger.error(log_msg)
        
        if sync:
            self._write_audit_log(**log_entry)
        else:
            try:
                self._async_queue.put_nowait(log_entry)
            except queue.Full:
                self.logger.warning("Audit log queue full, writing synchronously")
                self._write_audit_log(**log_entry)
    
    def log_certificate_upload(self, employee_id: int, employee_name: str, 
                               certificate_id: int, success: bool, **kwargs):
        self.log(
            action="certificate_upload",
            user_id=employee_id,
            user_name=employee_name,
            resource_type="certificate",
            resource_id=certificate_id,
            details=kwargs,
            status="success" if success else "failed",
        )
    
    def log_certificate_verification(self, certificate_id: int, verifier_id: int,
                                     verifier_name: str, verified: bool, **kwargs):
        self.log(
            action="certificate_verification",
            user_id=verifier_id,
            user_name=verifier_name,
            resource_type="certificate",
            resource_id=certificate_id,
            details={"verified": verified, **kwargs},
            status="success",
        )
    
    def log_task_creation(self, task_id: int, creator_id: int, creator_name: str,
                          employee_id: int, task_type: str, **kwargs):
        self.log(
            action="task_creation",
            user_id=creator_id,
            user_name=creator_name,
            resource_type="task",
            resource_id=task_id,
            details={"employee_id": employee_id, "task_type": task_type, **kwargs},
            status="success",
        )
    
    def log_task_escalation(self, task_id: int, old_assignee: str, new_assignee: str,
                            escalation_level: int, **kwargs):
        self.log(
            action="task_escalation",
            user_id=None,
            user_name="SYSTEM",
            resource_type="task",
            resource_id=task_id,
            details={
                "old_assignee": old_assignee,
                "new_assignee": new_assignee,
                "escalation_level": escalation_level,
                **kwargs
            },
            status="success",
        )
    
    def log_task_completion(self, task_id: int, completer_id: int, completer_name: str, **kwargs):
        self.log(
            action="task_completion",
            user_id=completer_id,
            user_name=completer_name,
            resource_type="task",
            resource_id=task_id,
            details=kwargs,
            status="success",
        )
    
    def log_batch_import(self, batch_no: str, imported_by: int, importer_name: str,
                         success_count: int, error_count: int, duplicate_count: int, **kwargs):
        self.log(
            action="batch_import",
            user_id=imported_by,
            user_name=importer_name,
            resource_type="import_batch",
            resource_id=None,
            details={
                "batch_no": batch_no,
                "success_count": success_count,
                "error_count": error_count,
                "duplicate_count": duplicate_count,
                **kwargs
            },
            status="success",
        )
    
    def log_report_generation(self, report_month: str, excel_path: str, pdf_path: str, **kwargs):
        self.log(
            action="report_generation",
            user_id=None,
            user_name="SYSTEM",
            resource_type="monthly_report",
            resource_id=None,
            details={
                "report_month": report_month,
                "excel_path": excel_path,
                "pdf_path": pdf_path,
                **kwargs
            },
            status="success",
        )
    
    def log_training_plan(self, plan_id: int, department_id: int, **kwargs):
        self.log(
            action="training_plan_creation",
            user_id=None,
            user_name="SYSTEM",
            resource_type="training_plan",
            resource_id=plan_id,
            details={"department_id": department_id, **kwargs},
            status="success",
        )
    
    def log_scheduled_task(self, task_name: str, start_time: datetime, end_time: datetime,
                           success: bool, error_msg: Optional[str] = None, **kwargs):
        self.log(
            action=f"scheduled_{task_name}",
            user_id=None,
            user_name="SYSTEM",
            resource_type="scheduled_task",
            resource_id=None,
            details={
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": (end_time - start_time).total_seconds(),
                "error_msg": error_msg,
                **kwargs
            },
            status="success" if success else "failed",
        )


_audit_logger_singleton = None


def get_audit_logger() -> AuditLogger:
    global _audit_logger_singleton
    if _audit_logger_singleton is None:
        _audit_logger_singleton = AuditLogger()
    return _audit_logger_singleton


def audit_log(action: str, resource_type: Optional[str] = None):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_audit_logger()
            start_time = datetime.now()
            
            try:
                result = func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()
                logger.log(
                    action=action,
                    resource_type=resource_type,
                    details={"duration_seconds": duration},
                    status="success",
                )
                return result
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                logger.log(
                    action=action,
                    resource_type=resource_type,
                    details={"duration_seconds": duration, "error": str(e)},
                    status="failed",
                )
                raise
        
        return wrapper
    return decorator


class RateLimiter:
    def __init__(self, max_calls: int, period: int = 60):
        self.max_calls = max_calls
        self.period = period
        self.calls = []
        self.lock = threading.Lock()
    
    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self.lock:
                now = time.time()
                
                self.calls = [t for t in self.calls if now - t < self.period]
                
                if len(self.calls) >= self.max_calls:
                    wait_time = self.period - (now - self.calls[0])
                    time.sleep(wait_time)
                
                self.calls.append(now)
            
            return func(*args, **kwargs)
        
        return wrapper
    
    def acquire(self) -> bool:
        with self.lock:
            now = time.time()
            self.calls = [t for t in self.calls if now - t < self.period]
            
            if len(self.calls) >= self.max_calls:
                return False
            
            self.calls.append(now)
            return True


class ConcurrentTaskProcessor:
    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or Config.MAX_CONCURRENT_TASKS
        self.task_queue: queue.Queue = queue.Queue()
        self.results: Dict = {}
        self.lock = threading.Lock()
        self.workers = []
        self._shutdown = False
    
    def start(self):
        for i in range(self.max_workers):
            t = threading.Thread(target=self._worker, daemon=True, name=f"Worker-{i}")
            t.start()
            self.workers.append(t)
    
    def _worker(self):
        while not self._shutdown:
            try:
                task_id, func, args, kwargs = self.task_queue.get(timeout=1)
            except queue.Empty:
                continue
            
            try:
                result = func(*args, **kwargs)
                with self.lock:
                    self.results[task_id] = {"status": "success", "result": result}
            except Exception as e:
                with self.lock:
                    self.results[task_id] = {"status": "error", "error": str(e)}
            finally:
                self.task_queue.task_done()
    
    def submit(self, task_id: str, func: Callable, *args, **kwargs):
        self.task_queue.put((task_id, func, args, kwargs))
    
    def get_result(self, task_id: str, timeout: int = 30) -> Optional[Dict]:
        start_time = time.time()
        while time.time() - start_time < timeout:
            with self.lock:
                if task_id in self.results:
                    return self.results.pop(task_id)
            time.sleep(0.1)
        return None
    
    def wait_all(self):
        self.task_queue.join()
    
    def shutdown(self):
        self._shutdown = True
        for t in self.workers:
            t.join(timeout=5)


_concurrent_processor_singleton = None


def get_concurrent_processor() -> ConcurrentTaskProcessor:
    global _concurrent_processor_singleton
    if _concurrent_processor_singleton is None:
        _concurrent_processor_singleton = ConcurrentTaskProcessor()
        _concurrent_processor_singleton.start()
    return _concurrent_processor_singleton
