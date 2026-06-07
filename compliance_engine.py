from datetime import date, datetime, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import and_, or_

from database import get_db_session
from models import Employee, Certificate, PositionRequirement, CertificateType, Department, Task
from config import Config


class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    MISSING = "missing"
    EXPIRING_SOON = "expiring_soon"
    EXPIRED = "expired"
    INSUFFICIENT_SCORE = "insufficient_score"
    UNVERIFIED = "unverified"


@dataclass
class ComplianceIssue:
    employee_id: int
    employee_name: str
    employee_no: str
    department_id: int
    department_name: str
    position: str
    cert_type_id: int
    cert_type_name: str
    requirement_level: str
    status: ComplianceStatus
    certificate_id: Optional[int] = None
    expiry_date: Optional[date] = None
    days_to_expiry: Optional[int] = None
    current_score: Optional[float] = None
    required_score: Optional[float] = None
    issue_description: str = ""


@dataclass
class EmployeeComplianceReport:
    employee_id: int
    employee_name: str
    employee_no: str
    department_id: int
    department_name: str
    position: str
    total_requirements: int = 0
    compliant_count: int = 0
    issues: List[ComplianceIssue] = None
    
    @property
    def compliance_rate(self) -> float:
        if self.total_requirements == 0:
            return 1.0
        return self.compliant_count / self.total_requirements


class ComplianceEngine:
    def __init__(self):
        self.expiry_warning_days = Config.EXPIRY_WARNING_DAYS
    
    def get_position_requirements(self, position: str, department_id: Optional[int] = None) -> List[PositionRequirement]:
        with get_db_session() as session:
            query = session.query(PositionRequirement).filter(
                PositionRequirement.position == position
            )
            
            if department_id is not None:
                query = query.filter(
                    or_(
                        PositionRequirement.department_id == department_id,
                        PositionRequirement.department_id.is_(None)
                    )
                )
            else:
                query = query.filter(PositionRequirement.department_id.is_(None))
            
            return query.all()
    
    def get_employee_certificates(self, employee_id: int) -> Dict[int, Certificate]:
        with get_db_session() as session:
            certificates = session.query(Certificate).filter(
                Certificate.employee_id == employee_id,
                Certificate.status == "valid"
            ).all()
            
            return {cert.cert_type_id: cert for cert in certificates}
    
    def check_employee_compliance(self, employee: Employee) -> EmployeeComplianceReport:
        report = EmployeeComplianceReport(
            employee_id=employee.id,
            employee_name=employee.name,
            employee_no=employee.employee_no,
            department_id=employee.department_id or 0,
            department_name=employee.department.name if employee.department else "Unknown",
            position=employee.position or "",
            issues=[]
        )
        
        if not employee.position:
            return report
        
        requirements = self.get_position_requirements(employee.position, employee.department_id)
        certificates = self.get_employee_certificates(employee.id)
        
        report.total_requirements = len(requirements)
        
        for req in requirements:
            cert_type = req.cert_type
            cert = certificates.get(req.cert_type_id)
            
            if not cert:
                if req.requirement_level == "required":
                    issue = ComplianceIssue(
                        employee_id=employee.id,
                        employee_name=employee.name,
                        employee_no=employee.employee_no,
                        department_id=employee.department_id or 0,
                        department_name=employee.department.name if employee.department else "Unknown",
                        position=employee.position,
                        cert_type_id=req.cert_type_id,
                        cert_type_name=cert_type.name,
                        requirement_level=req.requirement_level,
                        status=ComplianceStatus.MISSING,
                        issue_description=f"缺少必需证书：{cert_type.name}"
                    )
                    report.issues.append(issue)
                else:
                    report.compliant_count += 1
                continue
            
            if not cert.verified:
                issue = ComplianceIssue(
                    employee_id=employee.id,
                    employee_name=employee.name,
                    employee_no=employee.employee_no,
                    department_id=employee.department_id or 0,
                    department_name=employee.department.name if employee.department else "Unknown",
                    position=employee.position,
                    cert_type_id=req.cert_type_id,
                    cert_type_name=cert_type.name,
                    requirement_level=req.requirement_level,
                    status=ComplianceStatus.UNVERIFIED,
                    certificate_id=cert.id,
                    issue_description=f"证书未验证：{cert_type.name}"
                )
                report.issues.append(issue)
                continue
            
            if cert.is_expired:
                issue = ComplianceIssue(
                    employee_id=employee.id,
                    employee_name=employee.name,
                    employee_no=employee.employee_no,
                    department_id=employee.department_id or 0,
                    department_name=employee.department.name if employee.department else "Unknown",
                    position=employee.position,
                    cert_type_id=req.cert_type_id,
                    cert_type_name=cert_type.name,
                    requirement_level=req.requirement_level,
                    status=ComplianceStatus.EXPIRED,
                    certificate_id=cert.id,
                    expiry_date=cert.expiry_date,
                    days_to_expiry=cert.days_to_expiry,
                    issue_description=f"证书已过期：{cert_type.name}（过期时间：{cert.expiry_date}）"
                )
                report.issues.append(issue)
                continue
            
            if cert.days_to_expiry is not None and cert.days_to_expiry <= self.expiry_warning_days:
                issue = ComplianceIssue(
                    employee_id=employee.id,
                    employee_name=employee.name,
                    employee_no=employee.employee_no,
                    department_id=employee.department_id or 0,
                    department_name=employee.department.name if employee.department else "Unknown",
                    position=employee.position,
                    cert_type_id=req.cert_type_id,
                    cert_type_name=cert_type.name,
                    requirement_level=req.requirement_level,
                    status=ComplianceStatus.EXPIRING_SOON,
                    certificate_id=cert.id,
                    expiry_date=cert.expiry_date,
                    days_to_expiry=cert.days_to_expiry,
                    issue_description=f"证书即将到期：{cert_type.name}（剩余{cert.days_to_expiry}天，到期时间：{cert.expiry_date}）"
                )
                report.issues.append(issue)
                continue
            
            if req.minimum_score is not None and cert.score is not None:
                if cert.score < req.minimum_score:
                    issue = ComplianceIssue(
                        employee_id=employee.id,
                        employee_name=employee.name,
                        employee_no=employee.employee_no,
                        department_id=employee.department_id or 0,
                        department_name=employee.department.name if employee.department else "Unknown",
                        position=employee.position,
                        cert_type_id=req.cert_type_id,
                        cert_type_name=cert_type.name,
                        requirement_level=req.requirement_level,
                        status=ComplianceStatus.INSUFFICIENT_SCORE,
                        certificate_id=cert.id,
                        current_score=cert.score,
                        required_score=req.minimum_score,
                        issue_description=f"证书成绩不达标：{cert_type.name}（当前{cert.score}分，要求{req.minimum_score}分）"
                    )
                    report.issues.append(issue)
                    continue
            
            report.compliant_count += 1
        
        return report
    
    def check_all_employees_compliance(self, department_id: Optional[int] = None) -> List[EmployeeComplianceReport]:
        with get_db_session() as session:
            query = session.query(Employee).filter(Employee.is_active == True)
            
            if department_id is not None:
                query = query.filter(Employee.department_id == department_id)
            
            employees = query.all()
        
        reports = []
        for employee in employees:
            report = self.check_employee_compliance(employee)
            reports.append(report)
        
        return reports
    
    def get_department_compliance_summary(self, department_id: int) -> Dict:
        reports = self.check_all_employees_compliance(department_id)
        
        total_employees = len(reports)
        if total_employees == 0:
            return {
                "department_id": department_id,
                "total_employees": 0,
                "compliant_employees": 0,
                "compliance_rate": 1.0,
                "total_requirements": 0,
                "compliant_requirements": 0,
                "requirement_compliance_rate": 1.0,
                "issues_count": 0,
                "issues_by_type": {},
            }
        
        fully_compliant = sum(1 for r in reports if r.compliance_rate == 1.0)
        total_requirements = sum(r.total_requirements for r in reports)
        compliant_requirements = sum(r.compliant_count for r in reports)
        
        issues_by_type = {}
        total_issues = 0
        for report in reports:
            for issue in report.issues:
                status_value = issue.status.value
                issues_by_type[status_value] = issues_by_type.get(status_value, 0) + 1
                total_issues += 1
        
        return {
            "department_id": department_id,
            "total_employees": total_employees,
            "compliant_employees": fully_compliant,
            "compliance_rate": fully_compliant / total_employees,
            "total_requirements": total_requirements,
            "compliant_requirements": compliant_requirements,
            "requirement_compliance_rate": compliant_requirements / total_requirements if total_requirements > 0 else 1.0,
            "issues_count": total_issues,
            "issues_by_type": issues_by_type,
        }
    
    def check_expiring_certificates(self, days: Optional[int] = None) -> List[Dict]:
        if days is None:
            days = self.expiry_warning_days
        
        today = date.today()
        cutoff_date = today + timedelta(days=days)
        
        with get_db_session() as session:
            certificates = session.query(Certificate).join(Employee).filter(
                Employee.is_active == True,
                Certificate.status == "valid",
                Certificate.verified == True,
                Certificate.expiry_date.isnot(None),
                Certificate.expiry_date >= today,
                Certificate.expiry_date <= cutoff_date
            ).all()
            
            result = []
            for cert in certificates:
                days_left = (cert.expiry_date - today).days
                result.append({
                    "certificate_id": cert.id,
                    "employee_id": cert.employee_id,
                    "employee_name": cert.employee.name,
                    "employee_no": cert.employee.employee_no,
                    "department_id": cert.employee.department_id,
                    "department_name": cert.employee.department.name if cert.employee.department else "",
                    "cert_name": cert.cert_name,
                    "cert_type_name": cert.cert_type.name if cert.cert_type else "",
                    "expiry_date": cert.expiry_date,
                    "days_to_expiry": days_left,
                    "cert_number": cert.cert_number,
                })
            
            return result
    
    def check_expired_certificates(self) -> List[Dict]:
        today = date.today()
        
        with get_db_session() as session:
            certificates = session.query(Certificate).join(Employee).filter(
                Employee.is_active == True,
                Certificate.status == "valid",
                Certificate.expiry_date.isnot(None),
                Certificate.expiry_date < today
            ).all()
            
            result = []
            for cert in certificates:
                days_expired = (today - cert.expiry_date).days
                result.append({
                    "certificate_id": cert.id,
                    "employee_id": cert.employee_id,
                    "employee_name": cert.employee.name,
                    "employee_no": cert.employee.employee_no,
                    "department_id": cert.employee.department_id,
                    "department_name": cert.employee.department.name if cert.employee.department else "",
                    "cert_name": cert.cert_name,
                    "cert_type_name": cert.cert_type.name if cert.cert_type else "",
                    "expiry_date": cert.expiry_date,
                    "days_expired": days_expired,
                    "cert_number": cert.cert_number,
                })
            
            return result


_compliance_engine_singleton = None


def get_compliance_engine() -> ComplianceEngine:
    global _compliance_engine_singleton
    if _compliance_engine_singleton is None:
        _compliance_engine_singleton = ComplianceEngine()
    return _compliance_engine_singleton
