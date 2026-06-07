from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel

from database import get_db_session
from models import Employee, Department
from auth import User, UserRole, UserCreate
from security import get_current_active_user, require_role, register_user, get_password_hash
from audit_logger import get_audit_logger
from compliance_engine import get_compliance_engine

router = APIRouter(prefix="/employees", tags=["员工管理"])
audit_logger = get_audit_logger()
compliance_engine = get_compliance_engine()


class EmployeeCreate(BaseModel):
    employee_no: str
    name: str
    gender: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    position: Optional[str] = None
    department_id: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    position: Optional[str] = None
    department_id: Optional[int] = None
    is_active: Optional[bool] = None


@router.get("/")
async def get_employees(
    department_id: Optional[int] = None,
    is_active: bool = True,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user)
):
    """获取员工列表"""
    with get_db_session() as session:
        query = session.query(Employee).filter(Employee.is_active == is_active)
        
        if department_id:
            query = query.filter(Employee.department_id == department_id)
        
        if current_user.role == UserRole.MANAGER.value and current_user.employee_id:
            emp = session.query(Employee).filter(Employee.id == current_user.employee_id).first()
            if emp and emp.department_id and emp.department.manager_id != current_user.employee_id:
                query = query.filter(Employee.id == current_user.employee_id)
        
        total = query.count()
        employees = query.offset(skip).limit(limit).all()
        
        return {
            "total": total,
            "items": [
                {
                    "id": e.id,
                    "employee_no": e.employee_no,
                    "name": e.name,
                    "gender": e.gender,
                    "phone": e.phone,
                    "email": e.email,
                    "position": e.position,
                    "department_id": e.department_id,
                    "department_name": e.department.name if e.department else None,
                    "hire_date": e.hire_date.isoformat() if e.hire_date else None,
                    "is_active": e.is_active,
                    "certificate_count": len(e.certificates),
                    "created_at": e.created_at.isoformat(),
                }
                for e in employees
            ]
        }


@router.get("/{emp_id}")
async def get_employee(emp_id: int, current_user: User = Depends(get_current_active_user)):
    """获取员工详情"""
    with get_db_session() as session:
        emp = session.query(Employee).filter(Employee.id == emp_id).first()
        
        if not emp:
            raise HTTPException(status_code=404, detail="员工不存在")
        
        if current_user.role == UserRole.EMPLOYEE.value and current_user.employee_id != emp_id:
            raise HTTPException(status_code=403, detail="无权查看此员工信息")
        
        compliance_report = compliance_engine.check_employee_compliance(emp)
        
        return {
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
            "compliance_rate": compliance_report.compliance_rate,
            "total_requirements": compliance_report.total_requirements,
            "compliant_count": compliance_report.compliant_count,
            "issues": [
                {
                    "cert_type_name": issue.cert_type_name,
                    "status": issue.status.value,
                    "issue_description": issue.issue_description,
                    "days_to_expiry": issue.days_to_expiry,
                }
                for issue in compliance_report.issues
            ],
            "certificates": [
                {
                    "id": c.id,
                    "cert_name": c.cert_name,
                    "cert_type_name": c.cert_type.name if c.cert_type else None,
                    "status": c.status,
                    "verified": c.verified,
                    "expiry_date": c.expiry_date.isoformat() if c.expiry_date else None,
                    "is_valid": c.is_valid,
                }
                for c in emp.certificates
            ],
            "created_at": emp.created_at.isoformat(),
        }


@router.post("/", status_code=201)
async def create_employee(
    emp_data: EmployeeCreate,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """创建新员工（仅管理员）"""
    with get_db_session() as session:
        existing = session.query(Employee).filter(Employee.employee_no == emp_data.employee_no).first()
        if existing:
            raise HTTPException(status_code=400, detail="员工工号已存在")
        
        emp = Employee(
            employee_no=emp_data.employee_no,
            name=emp_data.name,
            gender=emp_data.gender,
            phone=emp_data.phone,
            email=emp_data.email,
            position=emp_data.position,
            department_id=emp_data.department_id,
            is_active=True,
        )
        session.add(emp)
        session.flush()
        emp_id = emp.id
        
        if emp_data.username and emp_data.password:
            try:
                user_data = UserCreate(
                    username=emp_data.username,
                    email=emp_data.email or f"{emp_data.username}@company.com",
                    password=emp_data.password,
                    full_name=emp_data.name,
                    role=UserRole.EMPLOYEE,
                    employee_id=emp_id,
                )
                register_user(user_data)
            except Exception as e:
                session.rollback()
                raise HTTPException(status_code=400, detail=f"创建用户失败: {str(e)}")
        
        audit_logger.log(
            action="employee_create",
            user_id=current_user.id,
            user_name=current_user.full_name,
            resource_type="employee",
            resource_id=emp_id,
            details={"employee_no": emp_data.employee_no, "name": emp_data.name},
        )
        
        return {"message": "员工创建成功", "employee_id": emp_id}


@router.put("/{emp_id}")
async def update_employee(
    emp_id: int,
    emp_data: EmployeeUpdate,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """更新员工信息（仅管理员）"""
    with get_db_session() as session:
        emp = session.query(Employee).filter(Employee.id == emp_id).first()
        
        if not emp:
            raise HTTPException(status_code=404, detail="员工不存在")
        
        update_data = emp_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(emp, key, value)
        
        audit_logger.log(
            action="employee_update",
            user_id=current_user.id,
            user_name=current_user.full_name,
            resource_type="employee",
            resource_id=emp_id,
            details=update_data,
        )
        
        return {"message": "员工信息更新成功"}


@router.get("/departments")
async def get_departments(current_user: User = Depends(get_current_active_user)):
    """获取部门列表"""
    with get_db_session() as session:
        depts = session.query(Department).all()
        
        result = []
        for dept in depts:
            compliance_summary = compliance_engine.get_department_compliance_summary(dept.id)
            result.append({
                "id": dept.id,
                "name": dept.name,
                "manager_id": dept.manager_id,
                "manager_name": dept.manager.name if dept.manager else None,
                "employee_count": len([e for e in dept.employees if e.is_active]),
                "compliance_rate": compliance_summary.get("compliance_rate", 0),
                "created_at": dept.created_at.isoformat(),
            })
        
        return result


@router.get("/{emp_id}/compliance")
async def get_employee_compliance(emp_id: int, current_user: User = Depends(get_current_active_user)):
    """获取员工合规报告"""
    with get_db_session() as session:
        emp = session.query(Employee).filter(Employee.id == emp_id).first()
        
        if not emp:
            raise HTTPException(status_code=404, detail="员工不存在")
        
        if current_user.role == UserRole.EMPLOYEE.value and current_user.employee_id != emp_id:
            raise HTTPException(status_code=403, detail="无权查看此员工信息")
    
    report = compliance_engine.check_employee_compliance(emp)
    
    return {
        "employee_id": emp_id,
        "employee_name": emp.name,
        "employee_no": emp.employee_no,
        "total_requirements": report.total_requirements,
        "compliant_count": report.compliant_count,
        "compliance_rate": report.compliance_rate,
        "issues": [
            {
                "cert_type_name": issue.cert_type_name,
                "status": issue.status.value,
                "issue_description": issue.issue_description,
                "days_to_expiry": issue.days_to_expiry,
                "expiry_date": issue.expiry_date.isoformat() if issue.expiry_date else None,
            }
            for issue in report.issues
        ],
    }
