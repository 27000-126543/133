import uuid
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

from sqlalchemy import and_

from database import get_db_session
from models import Department, Employee, MonthlyReport, TrainingCourse, TrainingPlan
from config import Config


@dataclass
class TrainingRecommendation:
    department_id: int
    department_name: str
    current_compliance_rate: float
    consecutive_low_months: int
    issues_summary: Dict
    recommended_courses: List[TrainingCourse]
    target_employees: List[Employee]
    estimated_duration: float = 0.0
    reason: str = ""


class TrainingEngine:
    def __init__(self):
        self.compliance_threshold = Config.COMPLIANCE_THRESHOLD
        self.consecutive_months_threshold = Config.CONSECUTIVE_MONTHS_THRESHOLD
    
    def _get_monthly_reports(self, department_id: int, months: int) -> List[MonthlyReport]:
        today = date.today()
        month_dates = []
        for i in range(months):
            d = today - timedelta(days=i * 30)
            month_dates.append(d.strftime("%Y-%m"))
        
        with get_db_session() as session:
            reports = session.query(MonthlyReport).filter(
                MonthlyReport.department_id == department_id,
                MonthlyReport.report_month.in_(month_dates)
            ).order_by(MonthlyReport.report_month.desc()).all()
            
            sorted_reports = []
            for month in month_dates:
                for report in reports:
                    if report.report_month == month:
                        sorted_reports.append(report)
                        break
            
            return sorted_reports
    
    def check_low_compliance_departments(self) -> List[Dict]:
        with get_db_session() as session:
            departments = session.query(Department).all()
        
        low_compliance_depts = []
        
        for dept in departments:
            reports = self._get_monthly_reports(dept.id, self.consecutive_months_threshold)
            
            if len(reports) < self.consecutive_months_threshold:
                continue
            
            consecutive_low = all(
                report.compliance_rate < self.compliance_threshold 
                for report in reports
            )
            
            if consecutive_low:
                low_compliance_depts.append({
                    "department_id": dept.id,
                    "department_name": dept.name,
                    "consecutive_months": self.consecutive_months_threshold,
                    "compliance_history": [
                        {"month": r.report_month, "rate": r.compliance_rate}
                        for r in reports
                    ],
                    "current_rate": reports[0].compliance_rate,
                })
        
        return low_compliance_depts
    
    def identify_skill_gaps(self, department_id: int) -> Dict:
        with get_db_session() as session:
            employees = session.query(Employee).filter(
                Employee.department_id == department_id,
                Employee.is_active == True
            ).all()
            
            from compliance_engine import get_compliance_engine
            compliance_engine = get_compliance_engine()
            
            cert_type_gaps = {}
            
            for emp in employees:
                report = compliance_engine.check_employee_compliance(emp)
                
                for issue in report.issues:
                    if issue.cert_type_id not in cert_type_gaps:
                        cert_type_gaps[issue.cert_type_id] = {
                            "cert_type_name": issue.cert_type_name,
                            "issue_count": 0,
                            "employees": [],
                            "issue_types": {},
                        }
                    
                    cert_type_gaps[issue.cert_type_id]["issue_count"] += 1
                    if emp.name not in cert_type_gaps[issue.cert_type_id]["employees"]:
                        cert_type_gaps[issue.cert_type_id]["employees"].append(emp.name)
                    
                    status_key = issue.status.value
                    cert_type_gaps[issue.cert_type_id]["issue_types"][status_key] = \
                        cert_type_gaps[issue.cert_type_id]["issue_types"].get(status_key, 0) + 1
            
            sorted_gaps = sorted(
                cert_type_gaps.values(),
                key=lambda x: x["issue_count"],
                reverse=True
            )
            
            return {
                "department_id": department_id,
                "total_employees": len(employees),
                "total_gaps": sum(g["issue_count"] for g in sorted_gaps),
                "skill_gaps": sorted_gaps,
            }
    
    def find_matching_courses(self, cert_type_ids: List[int]) -> List[TrainingCourse]:
        with get_db_session() as session:
            courses = session.query(TrainingCourse).filter(
                TrainingCourse.cert_type_id.in_(cert_type_ids),
                TrainingCourse.is_active == True
            ).all()
            
            if not courses:
                courses = session.query(TrainingCourse).filter(
                    TrainingCourse.is_active == True
                ).all()
                
                matched = []
                for cert_type_id in cert_type_ids:
                    from models import CertificateType
                    cert_type = session.query(CertificateType).filter(
                        CertificateType.id == cert_type_id
                    ).first()
                    
                    if cert_type:
                        for course in courses:
                            if (cert_type.name in course.name or 
                                course.name in cert_type.name or
                                (cert_type.category and cert_type.category == course.category)):
                                if course not in matched:
                                    matched.append(course)
                
                return matched
            
            return courses
    
    def generate_training_recommendation(self, department_id: int) -> Optional[TrainingRecommendation]:
        dept_info = None
        for d in self.check_low_compliance_departments():
            if d["department_id"] == department_id:
                dept_info = d
                break
        
        if not dept_info:
            return None
        
        skill_gaps = self.identify_skill_gaps(department_id)
        
        cert_type_ids = []
        for gap in skill_gaps["skill_gaps"]:
            with get_db_session() as session:
                from models import CertificateType
                ct = session.query(CertificateType).filter(
                    CertificateType.name == gap["cert_type_name"]
                ).first()
                if ct and ct.id not in cert_type_ids:
                    cert_type_ids.append(ct.id)
        
        recommended_courses = self.find_matching_courses(cert_type_ids)
        
        with get_db_session() as session:
            employees = session.query(Employee).filter(
                Employee.department_id == department_id,
                Employee.is_active == True
            ).all()
        
        reason_parts = [
            f"部门{dept_info['department_name']}已连续{dept_info['consecutive_months']}个月合规达标率低于{self.compliance_threshold * 100:.0f}%",
            f"当前合规率：{dept_info['current_rate'] * 100:.2f}%",
            f"共有{skill_gaps['total_gaps']}个资质问题需要解决",
        ]
        
        for gap in skill_gaps["skill_gaps"][:3]:
            reason_parts.append(
                f"- {gap['cert_type_name']}: {gap['issue_count']}个问题，涉及{len(gap['employees'])}名员工"
            )
        
        estimated_duration = sum(c.duration_hours or 0 for c in recommended_courses)
        
        return TrainingRecommendation(
            department_id=department_id,
            department_name=dept_info["department_name"],
            current_compliance_rate=dept_info["current_rate"],
            consecutive_low_months=dept_info["consecutive_months"],
            issues_summary=skill_gaps,
            recommended_courses=recommended_courses,
            target_employees=employees,
            estimated_duration=estimated_duration,
            reason="\n".join(reason_parts),
        )
    
    def generate_all_training_recommendations(self) -> List[TrainingRecommendation]:
        low_depts = self.check_low_compliance_departments()
        recommendations = []
        
        for dept_info in low_depts:
            with get_db_session() as session:
                existing_plan = session.query(TrainingPlan).filter(
                    TrainingPlan.department_id == dept_info["department_id"],
                    TrainingPlan.status.in_(["draft", "pending", "in_progress"])
                ).first()
                
                if existing_plan:
                    continue
            
            recommendation = self.generate_training_recommendation(dept_info["department_id"])
            if recommendation:
                recommendations.append(recommendation)
        
        return recommendations
    
    def create_training_plan(self, recommendation: TrainingRecommendation, created_by: Optional[int] = None) -> TrainingPlan:
        plan_code = f"TRAIN-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
        
        start_date = date.today() + timedelta(days=7)
        end_date = start_date + timedelta(days=int(recommendation.estimated_duration / 4 * 30) + 30)
        
        with get_db_session() as session:
            plan = TrainingPlan(
                plan_code=plan_code,
                name=f"{recommendation.department_name}专项培训计划",
                department_id=recommendation.department_id,
                course_ids=[c.id for c in recommendation.recommended_courses],
                target_employees=[e.id for e in recommendation.target_employees],
                start_date=start_date,
                end_date=end_date,
                status="pending",
                reason=recommendation.reason,
                created_by=created_by,
            )
            
            session.add(plan)
            session.flush()
            plan_id = plan.id
        
        with get_db_session() as session:
            return session.query(TrainingPlan).filter(TrainingPlan.id == plan_id).first()
    
    def auto_generate_training_plans(self) -> List[TrainingPlan]:
        recommendations = self.generate_all_training_recommendations()
        plans = []
        
        for rec in recommendations:
            plan = self.create_training_plan(rec)
            plans.append(plan)
        
        return plans
    
    def get_training_plan_statistics(self) -> Dict:
        with get_db_session() as session:
            total = session.query(TrainingPlan).count()
            draft = session.query(TrainingPlan).filter(TrainingPlan.status == "draft").count()
            pending = session.query(TrainingPlan).filter(TrainingPlan.status == "pending").count()
            in_progress = session.query(TrainingPlan).filter(TrainingPlan.status == "in_progress").count()
            completed = session.query(TrainingPlan).filter(TrainingPlan.status == "completed").count()
            cancelled = session.query(TrainingPlan).filter(TrainingPlan.status == "cancelled").count()
            
            courses = session.query(TrainingCourse).filter(TrainingCourse.is_active == True).count()
            
            low_depts = self.check_low_compliance_departments()
        
        return {
            "total_plans": total,
            "draft": draft,
            "pending": pending,
            "in_progress": in_progress,
            "completed": completed,
            "cancelled": cancelled,
            "active_courses": courses,
            "low_compliance_departments": len(low_depts),
            "low_compliance_details": low_depts,
        }


_training_engine_singleton = None


def get_training_engine() -> TrainingEngine:
    global _training_engine_singleton
    if _training_engine_singleton is None:
        _training_engine_singleton = TrainingEngine()
    return _training_engine_singleton
