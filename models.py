from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Text, Boolean, Float, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, date

from database import Base


class Department(Base):
    __tablename__ = "departments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    manager_id = Column(Integer, ForeignKey("employees.id"))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    employees = relationship("Employee", back_populates="department", foreign_keys="Employee.department_id")
    manager = relationship("Employee", foreign_keys=[manager_id], remote_side="Employee.id")


class Employee(Base):
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_no = Column(String(50), unique=True, nullable=False)
    name = Column(String(50), nullable=False)
    gender = Column(String(10))
    phone = Column(String(20))
    email = Column(String(100))
    position = Column(String(100))
    department_id = Column(Integer, ForeignKey("departments.id"))
    hire_date = Column(Date)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    department = relationship("Department", back_populates="employees", foreign_keys=[department_id])
    certificates = relationship("Certificate", back_populates="employee", cascade="all, delete-orphan", foreign_keys="Certificate.employee_id")
    tasks = relationship("Task", back_populates="employee", foreign_keys="Task.employee_id")
    assigned_tasks = relationship("Task", back_populates="assignee", foreign_keys="Task.assignee_id")


class CertificateType(Base):
    __tablename__ = "certificate_types"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    category = Column(String(50))
    description = Column(Text)
    validity_years = Column(Integer)
    is_required = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    
    certificates = relationship("Certificate", back_populates="cert_type")
    position_requirements = relationship("PositionRequirement", back_populates="cert_type")


class Certificate(Base):
    __tablename__ = "certificates"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    cert_type_id = Column(Integer, ForeignKey("certificate_types.id"), nullable=False)
    cert_number = Column(String(100))
    cert_name = Column(String(200), nullable=False)
    issuing_authority = Column(String(200))
    issue_date = Column(Date)
    expiry_date = Column(Date)
    score = Column(Float)
    image_path = Column(String(500))
    ocr_data = Column(JSON)
    status = Column(String(20), default="valid")
    verified = Column(Boolean, default=False)
    verified_by = Column(Integer, ForeignKey("employees.id"))
    verified_at = Column(DateTime)
    verification_notes = Column(Text)
    source = Column(String(50), default="manual")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    employee = relationship("Employee", back_populates="certificates", foreign_keys=[employee_id])
    cert_type = relationship("CertificateType", back_populates="certificates")
    tasks = relationship("Task", back_populates="certificate")
    
    @property
    def is_expired(self):
        if not self.expiry_date:
            return False
        return date.today() > self.expiry_date
    
    @property
    def days_to_expiry(self):
        if not self.expiry_date:
            return None
        return (self.expiry_date - date.today()).days
    
    @property
    def is_valid(self):
        return self.status == "valid" and not self.is_expired


class PositionRequirement(Base):
    __tablename__ = "position_requirements"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    position = Column(String(100), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"))
    cert_type_id = Column(Integer, ForeignKey("certificate_types.id"), nullable=False)
    requirement_level = Column(String(20), default="required")
    minimum_score = Column(Float)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    cert_type = relationship("CertificateType", back_populates="position_requirements")
    department = relationship("Department")


class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    assignee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    certificate_id = Column(Integer, ForeignKey("certificates.id"))
    deadline = Column(Date, nullable=False)
    status = Column(String(20), default="pending")
    priority = Column(String(20), default="medium")
    escalation_level = Column(Integer, default=0)
    last_reminder_at = Column(DateTime)
    reminder_count = Column(Integer, default=0)
    completed_at = Column(DateTime)
    completed_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    employee = relationship("Employee", back_populates="tasks", foreign_keys=[employee_id])
    assignee = relationship("Employee", back_populates="assigned_tasks", foreign_keys=[assignee_id])
    certificate = relationship("Certificate", back_populates="tasks")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.now, index=True)
    user_id = Column(Integer, ForeignKey("employees.id"))
    user_name = Column(String(100))
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50))
    resource_id = Column(Integer)
    details = Column(JSON)
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    status = Column(String(20), default="success")
    
    employee = relationship("Employee")


class MonthlyReport(Base):
    __tablename__ = "monthly_reports"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    report_month = Column(String(7), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"))
    total_employees = Column(Integer, default=0)
    certified_employees = Column(Integer, default=0)
    total_certificates = Column(Integer, default=0)
    valid_certificates = Column(Integer, default=0)
    expiring_soon = Column(Integer, default=0)
    expired = Column(Integer, default=0)
    compliance_rate = Column(Float, default=0.0)
    certification_rate = Column(Float, default=0.0)
    expiry_rate = Column(Float, default=0.0)
    pending_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    report_data = Column(JSON)
    pdf_path = Column(String(500))
    excel_path = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)
    
    department = relationship("Department")


class TrainingCourse(Base):
    __tablename__ = "training_courses"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    course_code = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(50))
    cert_type_id = Column(Integer, ForeignKey("certificate_types.id"))
    duration_hours = Column(Float)
    provider = Column(String(200))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    
    cert_type = relationship("CertificateType")


class TrainingPlan(Base):
    __tablename__ = "training_plans"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_code = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"))
    course_ids = Column(JSON)
    target_employees = Column(JSON)
    start_date = Column(Date)
    end_date = Column(Date)
    status = Column(String(20), default="draft")
    reason = Column(Text)
    created_by = Column(Integer, ForeignKey("employees.id"))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    department = relationship("Department")
    creator = relationship("Employee", foreign_keys=[created_by])


class ImportBatch(Base):
    __tablename__ = "import_batches"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_no = Column(String(50), unique=True, nullable=False)
    file_name = Column(String(200))
    total_records = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    duplicate_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    error_details = Column(JSON)
    status = Column(String(20), default="processing")
    imported_by = Column(Integer, ForeignKey("employees.id"))
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime)
    
    importer = relationship("Employee")
