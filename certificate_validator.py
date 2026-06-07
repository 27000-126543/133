import os
import re
from datetime import datetime, date
from typing import Optional, Dict, Tuple, List
from dataclasses import dataclass

from database import get_db_session
from models import Certificate, Employee, Task, CertificateType
from ocr_engine import get_ocr_engine, OCRResult
from task_manager import TaskStatus
from config import Config


@dataclass
class VerificationResult:
    success: bool
    certificate_id: Optional[int] = None
    message: str = ""
    issues: List[str] = None
    updated_fields: Dict = None


class CertificateValidator:
    def __init__(self):
        self.ocr_engine = get_ocr_engine()
        self.min_confidence = 0.6
    
    def _validate_cert_number(self, cert_number: str, cert_type_id: int) -> Tuple[bool, str]:
        if not cert_number:
            return False, "证书编号不能为空"
        
        patterns = {
            "JZS": r'^JZS\d{4}\d{5,6}$',
            "建安": r'^[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领]建安[A,B,C]\d{8}$',
            "GCS": r'^GCS\d{4}\d{5,6}$',
            "KJ": r'^KJ\d{4}\d{5,6}$',
            "PMP": r'^PMP-\d{4}-\d{6}$',
        }
        
        for prefix, pattern in patterns.items():
            if cert_number.startswith(prefix) or prefix in cert_number:
                if not re.match(pattern, cert_number):
                    return False, f"证书编号格式不正确，{prefix}证书编号格式应为：{pattern}"
                break
        
        with get_db_session() as session:
            existing = session.query(Certificate).filter(
                Certificate.cert_number == cert_number,
                Certificate.cert_type_id == cert_type_id,
                Certificate.status == "valid"
            ).first()
            
            if existing:
                return False, f"证书编号{cert_number}已存在，持有人：{existing.employee.name}"
        
        return True, ""
    
    def _validate_dates(self, issue_date: Optional[date], expiry_date: Optional[date]) -> Tuple[bool, str]:
        if issue_date and expiry_date:
            if issue_date >= expiry_date:
                return False, "签发日期必须早于有效期截止日期"
        
        if issue_date and issue_date > date.today():
            return False, "签发日期不能晚于当前日期"
        
        if expiry_date and expiry_date < date.today():
            return False, "证书已过期"
        
        return True, ""
    
    def _validate_issuing_authority(self, authority: str, cert_type_id: int) -> Tuple[bool, str]:
        if not authority:
            return False, "颁发机构不能为空"
        
        valid_authorities = {
            "注册建造师": ["中华人民共和国住房和城乡建设部", "住房和城乡建设部"],
            "安全生产": ["住房和城乡建设委员会", "应急管理厅", "安全生产监督管理局"],
            "工程师": ["人力资源和社会保障局", "人事考试中心", "专业技术资格评审委员会"],
            "会计": ["财政部", "人力资源社会保障部"],
            "PMP": ["Project Management Institute", "PMI"],
        }
        
        with get_db_session() as session:
            cert_type = session.query(CertificateType).filter(CertificateType.id == cert_type_id).first()
            if cert_type:
                for category, authorities in valid_authorities.items():
                    if category in cert_type.name:
                        for valid_auth in authorities:
                            if valid_auth in authority:
                                return True, ""
                        return False, f"{cert_type.name}的颁发机构应为以下之一：{', '.join(authorities)}"
        
        return True, ""
    
    def _match_cert_type(self, ocr_result: OCRResult) -> Optional[int]:
        if not ocr_result.cert_name:
            return None
        
        with get_db_session() as session:
            cert_types = session.query(CertificateType).all()
            
            for cert_type in cert_types:
                if cert_type.name in ocr_result.cert_name or ocr_result.cert_name in cert_type.name:
                    return cert_type.id
            
            keywords = {
                "建造师": "注册建造师执业资格证书",
                "安全生产": "安全生产考核合格证书",
                "工程师": "工程师职称证书",
                "会计": "会计专业技术资格证书",
                "PMP": "PMP项目管理专业人士资格证书",
            }
            
            for keyword, type_name in keywords.items():
                if keyword in ocr_result.cert_name:
                    for cert_type in cert_types:
                        if cert_type.name == type_name:
                            return cert_type.id
        
        return None
    
    def verify_new_certificate(self,
                               employee_id: int,
                               image_path: str,
                               cert_type_id: Optional[int] = None,
                               manual_data: Optional[Dict] = None) -> VerificationResult:
        result = VerificationResult(success=False, issues=[], updated_fields={})
        
        with get_db_session() as session:
            employee = session.query(Employee).filter(Employee.id == employee_id).first()
            if not employee:
                result.message = f"员工ID {employee_id} 不存在"
                return result
        
        if not os.path.exists(image_path):
            result.message = f"图片文件不存在: {image_path}"
            return result
        
        try:
            ocr_result, metadata = self.ocr_engine.process_image(image_path)
        except Exception as e:
            result.message = f"OCR识别失败: {str(e)}"
            return result
        
        if ocr_result.confidence < self.min_confidence and not manual_data:
            result.message = f"OCR识别置信度过低（{ocr_result.confidence:.2f}），请手动输入证书信息"
            result.issues.append("OCR识别置信度不足")
            return result
        
        final_data = {
            "cert_name": ocr_result.cert_name,
            "cert_number": ocr_result.cert_number,
            "issuing_authority": ocr_result.issuing_authority,
            "issue_date": ocr_result.issue_date,
            "expiry_date": ocr_result.expiry_date,
            "score": ocr_result.score,
        }
        
        if manual_data:
            for key, value in manual_data.items():
                if value is not None:
                    final_data[key] = value
        
        if not cert_type_id:
            cert_type_id = self._match_cert_type(ocr_result)
            if not cert_type_id and final_data.get("cert_name"):
                result.issues.append(f"无法自动识别证书类型：{final_data['cert_name']}，请手动指定")
                result.message = "证书类型识别失败"
                return result
        
        all_issues = []
        
        if final_data.get("cert_number"):
            valid, msg = self._validate_cert_number(final_data["cert_number"], cert_type_id)
            if not valid:
                all_issues.append(msg)
        
        if final_data.get("issue_date") or final_data.get("expiry_date"):
            valid, msg = self._validate_dates(final_data.get("issue_date"), final_data.get("expiry_date"))
            if not valid:
                all_issues.append(msg)
        
        if final_data.get("issuing_authority"):
            valid, msg = self._validate_issuing_authority(final_data["issuing_authority"], cert_type_id)
            if not valid:
                all_issues.append(msg)
        
        if all_issues:
            result.issues = all_issues
            result.message = "证书信息校验失败"
            return result
        
        result.updated_fields = final_data
        
        with get_db_session() as session:
            old_cert = session.query(Certificate).filter(
                Certificate.employee_id == employee_id,
                Certificate.cert_type_id == cert_type_id,
                Certificate.status == "valid"
            ).first()
            
            new_cert = Certificate(
                employee_id=employee_id,
                cert_type_id=cert_type_id,
                cert_name=final_data.get("cert_name", ""),
                cert_number=final_data.get("cert_number"),
                issuing_authority=final_data.get("issuing_authority"),
                issue_date=final_data.get("issue_date"),
                expiry_date=final_data.get("expiry_date"),
                score=final_data.get("score"),
                image_path=image_path,
                ocr_data={
                    "raw_text": ocr_result.raw_text,
                    "confidence": ocr_result.confidence,
                    "metadata": metadata,
                },
                status="valid",
                verified=True,
                verified_at=datetime.now(),
                source="ocr",
            )
            
            session.add(new_cert)
            session.flush()
            
            if old_cert:
                old_cert.status = "replaced"
                result.updated_fields["replaced_certificate_id"] = old_cert.id
            
            related_tasks = session.query(Task).filter(
                Task.employee_id == employee_id,
                Task.certificate_id == (old_cert.id if old_cert else None),
                Task.status.in_([TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value, TaskStatus.ESCALATED.value])
            ).all()
            
            for task in related_tasks:
                task.status = TaskStatus.COMPLETED.value
                task.completed_at = datetime.now()
                task.completed_notes = f"员工已上传新证书（ID: {new_cert.id}），任务自动完成"
            
            result.certificate_id = new_cert.id
            result.success = True
            result.message = f"证书验证通过，已更新台账。新证书ID: {new_cert.id}"
            
            if old_cert:
                result.message += f" 旧证书（ID: {old_cert.id}）已标记为已替换。"
            
            if related_tasks:
                result.message += f" 已自动完成 {len(related_tasks)} 个相关任务。"
        
        return result
    
    def manual_verify_certificate(self,
                                  certificate_id: int,
                                  verified: bool,
                                  verifier_id: int,
                                  notes: str = "") -> VerificationResult:
        result = VerificationResult(success=False, issues=[])
        
        with get_db_session() as session:
            cert = session.query(Certificate).filter(Certificate.id == certificate_id).first()
            
            if not cert:
                result.message = f"证书ID {certificate_id} 不存在"
                return result
            
            cert.verified = verified
            cert.verified_by = verifier_id
            cert.verified_at = datetime.now()
            cert.verification_notes = notes
            
            if verified:
                cert.status = "valid"
                result.message = "证书验证通过"
            else:
                cert.status = "invalid"
                result.message = "证书验证不通过"
            
            result.success = True
            result.certificate_id = certificate_id
            result.updated_fields = {
                "verified": verified,
                "verified_by": verifier_id,
                "verified_at": datetime.now().isoformat(),
                "verification_notes": notes,
                "status": cert.status,
            }
            
            if verified:
                related_tasks = session.query(Task).filter(
                    Task.certificate_id == certificate_id,
                    Task.status.in_([TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value, TaskStatus.ESCALATED.value])
                ).all()
                
                for task in related_tasks:
                    task.status = TaskStatus.COMPLETED.value
                    task.completed_at = datetime.now()
                    task.completed_notes = f"证书已通过验证，任务自动完成。备注：{notes}"
        
        return result
    
    def check_and_update_expired_certificates(self) -> Dict:
        today = date.today()
        stats = {
            "total_checked": 0,
            "newly_expired": 0,
            "already_expired": 0,
            "tasks_created": 0,
        }
        
        with get_db_session() as session:
            valid_certs = session.query(Certificate).filter(
                Certificate.status == "valid",
                Certificate.expiry_date.isnot(None)
            ).all()
            
            stats["total_checked"] = len(valid_certs)
            
            for cert in valid_certs:
                if cert.expiry_date < today:
                    cert.status = "expired"
                    stats["newly_expired"] += 1
        
        return stats


_certificate_validator_singleton = None


def get_certificate_validator() -> CertificateValidator:
    global _certificate_validator_singleton
    if _certificate_validator_singleton is None:
        _certificate_validator_singleton = CertificateValidator()
    return _certificate_validator_singleton
