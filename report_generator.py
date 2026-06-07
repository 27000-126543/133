import os
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import rcParams
import pandas as pd
import numpy as np

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.linecharts import HorizontalLineChart
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

from database import get_db_session
from models import Department, Employee, Certificate, MonthlyReport, Task
from compliance_engine import get_compliance_engine
from task_manager import get_task_manager
from config import Config

rcParams["font.sans-serif"] = ["Arial Unicode MS", "DejaVu Sans", "SimHei"]
rcParams["axes.unicode_minus"] = False


class ReportGenerator:
    def __init__(self):
        self.compliance_engine = get_compliance_engine()
        self.task_manager = get_task_manager()
        self.report_dir = Config.REPORT_DIR
    
    def _get_report_month(self, report_date: Optional[date] = None) -> str:
        if report_date is None:
            report_date = date.today()
        return report_date.strftime("%Y-%m")
    
    def _get_trend_data(self, department_id: Optional[int] = None, months: int = 6) -> Dict:
        today = date.today()
        trend_data = {
            "months": [],
            "compliance_rates": [],
            "certification_rates": [],
            "expiry_rates": [],
        }
        
        with get_db_session() as session:
            for i in range(months - 1, -1, -1):
                month_date = today - timedelta(days=i * 30)
                month_str = month_date.strftime("%Y-%m")
                trend_data["months"].append(month_str)
                
                report = session.query(MonthlyReport).filter(
                    MonthlyReport.report_month == month_str,
                    (MonthlyReport.department_id == department_id) if department_id else True
                ).order_by(MonthlyReport.created_at.desc()).first()
                
                if report:
                    trend_data["compliance_rates"].append(report.compliance_rate * 100)
                    trend_data["certification_rates"].append(report.certification_rate * 100)
                    trend_data["expiry_rates"].append(report.expiry_rate * 100)
                else:
                    trend_data["compliance_rates"].append(None)
                    trend_data["certification_rates"].append(None)
                    trend_data["expiry_rates"].append(None)
        
        return trend_data
    
    def _generate_trend_chart(self, trend_data: Dict, output_path: str) -> str:
        fig, axes = plt.subplots(2, 1, figsize=(12, 8))
        
        months = trend_data["months"]
        x = np.arange(len(months))
        
        ax1 = axes[0]
        width = 0.35
        
        compliance_rates = [r if r is not None else 0 for r in trend_data["compliance_rates"]]
        certification_rates = [r if r is not None else 0 for r in trend_data["certification_rates"]]
        
        bars1 = ax1.bar(x - width/2, compliance_rates, width, label="合规达标率", color="#4CAF50", alpha=0.8)
        bars2 = ax1.bar(x + width/2, certification_rates, width, label="持证率", color="#2196F3", alpha=0.8)
        
        ax1.set_title("各月合规达标率与持证率趋势", fontsize=14, fontweight="bold")
        ax1.set_ylabel("百分比 (%)")
        ax1.set_xticks(x)
        ax1.set_xticklabels(months)
        ax1.legend()
        ax1.grid(axis="y", alpha=0.3)
        ax1.set_ylim(0, 100)
        
        for bar in bars1:
            height = bar.get_height()
            if height > 0:
                ax1.text(bar.get_x() + bar.get_width()/2., height, f"{height:.1f}%", ha="center", va="bottom", fontsize=8)
        for bar in bars2:
            height = bar.get_height()
            if height > 0:
                ax1.text(bar.get_x() + bar.get_width()/2., height, f"{height:.1f}%", ha="center", va="bottom", fontsize=8)
        
        ax2 = axes[1]
        expiry_rates = [r if r is not None else 0 for r in trend_data["expiry_rates"]]
        
        ax2.plot(x, expiry_rates, marker="o", linewidth=2, markersize=8, color="#FF5722", label="到期率")
        ax2.fill_between(x, expiry_rates, alpha=0.3, color="#FF5722")
        
        ax2.set_title("各月证书到期率趋势", fontsize=14, fontweight="bold")
        ax2.set_xlabel("月份")
        ax2.set_ylabel("百分比 (%)")
        ax2.set_xticks(x)
        ax2.set_xticklabels(months)
        ax2.legend()
        ax2.grid(axis="y", alpha=0.3)
        ax2.set_ylim(0, max(10, max(expiry_rates) + 10) if expiry_rates else 10)
        
        for i, v in enumerate(expiry_rates):
            if v > 0:
                ax2.text(i, v + 1, f"{v:.1f}%", ha="center", va="bottom", fontsize=8)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close()
        
        return output_path
    
    def _generate_department_chart(self, dept_data: List[Dict], output_path: str) -> str:
        fig, ax = plt.subplots(figsize=(14, 6))
        
        dept_names = [d["department_name"][:8] for d in dept_data]
        compliance_rates = [d["compliance_rate"] * 100 for d in dept_data]
        
        colors_list = ["#4CAF50" if r >= 80 else "#FF9800" if r >= 60 else "#F44336" for r in compliance_rates]
        
        bars = ax.bar(dept_names, compliance_rates, color=colors_list, alpha=0.8)
        
        ax.set_title("各部门合规达标率对比", fontsize=14, fontweight="bold")
        ax.set_xlabel("部门")
        ax.set_ylabel("合规达标率 (%)")
        ax.grid(axis="y", alpha=0.3)
        ax.axhline(y=80, color="#F44336", linestyle="--", linewidth=2, label="80% 达标线")
        ax.legend()
        ax.set_ylim(0, 100)
        
        plt.xticks(rotation=45, ha="right")
        
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 1, f"{height:.1f}%", ha="center", va="bottom", fontsize=9, fontweight="bold")
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close()
        
        return output_path
    
    def _calculate_department_stats(self, department_id: int, report_month: str) -> Dict:
        with get_db_session() as session:
            dept = session.query(Department).filter(Department.id == department_id).first()
            dept_name = dept.name if dept else "未知部门"
            
            employees = session.query(Employee).filter(
                Employee.department_id == department_id,
                Employee.is_active == True
            ).all()
            
            total_employees = len(employees)
            employee_ids = [e.id for e in employees]
            
            certificates = session.query(Certificate).filter(
                Certificate.employee_id.in_(employee_ids)
            ).all()
            
            total_certificates = len(certificates)
            valid_certificates = sum(1 for c in certificates if c.is_valid)
            expired_certificates = sum(1 for c in certificates if c.is_expired)
            
            today = date.today()
            cutoff = today + timedelta(days=Config.EXPIRY_WARNING_DAYS)
            expiring_soon = sum(1 for c in certificates 
                               if c.expiry_date and c.expiry_date > today and c.expiry_date <= cutoff and c.status == "valid")
            
            tasks = session.query(Task).filter(
                Task.employee_id.in_(employee_ids)
            ).all()
            
            pending_tasks = sum(1 for t in tasks if t.status in ["pending", "in_progress", "escalated"])
            completed_tasks = sum(1 for t in tasks if t.status == "completed")
            
            dept_report = self.compliance_engine.get_department_compliance_summary(department_id)
            
            certified_employees = dept_report["compliant_employees"]
            compliance_rate = dept_report["compliance_rate"]
            certification_rate = certified_employees / total_employees if total_employees > 0 else 0
            expiry_rate = expired_certificates / total_certificates if total_certificates > 0 else 0
            
            return {
                "department_id": department_id,
                "department_name": dept_name,
                "total_employees": total_employees,
                "certified_employees": certified_employees,
                "total_certificates": total_certificates,
                "valid_certificates": valid_certificates,
                "expiring_soon": expiring_soon,
                "expired": expired_certificates,
                "compliance_rate": compliance_rate,
                "certification_rate": certification_rate,
                "expiry_rate": expiry_rate,
                "pending_tasks": pending_tasks,
                "completed_tasks": completed_tasks,
                "issues_count": dept_report["issues_count"],
                "issues_by_type": dept_report["issues_by_type"],
            }
    
    def _generate_excel_report(self, all_dept_stats: List[Dict], report_month: str, trend_data: Dict) -> str:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        excel_path = os.path.join(self.report_dir, f"cert_report_{report_month}_{timestamp}.xlsx")
        
        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            summary_data = []
            for stats in all_dept_stats:
                summary_data.append({
                    "部门": stats["department_name"],
                    "员工总数": stats["total_employees"],
                    "持证人数": stats["certified_employees"],
                    "合规达标率(%)": round(stats["compliance_rate"] * 100, 2),
                    "持证率(%)": round(stats["certification_rate"] * 100, 2),
                    "证书总数": stats["total_certificates"],
                    "有效证书": stats["valid_certificates"],
                    "即将到期": stats["expiring_soon"],
                    "已过期": stats["expired"],
                    "到期率(%)": round(stats["expiry_rate"] * 100, 2),
                    "待处理任务": stats["pending_tasks"],
                    "已完成任务": stats["completed_tasks"],
                    "问题总数": stats["issues_count"],
                })
            
            df_summary = pd.DataFrame(summary_data)
            df_summary.to_excel(writer, index=False, sheet_name="部门汇总")
            
            if trend_data["months"]:
                trend_df = pd.DataFrame({
                    "月份": trend_data["months"],
                    "平均合规达标率(%)": trend_data["compliance_rates"],
                    "平均持证率(%)": trend_data["certification_rates"],
                    "平均到期率(%)": trend_data["expiry_rates"],
                })
                trend_df.to_excel(writer, index=False, sheet_name="历史趋势")
            
            for stats in all_dept_stats:
                dept_name = stats["department_name"][:25] if stats["department_name"] else "未知部门"
                dept_sheet_name = dept_name.replace("/", "_").replace("\\", "_")
                
                with get_db_session() as session:
                    employees = session.query(Employee).filter(
                        Employee.department_id == stats["department_id"],
                        Employee.is_active == True
                    ).all()
                    
                    employee_data = []
                    for emp in employees:
                        emp_report = self.compliance_engine.check_employee_compliance(emp)
                        employee_data.append({
                            "工号": emp.employee_no,
                            "姓名": emp.name,
                            "岗位": emp.position or "",
                            "合规率(%)": round(emp_report.compliance_rate * 100, 2),
                            "问题数": len(emp_report.issues),
                            "问题详情": "; ".join([i.issue_description for i in emp_report.issues]),
                        })
                    
                    df_dept = pd.DataFrame(employee_data)
                    df_dept.to_excel(writer, index=False, sheet_name=dept_sheet_name)
            
            workbook = writer.book
            for sheet_name in writer.sheets:
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
        
        return excel_path
    
    def _generate_pdf_report(self, all_dept_stats: List[Dict], report_month: str, 
                            trend_chart_path: str, dept_chart_path: str, trend_data: Dict) -> Optional[str]:
        if not REPORTLAB_AVAILABLE:
            print("Warning: reportlab not available, skipping PDF generation")
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        pdf_path = os.path.join(self.report_dir, f"cert_report_{report_month}_{timestamp}.pdf")
        
        doc = SimpleDocTemplate(pdf_path, pagesize=landscape(A4), 
                               rightMargin=0.5*inch, leftMargin=0.5*inch,
                               topMargin=0.5*inch, bottomMargin=0.5*inch)
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("title", parent=styles["Heading1"], fontSize=18, alignment=1, spaceAfter=12)
        subtitle_style = ParagraphStyle("subtitle", parent=styles["Heading2"], fontSize=14, spaceAfter=8)
        normal_style = styles["Normal"]
        
        story = []
        
        story.append(Paragraph("企业员工资质证书管理月度报告", title_style))
        story.append(Paragraph(f"报告月份：{report_month} | 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", subtitle_style))
        story.append(Spacer(1, 0.2*inch))
        
        total_employees = sum(d["total_employees"] for d in all_dept_stats)
        total_certified = sum(d["certified_employees"] for d in all_dept_stats)
        total_certs = sum(d["total_certificates"] for d in all_dept_stats)
        avg_compliance = sum(d["compliance_rate"] for d in all_dept_stats) / len(all_dept_stats) if all_dept_stats else 0
        low_compliance = [d for d in all_dept_stats if d["compliance_rate"] < Config.COMPLIANCE_THRESHOLD]
        
        summary_data = [
            ["统计项", "数值"],
            ["部门总数", str(len(all_dept_stats))],
            ["员工总数", str(total_employees)],
            ["持证人数", str(total_certified)],
            ["平均合规达标率", f"{avg_compliance * 100:.2f}%"],
            ["证书总数", str(total_certs)],
            ["即将到期(90天内)", str(sum(d["expiring_soon"] for d in all_dept_stats))],
            ["已过期", str(sum(d["expired"] for d in all_dept_stats))],
            ["待处理任务", str(sum(d["pending_tasks"] for d in all_dept_stats))],
            ["不达标部门数", f"{len(low_compliance)}"],
        ]
        
        summary_table = Table(summary_data, colWidths=[2.5*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("GRID", (0, 0), (-1, -1), 1, colors.grey),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F2F2F2")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F2F2F2"), colors.white]),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.3*inch))
        
        if low_compliance:
            story.append(Paragraph("⚠️ 预警：合规达标率低于80%的部门", subtitle_style))
            alert_data = [["部门", "合规达标率", "问题数"]]
            for d in low_compliance:
                alert_data.append([d["department_name"], f"{d['compliance_rate'] * 100:.2f}%", str(d["issues_count"])])
            alert_table = Table(alert_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
            alert_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F44336")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 1, colors.grey),
            ]))
            story.append(alert_table)
            story.append(Spacer(1, 0.3*inch))
        
        story.append(Paragraph("一、各部门合规达标率对比", subtitle_style))
        if os.path.exists(dept_chart_path):
            story.append(Image(dept_chart_path, width=9*inch, height=3.5*inch))
        story.append(Spacer(1, 0.3*inch))
        
        story.append(Paragraph("二、历史趋势分析", subtitle_style))
        if os.path.exists(trend_chart_path):
            story.append(Image(trend_chart_path, width=9*inch, height=5*inch))
        story.append(Spacer(1, 0.3*inch))
        
        story.append(PageBreak())
        
        story.append(Paragraph("三、各部门详细数据", subtitle_style))
        dept_table_data = [
            ["部门", "员工数", "合规率", "持证率", "证书数", "即将到期", "已过期", "待处理任务"]
        ]
        for d in all_dept_stats:
            row_color = colors.HexColor("#FFCDD2") if d["compliance_rate"] < Config.COMPLIANCE_THRESHOLD else colors.white
            dept_table_data.append([
                d["department_name"],
                str(d["total_employees"]),
                f"{d['compliance_rate'] * 100:.2f}%",
                f"{d['certification_rate'] * 100:.2f}%",
                str(d["total_certificates"]),
                str(d["expiring_soon"]),
                str(d["expired"]),
                str(d["pending_tasks"]),
            ])
        
        dept_table = Table(dept_table_data, colWidths=[1.5*inch, 0.8*inch, 0.9*inch, 0.9*inch, 0.8*inch, 1*inch, 0.8*inch, 1*inch])
        table_style = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 1, colors.grey),
        ]
        
        for i, d in enumerate(all_dept_stats, start=1):
            if d["compliance_rate"] < Config.COMPLIANCE_THRESHOLD:
                table_style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#FFCDD2")))
        
        dept_table.setStyle(TableStyle(table_style))
        story.append(dept_table)
        
        doc.build(story)
        return pdf_path
    
    def generate_monthly_report(self, report_date: Optional[date] = None) -> Dict:
        report_month = self._get_report_month(report_date)
        
        with get_db_session() as session:
            departments = session.query(Department).all()
            if not departments:
                departments = [Department(id=0, name="公司整体")]
        
        all_dept_stats = []
        for dept in departments:
            if dept.id == 0:
                continue
            stats = self._calculate_department_stats(dept.id, report_month)
            all_dept_stats.append(stats)
        
        if not all_dept_stats:
            all_dept_stats.append(self._calculate_department_stats(0, report_month))
        
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        trend_chart_path = os.path.join(self.report_dir, f"trend_chart_{report_month}_{timestamp}.png")
        dept_chart_path = os.path.join(self.report_dir, f"dept_chart_{report_month}_{timestamp}.png")
        
        trend_data = self._get_trend_data(months=6)
        self._generate_trend_chart(trend_data, trend_chart_path)
        self._generate_department_chart(all_dept_stats, dept_chart_path)
        
        excel_path = self._generate_excel_report(all_dept_stats, report_month, trend_data)
        pdf_path = self._generate_pdf_report(all_dept_stats, report_month, trend_chart_path, dept_chart_path, trend_data)
        
        report_data = {
            "report_month": report_month,
            "generated_at": datetime.now().isoformat(),
            "departments": all_dept_stats,
            "trend_data": trend_data,
            "charts": {
                "trend_chart": trend_chart_path,
                "department_chart": dept_chart_path,
            },
            "reports": {
                "excel": excel_path,
                "pdf": pdf_path,
            },
        }
        
        for stats in all_dept_stats:
            with get_db_session() as session:
                monthly_report = MonthlyReport(
                    report_month=report_month,
                    department_id=stats["department_id"] if stats["department_id"] > 0 else None,
                    total_employees=stats["total_employees"],
                    certified_employees=stats["certified_employees"],
                    total_certificates=stats["total_certificates"],
                    valid_certificates=stats["valid_certificates"],
                    expiring_soon=stats["expiring_soon"],
                    expired=stats["expired"],
                    compliance_rate=stats["compliance_rate"],
                    certification_rate=stats["certification_rate"],
                    expiry_rate=stats["expiry_rate"],
                    pending_tasks=stats["pending_tasks"],
                    completed_tasks=stats["completed_tasks"],
                    report_data=stats,
                    pdf_path=pdf_path,
                    excel_path=excel_path,
                )
                session.add(monthly_report)
        
        return report_data


_report_generator_singleton = None


def get_report_generator() -> ReportGenerator:
    global _report_generator_singleton
    if _report_generator_singleton is None:
        _report_generator_singleton = ReportGenerator()
    return _report_generator_singleton
