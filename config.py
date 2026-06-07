import os
from datetime import timedelta


class Config:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'data', 'cert_management.db')}"
    )
    
    OCR_ENGINE = os.getenv("OCR_ENGINE", "paddle")
    OCR_LANG = os.getenv("OCR_LANG", "ch")
    
    EXPIRY_WARNING_DAYS = int(os.getenv("EXPIRY_WARNING_DAYS", 90))
    TASK_DEADLINE_DAYS = int(os.getenv("TASK_DEADLINE_DAYS", 30))
    ESCALATION_DAYS = int(os.getenv("ESCALATION_DAYS", 15))
    REMINDER_INTERVAL_DAYS = int(os.getenv("REMINDER_INTERVAL_DAYS", 5))
    
    COMPLIANCE_THRESHOLD = float(os.getenv("COMPLIANCE_THRESHOLD", 0.8))
    CONSECUTIVE_MONTHS_THRESHOLD = int(os.getenv("CONSECUTIVE_MONTHS_THRESHOLD", 2))
    
    UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
    REPORT_DIR = os.path.join(BASE_DIR, "reports")
    LOG_DIR = os.path.join(BASE_DIR, "logs")
    DATA_DIR = os.path.join(BASE_DIR, "data")
    
    MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", 10 * 1024 * 1024))  # 10MB
    
    MAX_CONCURRENT_TASKS = int(os.getenv("MAX_CONCURRENT_TASKS", 10))
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", 100))
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", 60))
    
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.path.join(LOG_DIR, "cert_management.log")
    
    SCHEDULER_TIMEZONE = os.getenv("SCHEDULER_TIMEZONE", "Asia/Shanghai")
    DAILY_CHECK_TIME = os.getenv("DAILY_CHECK_TIME", "02:00")
    MONTHLY_REPORT_DAY = int(os.getenv("MONTHLY_REPORT_DAY", 1))
    MONTHLY_REPORT_TIME = os.getenv("MONTHLY_REPORT_TIME", "03:00")
    
    @classmethod
    def ensure_dirs(cls):
        for dir_path in [cls.UPLOAD_DIR, cls.REPORT_DIR, cls.LOG_DIR, cls.DATA_DIR]:
            os.makedirs(dir_path, exist_ok=True)
