import os
import json
from datetime import datetime, date
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
import pandas as pd

from sqlalchemy import and_, or_

from database import get_db_session
from models import Employee, Certificate, CertificateType, Department, Task, AuditLog
from config import Config


@dataclass
class QueryFilter:
    field: str
    operator: str
    value: Any


class QueryEngine:
    ALLOWED_FIELDS = {
        "employee": ["employee_no", "name", "department_id", "position", "is_active"],
        "certificate": ["employee_id", "cert_type_id", "status", "verified", "issue_date", "expiry_date", "created_at"],
        "task": ["employee_id", "assignee_id", "task_type", "status", "priority", "deadline", "created_at"],
        "audit_log": ["user_id", "action", "resource_type", "timestamp", "status"],
    }
    
    ALLOWED_OPERATORS = ["eq", "ne", "gt", "gte", "lt", "lte", "in", "nin", "like", "between"]
    
    def __init__(self):
        self.export_dir = Config.REPORT_DIR
    
    def _build_query(self, model, filters: List[QueryFilter]):
        with get_db_session() as session:
            query = session.query(model)
            
            for f in filters:
                if f.field not in self.ALLOWED_FIELDS.get(model.__tablename__, []):
                    continue
                
                column = getattr(model, f.field)
                
                if f.operator == "eq":
                    query = query.filter(column == f.value)
                elif f.operator == "ne":
                    query = query.filter(column != f.value)
                elif f.operator == "gt":
                    query = query.filter(column > f.value)
                elif f.operator == "gte":
                    query = query.filter(column >= f.value)
                elif f.operator == "lt":
                    query = query.filter(column < f.value)
                elif f.operator == "lte":
                    query = query.filter(column <= f.value)
                elif f.operator == "in":
                    query = query.filter(column.in_(f.value))
                elif f.operator == "nin":
                    query = query.filter(column.notin_(f.value))
                elif f.operator == "like":
                    query = query.filter(column.like(f"%{f.value}%"))
                elif f.operator == "between":
                    if isinstance(f.value, (list, tuple)) and len(f.value) == 2:
                        query = query.filter(column.between(f.value[0], f.value[1]))
            
            return query
    
    def query_employees(self, filters: Optional[List[QueryFilter]] = None, 
                       include_certificates: bool = False) -> List[Dict]:
        filters = filters or []
        
        with get_db_session() as session:
            query = self._build_query(Employee, filters)
            employees = query.all()
            
            result = []
            for emp in employees:
                emp_dict = {
                    "id": emp.id,
                    "employee_no": emp.employee_no,
                    "name": emp.name,
                    "gender": emp.gender,
                    "phone": emp.phone,
                    "email": emp.email,
                    "position": emp.position,
                    "department_id": emp.department_id,
                    "department_name": emp.department.name if emp.department else None,
                    "hire_date": emp.hire_date.isoformat() if emp.hire_date else None,
                    "is_active": emp.is_active,
                    "created_at": emp.created_at.isoformat(),
                }
                
                if include_certificates:
                    emp_dict["certificates"] = [
                        {
                            "id": c.id,
                            "cert_name": c.cert_name,
                            "cert_type": c.cert_type.name if c.cert_type else None,
                            "cert_number": c.cert_number,
                            "status": c.status,
                            "verified": c.verified,
                            "expiry_date": c.expiry_date.isoformat() if c.expiry_date else None,
                            "is_valid": c.is_valid,
                            "days_to_expiry": c.days_to_expiry,
                        }
                        for c in emp.certificates
                    ]
                
                result.append(emp_dict)
            
            return result
    
    def query_certificates(self, filters: Optional[List[QueryFilter]] = None,
                          start_date: Optional[date] = None,
                          end_date: Optional[date] = None,
                          employee_ids: Optional[List[int]] = None,
                          cert_type_ids: Optional[List[int]] = None,
                          status: Optional[str] = None) -> List[Dict]:
        filters = filters or []
        
        if employee_ids:
            filters.append(QueryFilter(field="employee_id", operator="in", value=employee_ids))
        if cert_type_ids:
            filters.append(QueryFilter(field="cert_type_id", operator="in", value=cert_type_ids))
        if status:
            filters.append(QueryFilter(field="status", operator="eq", value=status))
        if start_date and end_date:
            filters.append(QueryFilter(field="issue_date", operator="between", value=[start_date, end_date]))
        
        with get_db_session() as session:
            query = self._build_query(Certificate, filters)
            certificates = query.order_by(Certificate.created_at.desc()).all()
            
            result = []
            for cert in certificates:
                result.append({
                    "id": cert.id,
                    "employee_id": cert.employee_id,
                    "employee_name": cert.employee.name if cert.employee else None,
                    "employee_no": cert.employee.employee_no if cert.employee else None,
                    "department_name": cert.employee.department.name if cert.employee and cert.employee.department else None,
                    "cert_type_id": cert.cert_type_id,
                    "cert_type_name": cert.cert_type.name if cert.cert_type else None,
                    "cert_name": cert.cert_name,
                    "cert_number": cert.cert_number,
                    "issuing_authority": cert.issuing_authority,
                    "issue_date": cert.issue_date.isoformat() if cert.issue_date else None,
                    "expiry_date": cert.expiry_date.isoformat() if cert.expiry_date else None,
                    "score": cert.score,
                    "status": cert.status,
                    "verified": cert.verified,
                    "source": cert.source,
                    "is_valid": cert.is_valid,
                    "is_expired": cert.is_expired,
                    "days_to_expiry": cert.days_to_expiry,
                    "created_at": cert.created_at.isoformat(),
                })
            
            return result
    
    def query_tasks(self, filters: Optional[List[QueryFilter]] = None) -> List[Dict]:
        filters = filters or []
        
        with get_db_session() as session:
            query = self._build_query(Task, filters)
            tasks = query.order_by(Task.created_at.desc()).all()
            
            result = []
            for task in tasks:
                result.append({
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
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                    "created_at": task.created_at.isoformat(),
                })
            
            return result
    
    def query_audit_logs(self, filters: Optional[List[QueryFilter]] = None,
                        start_date: Optional[date] = None,
                        end_date: Optional[date] = None,
                        user_id: Optional[int] = None,
                        action: Optional[str] = None) -> List[Dict]:
        filters = filters or []
        
        if start_date and end_date:
            filters.append(QueryFilter(field="timestamp", operator="between", 
                                      value=[datetime.combine(start_date, datetime.min.time()),
                                             datetime.combine(end_date, datetime.max.time())]))
        if user_id:
            filters.append(QueryFilter(field="user_id", operator="eq", value=user_id))
        if action:
            filters.append(QueryFilter(field="action", operator="like", value=action))
        
        with get_db_session() as session:
            query = self._build_query(AuditLog, filters)
            logs = query.order_by(AuditLog.timestamp.desc()).all()
            
            result = []
            for log in logs:
                result.append({
                    "id": log.id,
                    "timestamp": log.timestamp.isoformat(),
                    "user_id": log.user_id,
                    "user_name": log.user_name,
                    "action": log.action,
                    "resource_type": log.resource_type,
                    "resource_id": log.resource_id,
                    "details": log.details,
                    "ip_address": log.ip_address,
                    "status": log.status,
                })
            
            return result
    
    def advanced_query(self,
                      employee_name: Optional[str] = None,
                      employee_no: Optional[str] = None,
                      department_id: Optional[int] = None,
                      cert_type_id: Optional[int] = None,
                      cert_name: Optional[str] = None,
                      status: Optional[str] = None,
                      start_date: Optional[date] = None,
                      end_date: Optional[date] = None,
                      only_expiring: bool = False,
                      only_expired: bool = False,
                      only_unverified: bool = False) -> List[Dict]:
        filters = []
        
        if employee_name or employee_no or department_id:
            with get_db_session() as session:
                emp_query = session.query(Employee)
                if employee_name:
                    emp_query = emp_query.filter(Employee.name.like(f"%{employee_name}%"))
                if employee_no:
                    emp_query = emp_query.filter(Employee.employee_no.like(f"%{employee_no}%"))
                if department_id:
                    emp_query = emp_query.filter(Employee.department_id == department_id)
                
                employee_ids = [e.id for e in emp_query.all()]
                if employee_ids:
                    filters.append(QueryFilter(field="employee_id", operator="in", value=employee_ids))
                else:
                    return []
        
        if cert_type_id:
            filters.append(QueryFilter(field="cert_type_id", operator="eq", value=cert_type_id))
        
        if status:
            filters.append(QueryFilter(field="status", operator="eq", value=status))
        
        if start_date and end_date:
            filters.append(QueryFilter(field="issue_date", operator="between", value=[start_date, end_date]))
        
        certificates = self.query_certificates(filters=filters)
        
        if only_expiring:
            certificates = [c for c in certificates if c["days_to_expiry"] is not None 
                           and 0 < c["days_to_expiry"] <= Config.EXPIRY_WARNING_DAYS]
        elif only_expired:
            certificates = [c for c in certificates if c.get("is_expired", False)]
        
        if only_unverified:
            certificates = [c for c in certificates if not c.get("verified", False)]
        
        if cert_name:
            certificates = [c for c in certificates if cert_name.lower() in (c.get("cert_name") or "").lower()]
        
        return certificates
    
    def export_to_excel(self, data: List[Dict], file_name: str, sheet_name: str = "Sheet1") -> str:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        safe_name = file_name.replace(" ", "_").replace("/", "_")
        output_path = os.path.join(self.export_dir, f"{safe_name}_{timestamp}.xlsx")
        
        df = pd.DataFrame(data)
        
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name=sheet_name)
            
            workbook = writer.book
            worksheet = writer.sheets[sheet_name]
            
            for column in worksheet.columns:
                max_length = 0
                column = [cell for cell in column]
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
        
        return output_path
    
    def export_to_csv(self, data: List[Dict], file_name: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        safe_name = file_name.replace(" ", "_").replace("/", "_")
        output_path = os.path.join(self.export_dir, f"{safe_name}_{timestamp}.csv")
        
        df = pd.DataFrame(data)
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        
        return output_path
    
    def export_certificates(self, **query_params) -> Dict[str, str]:
        certificates = self.advanced_query(**query_params)
        
        return {
            "total": len(certificates),
            "excel_path": self.export_to_excel(certificates, "certificates_export", "证书数据"),
            "csv_path": self.export_to_csv(certificates, "certificates_export"),
        }
    
    def get_statistics(self) -> Dict:
        with get_db_session() as session:
            total_employees = session.query(Employee).filter(Employee.is_active == True).count()
            total_certificates = session.query(Certificate).count()
            valid_certificates = session.query(Certificate).filter(Certificate.status == "valid").count()
            verified_certificates = session.query(Certificate).filter(Certificate.verified == True).count()
            unverified_certificates = total_certificates - verified_certificates
            
            today = date.today()
            cutoff = today + pd.Timedelta(days=Config.EXPIRY_WARNING_DAYS)
            
            expiring_soon = session.query(Certificate).filter(
                Certificate.status == "valid",
                Certificate.expiry_date.isnot(None),
                Certificate.expiry_date > today,
                Certificate.expiry_date <= cutoff
            ).count()
            
            expired = session.query(Certificate).filter(
                Certificate.expiry_date.isnot(None),
                Certificate.expiry_date < today
            ).count()
            
            cert_types = session.query(CertificateType).count()
            departments = session.query(Department).count()
        
        return {
            "total_employees": total_employees,
            "total_certificates": total_certificates,
            "valid_certificates": valid_certificates,
            "verified_certificates": verified_certificates,
            "unverified_certificates": unverified_certificates,
            "expiring_soon": expiring_soon,
            "expired": expired,
            "certificate_types": cert_types,
            "departments": departments,
            "verification_rate": verified_certificates / total_certificates if total_certificates > 0 else 0,
        }


_query_engine_singleton = None


def get_query_engine() -> QueryEngine:
    global _query_engine_singleton
    if _query_engine_singleton is None:
        _query_engine_singleton = QueryEngine()
    return _query_engine_singleton
