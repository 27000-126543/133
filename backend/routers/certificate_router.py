from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from typing import List, Optional, Dict, Any
from datetime import date
import os
import uuid

from database import get_db_session
from models import Employee, Department, Certificate, CertificateType
from auth import User, UserRole
from security import get_current_active_user, require_role
from audit_logger import get_audit_logger
from certificate_validator import get_certificate_validator
from ocr_engine import get_ocr_engine
from config import Config
from query_engine import get_query_engine, QueryFilter

router = APIRouter(prefix="/certificates", tags=["证书管理"])
audit_logger = get_audit_logger()
certificate_validator = get_certificate_validator()
ocr_engine = get_ocr_engine()
query_engine = get_query_engine()


@router.get("/")
async def get_certificates(
    employee_id: Optional[int] = None,
    employee_name: Optional[str] = None,
    employee_no: Optional[str] = None,
    cert_type_id: Optional[int] = None,
    status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    only_expiring: bool = False,
    only_expired: bool = False,
    only_unverified: bool = False,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user)
):
    """获取证书列表"""
    if employee_id:
        if current_user.role == UserRole.EMPLOYEE.value and current_user.employee_id != employee_id:
            raise HTTPException(status_code=403, detail="只能查看自己的证书")
    
    result = query_engine.advanced_query(
        employee_name=employee_name,
        employee_no=employee_no,
        cert_type_id=cert_type_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
        only_expiring=only_expiring,
        only_expired=only_expired,
        only_unverified=only_unverified
    )
    
    if employee_id or current_user.role == UserRole.EMPLOYEE.value:
        target_emp_id = employee_id if employee_id else current_user.employee_id
        result = [c for c in result if c.get("employee_id") == target_emp_id]
    
    total = len(result)
    paginated = result[skip:skip + limit]
    
    return {"total": total, "items": paginated}


@router.get("/{cert_id}")
async def get_certificate(cert_id: int, current_user: User = Depends(get_current_active_user)):
    """获取证书详情"""
    with get_db_session() as session:
        cert = session.query(Certificate).filter(Certificate.id == cert_id).first()
        
        if not cert:
            raise HTTPException(status_code=404, detail="证书不存在")
        
        if current_user.role == UserRole.EMPLOYEE.value and current_user.employee_id != cert.employee_id:
            raise HTTPException(status_code=403, detail="只能查看自己的证书")
        
        return {
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
            "verified_at": cert.verified_at.isoformat() if cert.verified_at else None,
            "verification_notes": cert.verification_notes,
            "is_valid": cert.is_valid,
            "is_expired": cert.is_expired,
            "days_to_expiry": cert.days_to_expiry,
            "source": cert.source,
            "created_at": cert.created_at.isoformat(),
        }


@router.post("/upload")
async def upload_certificate(
    file: UploadFile = File(...),
    employee_id: int = Form(...),
    cert_type_id: Optional[int] = Form(None),
    manual_cert_name: Optional[str] = Form(None),
    manual_cert_number: Optional[str] = Form(None),
    manual_issuing_authority: Optional[str] = Form(None),
    manual_issue_date: Optional[str] = Form(None),
    manual_expiry_date: Optional[str] = Form(None),
    manual_score: Optional[float] = Form(None),
    current_user: User = Depends(get_current_active_user)
):
    """上传证书图片"""
    if current_user.role == UserRole.EMPLOYEE.value and current_user.employee_id != employee_id:
        raise HTTPException(status_code=403, detail="只能上传自己的证书")
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="请选择文件")
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
        raise HTTPException(status_code=400, detail="不支持的文件格式")
    
    file_id = uuid.uuid4().hex
    filename = f"{file_id}{ext}"
    file_path = os.path.join(Config.UPLOAD_DIR, filename)
    
    content = await file.read()
    if len(content) > Config.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="文件大小超过限制")
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    manual_data = None
    if any([manual_cert_name, manual_cert_number, manual_issuing_authority, 
            manual_issue_date, manual_expiry_date]):
        from datetime import datetime
        manual_data = {}
        if manual_cert_name:
            manual_data["cert_name"] = manual_cert_name
        if manual_cert_number:
            manual_data["cert_number"] = manual_cert_number
        if manual_issuing_authority:
            manual_data["issuing_authority"] = manual_issuing_authority
        if manual_issue_date:
            manual_data["issue_date"] = datetime.strptime(manual_issue_date, "%Y-%m-%d").date()
        if manual_expiry_date:
            manual_data["expiry_date"] = datetime.strptime(manual_expiry_date, "%Y-%m-%d").date()
        if manual_score is not None:
            manual_data["score"] = manual_score
    
    try:
        result = certificate_validator.verify_new_certificate(
            employee_id=employee_id,
            image_path=file_path,
            cert_type_id=cert_type_id,
            manual_data=manual_data
        )
    except Exception as e:
        os.remove(file_path) if os.path.exists(file_path) else None
        raise HTTPException(status_code=500, detail=f"证书处理失败: {str(e)}")
    
    audit_logger.log_certificate_upload(
        employee_id=employee_id,
        employee_name=current_user.full_name,
        certificate_id=result.certificate_id,
        success=result.success,
        file_name=file.filename,
        file_path=file_path,
        message=result.message,
    )
    
    if result.success:
        return {
            "success": True,
            "certificate_id": result.certificate_id,
            "message": result.message,
            "image_path": file_path,
            "extracted_data": result.updated_fields,
        }
    else:
        return {
            "success": False,
            "message": result.message,
            "issues": result.issues,
            "image_path": file_path,
            "extracted_data": result.updated_fields,
        }


@router.post("/ocr-preview")
async def ocr_preview(file: UploadFile = File(...), current_user: User = Depends(get_current_active_user)):
    """OCR预览（不保存到数据库）"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="请选择文件")
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
        raise HTTPException(status_code=400, detail="不支持的文件格式")
    
    file_id = uuid.uuid4().hex
    filename = f"{file_id}{ext}"
    file_path = os.path.join(Config.UPLOAD_DIR, "preview_" + filename)
    
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        ocr_result, metadata = ocr_engine.process_image(file_path)
        
        return {
            "success": True,
            "cert_name": ocr_result.cert_name,
            "cert_number": ocr_result.cert_number,
            "issuing_authority": ocr_result.issuing_authority,
            "issue_date": ocr_result.issue_date.isoformat() if ocr_result.issue_date else None,
            "expiry_date": ocr_result.expiry_date.isoformat() if ocr_result.expiry_date else None,
            "holder_name": ocr_result.holder_name,
            "score": ocr_result.score,
            "confidence": ocr_result.confidence,
            "raw_text": ocr_result.raw_text[:500] + "..." if len(ocr_result.raw_text) > 500 else ocr_result.raw_text,
        }
    finally:
        os.remove(file_path) if os.path.exists(file_path) else None


@router.post("/{cert_id}/verify")
async def verify_certificate(
    cert_id: int,
    verified: bool,
    notes: str = "",
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER]))
):
    """审核证书（管理员/经理）"""
    result = certificate_validator.manual_verify_certificate(
        certificate_id=cert_id,
        verified=verified,
        verifier_id=current_user.id,
        notes=notes
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    
    audit_logger.log_certificate_verification(
        certificate_id=cert_id,
        verifier_id=current_user.id,
        verifier_name=current_user.full_name,
        verified=verified,
        notes=notes,
    )
    
    return {
        "success": True,
        "message": result.message,
        "certificate_id": cert_id,
    }


@router.get("/image/{cert_id}")
async def get_certificate_image(cert_id: int, current_user: User = Depends(get_current_active_user)):
    """获取证书图片"""
    with get_db_session() as session:
        cert = session.query(Certificate).filter(Certificate.id == cert_id).first()
        
        if not cert or not cert.image_path or not os.path.exists(cert.image_path):
            raise HTTPException(status_code=404, detail="证书图片不存在")
        
        if current_user.role == UserRole.EMPLOYEE.value and current_user.employee_id != cert.employee_id:
            raise HTTPException(status_code=403, detail="只能查看自己的证书")
        
        return FileResponse(cert.image_path)


@router.get("/export")
async def export_certificates(
    format: str = "excel",
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER]))
):
    """导出证书数据"""
    result = query_engine.export_certificates()
    
    if format == "csv":
        return FileResponse(
            result["csv_path"],
            media_type="text/csv",
            filename=os.path.basename(result["csv_path"])
        )
    else:
        return FileResponse(
            result["excel_path"],
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=os.path.basename(result["excel_path"])
        )


@router.get("/types")
async def get_certificate_types(current_user: User = Depends(get_current_active_user)):
    """获取证书类型列表"""
    with get_db_session() as session:
        types = session.query(CertificateType).all()
        return [
            {
                "id": t.id,
                "code": t.code,
                "name": t.name,
                "category": t.category,
                "description": t.description,
                "validity_years": t.validity_years,
                "is_required": t.is_required,
            }
            for t in types
        ]
