import os
import sys
import uuid
from datetime import datetime, date
from typing import Optional, Dict, List, Tuple
import argparse

from config import Config
from database import init_db, get_db_session
from models import (
    Department, Employee, CertificateType, PositionRequirement,
    Certificate, Task, TrainingCourse, TrainingPlan, ImportBatch
)
from ocr_engine import get_ocr_engine
from compliance_engine import get_compliance_engine
from task_manager import get_task_manager
from certificate_validator import get_certificate_validator
from batch_importer import get_batch_importer
from report_generator import get_report_generator
from training_engine import get_training_engine
from query_engine import get_query_engine, QueryFilter
from audit_logger import get_audit_logger, audit_log, get_concurrent_processor
from scheduler import get_scheduler


Config.ensure_dirs()
init_db()


class CertificateManagementSystem:
    def __init__(self):
        self.ocr_engine = get_ocr_engine()
        self.compliance_engine = get_compliance_engine()
        self.task_manager = get_task_manager()
        self.certificate_validator = get_certificate_validator()
        self.batch_importer = get_batch_importer()
        self.report_generator = get_report_generator()
        self.training_engine = get_training_engine()
        self.query_engine = get_query_engine()
        self.audit_logger = get_audit_logger()
        self.scheduler = get_scheduler()
        self.concurrent_processor = get_concurrent_processor()
    
    def start(self):
        self.scheduler.start()
        self.audit_logger.logger.info("Certificate Management System started successfully")
    
    def stop(self):
        self.scheduler.shutdown()
        self.concurrent_processor.shutdown()
        self.audit_logger.logger.info("Certificate Management System stopped")
    
    def initialize_demo_data(self):
        with get_db_session() as session:
            if session.query(Department).count() > 0:
                print("Demo data already exists, skipping initialization")
                return
            
            departments = [
                Department(name="技术部"),
                Department(name="工程部"),
                Department(name="安全部"),
                Department(name="财务部"),
                Department(name="人力资源部"),
            ]
            session.add_all(departments)
            session.flush()
            
            dept_map = {d.name: d for d in departments}
            
            employees = [
                Employee(employee_no="E001", name="张三", gender="男", phone="13800138001", 
                        email="zhangsan@company.com", position="项目经理", 
                        department_id=dept_map["技术部"].id, hire_date=date(2020, 1, 15)),
                Employee(employee_no="E002", name="李四", gender="男", phone="13800138002",
                        email="lisi@company.com", position="安全员",
                        department_id=dept_map["安全部"].id, hire_date=date(2020, 3, 20)),
                Employee(employee_no="E003", name="王五", gender="男", phone="13800138003",
                        email="wangwu@company.com", position="土建工程师",
                        department_id=dept_map["工程部"].id, hire_date=date(2019, 6, 10)),
                Employee(employee_no="E004", name="赵六", gender="女", phone="13800138004",
                        email="zhaoliu@company.com", position="会计",
                        department_id=dept_map["财务部"].id, hire_date=date(2021, 2, 1)),
                Employee(employee_no="E005", name="钱七", gender="男", phone="13800138005",
                        email="qianqi@company.com", position="技术总监",
                        department_id=dept_map["技术部"].id, hire_date=date(2018, 8, 15)),
            ]
            session.add_all(employees)
            session.flush()
            
            dept_map["技术部"].manager_id = employees[4].id
            
            cert_types = [
                CertificateType(code="JZS", name="注册建造师执业资格证书", category="执业资格", 
                               description="注册建造师执业资格证书", validity_years=3, is_required=True),
                CertificateType(code="AQC", name="安全生产考核合格证书", category="安全资质",
                               description="安全生产管理人员考核合格证书", validity_years=3, is_required=True),
                CertificateType(code="GCS", name="工程师职称证书", category="职称",
                               description="中级工程师职称证书", validity_years=None, is_required=False),
                CertificateType(code="KJ", name="会计专业技术资格证书", category="专业资格",
                               description="中级会计师资格证书", validity_years=None, is_required=True),
                CertificateType(code="PMP", name="PMP项目管理专业人士资格证书", category="项目管理",
                               description="PMI项目管理专业人士认证", validity_years=3, is_required=False),
            ]
            session.add_all(cert_types)
            session.flush()
            
            cert_type_map = {ct.code: ct for ct in cert_types}
            
            position_requirements = [
                PositionRequirement(position="项目经理", department_id=dept_map["技术部"].id,
                                   cert_type_id=cert_type_map["JZS"].id, requirement_level="required"),
                PositionRequirement(position="项目经理", department_id=dept_map["技术部"].id,
                                   cert_type_id=cert_type_map["AQC"].id, requirement_level="required",
                                   minimum_score=None),
                PositionRequirement(position="安全员", department_id=dept_map["安全部"].id,
                                   cert_type_id=cert_type_map["AQC"].id, requirement_level="required"),
                PositionRequirement(position="土建工程师", department_id=dept_map["工程部"].id,
                                   cert_type_id=cert_type_map["GCS"].id, requirement_level="required"),
                PositionRequirement(position="会计", department_id=dept_map["财务部"].id,
                                   cert_type_id=cert_type_map["KJ"].id, requirement_level="required"),
                PositionRequirement(position="技术总监", department_id=dept_map["技术部"].id,
                                   cert_type_id=cert_type_map["PMP"].id, requirement_level="required"),
            ]
            session.add_all(position_requirements)
            
            today = date.today()
            certificates = [
                Certificate(employee_id=employees[0].id, cert_type_id=cert_type_map["JZS"].id,
                           cert_name="一级注册建造师执业资格证书", cert_number="JZS2023001234",
                           issuing_authority="中华人民共和国住房和城乡建设部",
                           issue_date=date(2023, 3, 15), expiry_date=today.replace(year=today.year + 1),
                           status="valid", verified=True, verified_at=datetime.now(), source="demo"),
                Certificate(employee_id=employees[1].id, cert_type_id=cert_type_map["AQC"].id,
                           cert_name="安全生产考核合格证书(B类)", cert_number="京建安B2023000567",
                           issuing_authority="北京市住房和城乡建设委员会",
                           issue_date=date(2023, 6, 20), expiry_date=today.replace(year=today.year + 1, month=6),
                           status="valid", verified=True, verified_at=datetime.now(), source="demo"),
                Certificate(employee_id=employees[2].id, cert_type_id=cert_type_map["GCS"].id,
                           cert_name="工程师职称证书", cert_number="GCS2022000890",
                           issuing_authority="北京市人力资源和社会保障局",
                           issue_date=date(2022, 10, 25), expiry_date=None,
                           status="valid", verified=True, verified_at=datetime.now(), source="demo"),
                Certificate(employee_id=employees[3].id, cert_type_id=cert_type_map["KJ"].id,
                           cert_name="中级会计专业技术资格证书", cert_number="KJ2023001122",
                           issuing_authority="财政部、人力资源社会保障部",
                           issue_date=date(2023, 11, 5), expiry_date=None, score=85.0,
                           status="valid", verified=True, verified_at=datetime.now(), source="demo"),
                Certificate(employee_id=employees[4].id, cert_type_id=cert_type_map["PMP"].id,
                           cert_name="PMP项目管理专业人士资格证书", cert_number="PMP-2023-001234",
                           issuing_authority="Project Management Institute",
                           issue_date=date(2023, 8, 15), expiry_date=today.replace(year=today.year - 1),
                           status="valid", verified=True, verified_at=datetime.now(), source="demo"),
            ]
            session.add_all(certificates)
            
            training_courses = [
                TrainingCourse(course_code="TRAIN001", name="注册建造师考前培训",
                              description="一级注册建造师执业资格考试考前培训课程",
                              category="执业资格", cert_type_id=cert_type_map["JZS"].id,
                              duration_hours=80, provider="建设部培训中心"),
                TrainingCourse(course_code="TRAIN002", name="安全生产管理人员培训",
                              description="安全生产考核合格证书培训课程",
                              category="安全资质", cert_type_id=cert_type_map["AQC"].id,
                              duration_hours=40, provider="安全生产培训中心"),
                TrainingCourse(course_code="TRAIN003", name="PMP项目管理培训",
                              description="PMP项目管理专业人士认证培训课程",
                              category="项目管理", cert_type_id=cert_type_map["PMP"].id,
                              duration_hours=60, provider="PMI授权培训机构"),
                TrainingCourse(course_code="TRAIN004", name="中级会计师考前培训",
                              description="中级会计专业技术资格考试培训课程",
                              category="专业资格", cert_type_id=cert_type_map["KJ"].id,
                              duration_hours=100, provider="会计学院"),
            ]
            session.add_all(training_courses)
            
            self.audit_logger.logger.info("Demo data initialized successfully")
            print("Demo data initialized successfully")
    
    @audit_log(action="upload_certificate", resource_type="certificate")
    def upload_certificate(self, employee_id: int, image_path: str, 
                          cert_type_id: Optional[int] = None, 
                          manual_data: Optional[Dict] = None) -> Dict:
        result = self.certificate_validator.verify_new_certificate(
            employee_id, image_path, cert_type_id, manual_data
        )
        
        with get_db_session() as session:
            employee = session.query(Employee).filter(Employee.id == employee_id).first()
            employee_name = employee.name if employee else "Unknown"
        
        self.audit_logger.log_certificate_upload(
            employee_id=employee_id,
            employee_name=employee_name,
            certificate_id=result.certificate_id,
            success=result.success,
            message=result.message,
            issues=result.issues,
        )
        
        return {
            "success": result.success,
            "certificate_id": result.certificate_id,
            "message": result.message,
            "issues": result.issues,
            "updated_fields": result.updated_fields,
        }
    
    def upload_certificate_async(self, employee_id: int, image_path: str,
                                cert_type_id: Optional[int] = None,
                                manual_data: Optional[Dict] = None) -> str:
        task_id = f"ocr_{uuid.uuid4().hex}"
        self.concurrent_processor.submit(
            task_id,
            self.upload_certificate,
            employee_id, image_path, cert_type_id, manual_data
        )
        return task_id
    
    def get_async_upload_result(self, task_id: str) -> Optional[Dict]:
        return self.concurrent_processor.get_result(task_id)
    
    @audit_log(action="verify_certificate", resource_type="certificate")
    def verify_certificate(self, certificate_id: int, verified: bool,
                           verifier_id: int, notes: str = "") -> Dict:
        result = self.certificate_validator.manual_verify_certificate(
            certificate_id, verified, verifier_id, notes
        )
        
        with get_db_session() as session:
            verifier = session.query(Employee).filter(Employee.id == verifier_id).first()
            verifier_name = verifier.name if verifier else "Unknown"
        
        self.audit_logger.log_certificate_verification(
            certificate_id=certificate_id,
            verifier_id=verifier_id,
            verifier_name=verifier_name,
            verified=verified,
            notes=notes,
        )
        
        return {
            "success": result.success,
            "certificate_id": result.certificate_id,
            "message": result.message,
            "updated_fields": result.updated_fields,
        }
    
    @audit_log(action="complete_task", resource_type="task")
    def complete_task(self, task_id: int, completion_notes: str,
                      completed_by: Optional[int] = None) -> Dict:
        task = self.task_manager.complete_task(task_id, completion_notes, completed_by)
        
        if task:
            with get_db_session() as session:
                completer = session.query(Employee).filter(Employee.id == completed_by).first() if completed_by else None
                completer_name = completer.name if completer else "Unknown"
            
            self.audit_logger.log_task_completion(
                task_id=task_id,
                completer_id=completed_by,
                completer_name=completer_name,
                notes=completion_notes,
            )
            
            return {
                "success": True,
                "task_id": task.id,
                "status": task.status,
                "message": "任务已完成",
            }
        
        return {"success": False, "message": f"任务ID {task_id} 不存在"}
    
    @audit_log(action="import_certificates", resource_type="import_batch")
    def import_certificates(self, file_path: str, imported_by: Optional[int] = None) -> Dict:
        result = self.batch_importer.import_from_file(file_path, imported_by)
        
        with get_db_session() as session:
            importer = session.query(Employee).filter(Employee.id == imported_by).first() if imported_by else None
            importer_name = importer.name if importer else "Unknown"
        
        self.audit_logger.log_batch_import(
            batch_no=result.batch_no,
            imported_by=imported_by,
            importer_name=importer_name,
            success_count=result.success_count,
            error_count=result.error_count,
            duplicate_count=result.duplicate_count,
            file_name=os.path.basename(file_path),
        )
        
        return {
            "batch_no": result.batch_no,
            "total_records": result.total_records,
            "success_count": result.success_count,
            "duplicate_count": result.duplicate_count,
            "error_count": result.error_count,
            "error_details": result.error_details,
        }
    
    def generate_import_template(self, output_path: str) -> str:
        return self.batch_importer.generate_import_template(output_path)
    
    def run_daily_check(self) -> Dict:
        result = self.scheduler.daily_compliance_check()
        return {
            "success": result.success,
            "task_name": result.task_name,
            "start_time": result.start_time.isoformat(),
            "end_time": result.end_time.isoformat() if result.end_time else None,
            "duration_seconds": (result.end_time - result.start_time).total_seconds() if result.end_time else None,
            "error_message": result.error_message,
            "details": result.details,
        }
    
    def run_monthly_report(self) -> Dict:
        result = self.scheduler.monthly_report_generation()
        return {
            "success": result.success,
            "task_name": result.task_name,
            "start_time": result.start_time.isoformat(),
            "end_time": result.end_time.isoformat() if result.end_time else None,
            "error_message": result.error_message,
            "details": result.details,
        }
    
    def check_employee_compliance(self, employee_id: int) -> Dict:
        with get_db_session() as session:
            employee = session.query(Employee).filter(Employee.id == employee_id).first()
            if not employee:
                return {"success": False, "message": f"员工ID {employee_id} 不存在"}
            
            report = self.compliance_engine.check_employee_compliance(employee)
            
            return {
                "employee_id": employee.id,
                "employee_name": employee.name,
                "employee_no": employee.employee_no,
                "department": employee.department.name if employee.department else None,
                "position": employee.position,
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
    
    def check_department_compliance(self, department_id: int) -> Dict:
        return self.compliance_engine.get_department_compliance_summary(department_id)
    
    def query_certificates(self, **kwargs) -> Dict:
        certificates = self.query_engine.advanced_query(**kwargs)
        return {
            "total": len(certificates),
            "certificates": certificates,
        }
    
    def export_certificates(self, **kwargs) -> Dict:
        return self.query_engine.export_certificates(**kwargs)
    
    def get_statistics(self) -> Dict:
        stats = self.query_engine.get_statistics()
        task_stats = self.task_manager.get_task_statistics()
        training_stats = self.training_engine.get_training_plan_statistics()
        
        return {
            "certificates": stats,
            "tasks": task_stats,
            "training": training_stats,
            "timestamp": datetime.now().isoformat(),
        }
    
    def get_pending_tasks(self, assignee_id: Optional[int] = None, 
                         department_id: Optional[int] = None) -> List[Dict]:
        tasks = self.task_manager.get_pending_tasks(assignee_id, department_id)
        return [
            {
                "id": t.id,
                "task_type": t.task_type,
                "title": t.title,
                "employee_name": t.employee.name if t.employee else None,
                "assignee_name": t.assignee.name if t.assignee else None,
                "deadline": t.deadline.isoformat() if t.deadline else None,
                "status": t.status,
                "priority": t.priority,
                "escalation_level": t.escalation_level,
                "reminder_count": t.reminder_count,
                "days_overdue": (date.today() - t.deadline).days if t.deadline and t.deadline < date.today() else None,
            }
            for t in tasks
        ]
    
    def check_training_needs(self) -> List[Dict]:
        return self.training_engine.check_low_compliance_departments()
    
    def generate_training_plans(self) -> List[Dict]:
        plans = self.training_engine.auto_generate_training_plans()
        return [
            {
                "plan_id": p.id,
                "plan_code": p.plan_code,
                "name": p.name,
                "department_name": p.department.name if p.department else None,
                "start_date": p.start_date.isoformat() if p.start_date else None,
                "end_date": p.end_date.isoformat() if p.end_date else None,
                "status": p.status,
                "reason": p.reason,
            }
            for p in plans
        ]
    
    def get_scheduled_jobs(self) -> List[Dict]:
        return self.scheduler.get_scheduled_jobs()
    
    def run_scheduled_task(self, task_name: str) -> Dict:
        result = self.scheduler.run_manual_task(task_name)
        return {
            "success": result.success,
            "task_name": result.task_name,
            "start_time": result.start_time.isoformat(),
            "end_time": result.end_time.isoformat() if result.end_time else None,
            "error_message": result.error_message,
            "details": result.details,
        }


_cms_singleton = None


def get_certificate_management_system() -> CertificateManagementSystem:
    global _cms_singleton
    if _cms_singleton is None:
        _cms_singleton = CertificateManagementSystem()
    return _cms_singleton


def main():
    parser = argparse.ArgumentParser(description="企业级员工资质证书自动化管理与岗位合规监控系统")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    subparsers.add_parser("init-demo", help="初始化演示数据")
    
    subparsers.add_parser("start", help="启动系统（包括定时任务）")
    
    subparsers.add_parser("daily-check", help="手动执行每日合规检查")
    
    subparsers.add_parser("monthly-report", help="手动生成月度报告")
    
    subparsers.add_parser("stats", help="查看系统统计数据")
    
    subparsers.add_parser("jobs", help="查看定时任务列表")
    
    subparsers.add_parser("generate-template", help="生成批量导入模板")\
        .add_argument("output", help="输出文件路径（.xlsx或.csv）")
    
    import_parser = subparsers.add_parser("import", help="批量导入证书数据")
    import_parser.add_argument("file", help="导入文件路径")
    import_parser.add_argument("--imported-by", type=int, default=None, help="导入人ID")
    
    compliance_parser = subparsers.add_parser("check-compliance", help="检查合规性")
    compliance_parser.add_argument("--employee-id", type=int, help="员工ID")
    compliance_parser.add_argument("--department-id", type=int, help="部门ID")
    
    upload_parser = subparsers.add_parser("upload", help="上传证书图片")
    upload_parser.add_argument("image", help="证书图片路径")
    upload_parser.add_argument("--employee-id", type=int, required=True, help="员工ID")
    upload_parser.add_argument("--cert-type-id", type=int, help="证书类型ID")
    
    args = parser.parse_args()
    
    cms = get_certificate_management_system()
    
    if args.command == "init-demo":
        cms.initialize_demo_data()
    
    elif args.command == "start":
        print("Starting Certificate Management System...")
        cms.start()
        print("System started. Press Ctrl+C to stop.")
        try:
            import time
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("\nShutting down...")
            cms.stop()
    
    elif args.command == "daily-check":
        print("Running daily compliance check...")
        result = cms.run_daily_check()
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "monthly-report":
        print("Generating monthly report...")
        result = cms.run_monthly_report()
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "stats":
        result = cms.get_statistics()
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "jobs":
        jobs = cms.get_scheduled_jobs()
        import json
        print(json.dumps(jobs, indent=2, ensure_ascii=False))
    
    elif args.command == "generate-template":
        path = cms.generate_import_template(args.output)
        print(f"导入模板已生成: {path}")
    
    elif args.command == "import":
        print(f"导入文件: {args.file}")
        result = cms.import_certificates(args.file, args.imported_by)
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "check-compliance":
        if args.employee_id:
            result = cms.check_employee_compliance(args.employee_id)
        elif args.department_id:
            result = cms.check_department_compliance(args.department_id)
        else:
            result = cms.check_training_needs()
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "upload":
        print(f"处理证书图片: {args.image}")
        result = cms.upload_certificate(args.employee_id, args.image, args.cert_type_id)
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
