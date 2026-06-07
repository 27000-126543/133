from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from typing import Optional, List
import os

from auth import User, UserRole
from security import get_current_active_user, require_role
from audit_logger import get_audit_logger
from report_generator import get_report_generator
from training_engine import get_training_engine
from query_engine import get_query_engine
from config import Config

router = APIRouter(prefix="", tags=["报告与统计"])
audit_logger = get_audit_logger()
report_generator = get_report_generator()
training_engine = get_training_engine()
query_engine = get_query_engine()


@router.get("/statistics/dashboard")
async def get_dashboard_stats(current_user: User = Depends(get_current_active_user)):
    """获取仪表盘统计数据"""
    cert_stats = query_engine.get_statistics()
    
    from task_manager import get_task_manager
    task_manager = get_task_manager()
    task_stats = task_manager.get_task_statistics()
    
    training_stats = training_engine.get_training_plan_statistics()
    
    from compliance_engine import get_compliance_engine
    compliance_engine = get_compliance_engine()
    
    with get_db_session() as session:
        from models import Department
        departments = session.query(Department).all()
        
        dept_compliance = []
        for dept in departments:
            summary = compliance_engine.get_department_compliance_summary(dept.id)
            dept_compliance.append({
                "department_id": dept.id,
                "department_name": dept.name,
                "compliance_rate": summary.get("compliance_rate", 0) * 100,
                "total_employees": summary.get("total_employees", 0),
                "issues_count": summary.get("issues_count", 0),
            })
    
    expiring_certs = compliance_engine.check_expiring_certificates()
    expired_certs = compliance_engine.check_expired_certificates()
    
    return {
        "certificates": {
            "total": cert_stats["total_certificates"],
            "valid": cert_stats["valid_certificates"],
            "verified": cert_stats["verified_certificates"],
            "unverified": cert_stats["unverified_certificates"],
            "expiring_soon": cert_stats["expiring_soon"],
            "expired": cert_stats["expired"],
            "verification_rate": cert_stats["verification_rate"] * 100,
        },
        "employees": {
            "total": cert_stats["total_employees"],
            "departments": cert_stats["departments"],
        },
        "tasks": task_stats,
        "training": {
            "total_plans": training_stats["total_plans"],
            "in_progress": training_stats["in_progress"],
            "low_compliance_departments": training_stats["low_compliance_departments"],
        },
        "department_compliance": dept_compliance,
        "expiring_certificates": expiring_certs[:10],
        "expired_certificates": expired_certs[:10],
        "timestamp": cert_stats["timestamp"],
    }


@router.get("/reports/monthly")
async def get_monthly_reports(
    month: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """获取月度报告列表"""
    from database import get_db_session
    from models import MonthlyReport
    
    with get_db_session() as session:
        query = session.query(MonthlyReport)
        
        if month:
            query = query.filter(MonthlyReport.report_month == month)
        
        reports = query.order_by(MonthlyReport.report_month.desc()).all()
        
        return {
            "total": len(reports),
            "items": [
                {
                    "id": r.id,
                    "report_month": r.report_month,
                    "department_id": r.department_id,
                    "department_name": r.department.name if r.department else "公司整体",
                    "total_employees": r.total_employees,
                    "certified_employees": r.certified_employees,
                    "compliance_rate": r.compliance_rate * 100,
                    "certification_rate": r.certification_rate * 100,
                    "expiry_rate": r.expiry_rate * 100,
                    "pending_tasks": r.pending_tasks,
                    "completed_tasks": r.completed_tasks,
                    "excel_path": r.excel_path,
                    "pdf_path": r.pdf_path,
                    "created_at": r.created_at.isoformat(),
                }
                for r in reports
            ]
        }


@router.post("/reports/monthly/generate")
async def generate_monthly_report(
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """手动生成月度报告"""
    from scheduler import get_scheduler
    scheduler = get_scheduler()
    
    result = scheduler.monthly_report_generation()
    
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error_message or "报告生成失败")
    
    audit_logger.log_report_generation(
        report_month=result.details.get("report_month", ""),
        excel_path=result.details.get("excel_path", ""),
        pdf_path=result.details.get("pdf_path", ""),
        departments_count=result.details.get("departments_count", 0),
        generated_by=current_user.full_name,
    )
    
    return {
        "success": True,
        "message": "月度报告生成成功",
        "report_month": result.details.get("report_month"),
        "excel_path": result.details.get("excel_path"),
        "pdf_path": result.details.get("pdf_path"),
    }


@router.get("/reports/download/{report_type}/{file_name}")
async def download_report(
    report_type: str,
    file_name: str,
    current_user: User = Depends(get_current_active_user)
):
    """下载报告文件"""
    file_path = os.path.join(Config.REPORT_DIR, file_name)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    
    if report_type == "pdf":
        return FileResponse(
            file_path,
            media_type="application/pdf",
            filename=file_name
        )
    elif report_type == "excel":
        return FileResponse(
            file_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=file_name
        )
    else:
        raise HTTPException(status_code=400, detail="不支持的文件类型")


@router.get("/training/plans")
async def get_training_plans(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """获取培训计划列表"""
    from database import get_db_session
    from models import TrainingPlan
    
    with get_db_session() as session:
        query = session.query(TrainingPlan)
        
        if status:
            query = query.filter(TrainingPlan.status == status)
        
        if current_user.role == UserRole.MANAGER.value and current_user.employee_id:
            from models import Employee
            emp = session.query(Employee).filter(Employee.id == current_user.employee_id).first()
            if emp and emp.department_id:
                query = query.filter(TrainingPlan.department_id == emp.department_id)
        elif current_user.role == UserRole.EMPLOYEE.value:
            pass
        
        plans = query.order_by(TrainingPlan.created_at.desc()).all()
        
        return {
            "total": len(plans),
            "items": [
                {
                    "id": p.id,
                    "plan_code": p.plan_code,
                    "name": p.name,
                    "department_id": p.department_id,
                    "department_name": p.department.name if p.department else None,
                    "start_date": p.start_date.isoformat() if p.start_date else None,
                    "end_date": p.end_date.isoformat() if p.end_date else None,
                    "status": p.status,
                    "reason": p.reason,
                    "course_count": len(p.course_ids) if p.course_ids else 0,
                    "target_count": len(p.target_employees) if p.target_employees else 0,
                    "created_at": p.created_at.isoformat(),
                }
                for p in plans
            ]
        }


@router.get("/training/courses")
async def get_training_courses(current_user: User = Depends(get_current_active_user)):
    """获取培训课程列表"""
    from database import get_db_session
    from models import TrainingCourse
    
    with get_db_session() as session:
        courses = session.query(TrainingCourse).filter(TrainingCourse.is_active == True).all()
        
        return [
            {
                "id": c.id,
                "course_code": c.course_code,
                "name": c.name,
                "description": c.description,
                "category": c.category,
                "duration_hours": c.duration_hours,
                "provider": c.provider,
                "cert_type_id": c.cert_type_id,
                "cert_type_name": c.cert_type.name if c.cert_type else None,
            }
            for c in courses
        ]


@router.get("/training/needs")
async def get_training_needs(current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER]))):
    """检查培训需求"""
    needs = training_engine.check_low_compliance_departments()
    return {"needs": needs}


@router.post("/training/generate-plans")
async def generate_training_plans(
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """自动生成培训计划"""
    plans = training_engine.auto_generate_training_plans()
    
    for plan in plans:
        audit_logger.log_training_plan(
            plan_id=plan.id,
            department_id=plan.department_id,
            plan_code=plan.plan_code,
            plan_name=plan.name,
            generated_by=current_user.full_name,
        )
    
    return {
        "success": True,
        "message": f"已生成 {len(plans)} 个培训计划",
        "plans": [
            {
                "plan_id": p.id,
                "plan_code": p.plan_code,
                "name": p.name,
                "department_name": p.department.name if p.department else None,
            }
            for p in plans
        ]
    }


@router.get("/audit-logs")
async def get_audit_logs(
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """获取审计日志（仅管理员）"""
    logs = query_engine.query_audit_logs(
        user_id=user_id,
        action=action,
    )
    
    if resource_type:
        logs = [l for l in logs if l.get("resource_type") == resource_type]
    
    total = len(logs)
    paginated = logs[skip:skip + limit]
    
    return {"total": total, "items": paginated}
