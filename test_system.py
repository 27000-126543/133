#!/usr/bin/env python3

import os
import sys
import tempfile
from datetime import date, timedelta
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import get_certificate_management_system
from config import Config


def test_system():
    print("=" * 80)
    print("企业级员工资质证书自动化管理系统 - 功能测试")
    print("=" * 80)
    
    cms = get_certificate_management_system()
    
    print("\n📋 步骤 1: 初始化演示数据...")
    try:
        cms.initialize_demo_data()
        print("   ✅ 演示数据初始化成功")
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        return False
    
    print("\n📊 步骤 2: 查看系统统计数据...")
    try:
        stats = cms.get_statistics()
        print(f"   ✅ 系统统计获取成功")
        print(f"   - 员工总数: {stats['certificates']['total_employees']}")
        print(f"   - 证书总数: {stats['certificates']['total_certificates']}")
        print(f"   - 即将到期: {stats['certificates']['expiring_soon']}")
        print(f"   - 已过期: {stats['certificates']['expired']}")
        print(f"   - 任务总数: {stats['tasks']['total']}")
    except Exception as e:
        print(f"   ❌ 失败: {e}")
    
    print("\n🔍 步骤 3: 检查员工合规性 (员工ID: 1)...")
    try:
        result = cms.check_employee_compliance(1)
        print(f"   ✅ 合规性检查成功")
        print(f"   - 员工: {result['employee_name']} ({result['employee_no']})")
        print(f"   - 岗位: {result['position']}")
        print(f"   - 合规率: {result['compliance_rate'] * 100:.2f}%")
        print(f"   - 问题数: {len(result['issues'])}")
        for issue in result['issues']:
            print(f"     * {issue['issue_description']}")
    except Exception as e:
        print(f"   ❌ 失败: {e}")
    
    print("\n🔍 步骤 4: 检查部门合规性 (部门ID: 1)...")
    try:
        result = cms.check_department_compliance(1)
        print(f"   ✅ 部门合规性检查成功")
        print(f"   - 部门ID: {result['department_id']}")
        print(f"   - 员工数: {result['total_employees']}")
        print(f"   - 合规率: {result['compliance_rate'] * 100:.2f}%")
        print(f"   - 问题总数: {result['issues_count']}")
    except Exception as e:
        print(f"   ❌ 失败: {e}")
    
    print("\n📝 步骤 5: 测试OCR证书信息提取...")
    try:
        ocr_engine = cms.ocr_engine
        mock_text = ocr_engine._mock_ocr("register_cert.jpg")
        ocr_result = ocr_engine.parse_certificate_info(mock_text)
        print(f"   ✅ OCR信息提取成功")
        print(f"   - 证书名称: {ocr_result.cert_name}")
        print(f"   - 证书编号: {ocr_result.cert_number}")
        print(f"   - 颁发机构: {ocr_result.issuing_authority}")
        print(f"   - 签发日期: {ocr_result.issue_date}")
        print(f"   - 有效期至: {ocr_result.expiry_date}")
        print(f"   - 置信度: {ocr_result.confidence:.2f}")
    except Exception as e:
        print(f"   ❌ 失败: {e}")
    
    print("\n📥 步骤 6: 生成批量导入模板...")
    try:
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            template_path = f.name
        
        result = cms.generate_import_template(template_path)
        print(f"   ✅ 导入模板生成成功: {result}")
        
        df = pd.read_excel(template_path)
        print(f"   - 模板列数: {len(df.columns)}")
        print(f"   - 示例数据行数: {len(df)}")
        
        os.unlink(template_path)
    except Exception as e:
        print(f"   ❌ 失败: {e}")
    
    print("\n📥 步骤 7: 测试批量导入功能...")
    try:
        test_data = [
            ["E006", "孙八", "技术部", "开发工程师", "一级建造师", "注册建造师", "JZS2024009999",
             "住房和城乡建设部", "2024-01-15", "2027-01-14", "", "test_import"],
            ["E007", "周九", "安全部", "安全主管", "安全员A证", "安全生产考核", "京建安A2024008888",
             "北京市住房和城乡建设委员会", "2024-02-20", "2027-02-19", "", "test_import"],
            ["E001", "张三", "技术部", "项目经理", "一级建造师", "注册建造师", "JZS2023001234",
             "住房和城乡建设部", "2023-03-15", "2026-03-14", "", "test_import"],
        ]
        
        columns = ["employee_no", "employee_name", "department", "position", "cert_name",
                   "cert_type", "cert_number", "issuing_authority", "issue_date", 
                   "expiry_date", "score", "source"]
        
        df_import = pd.DataFrame(test_data, columns=columns)
        
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            import_path = f.name
        
        df_import.to_excel(import_path, index=False)
        
        result = cms.import_certificates(import_path, imported_by=1)
        print(f"   ✅ 批量导入完成")
        print(f"   - 批次号: {result['batch_no']}")
        print(f"   - 总记录数: {result['total_records']}")
        print(f"   - 成功导入: {result['success_count']}")
        print(f"   - 重复记录: {result['duplicate_count']}")
        print(f"   - 错误记录: {result['error_count']}")
        
        os.unlink(import_path)
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n⏰ 步骤 8: 测试每日合规检查...")
    try:
        result = cms.run_daily_check()
        print(f"   ✅ 每日检查执行完成")
        print(f"   - 任务名称: {result['task_name']}")
        print(f"   - 执行状态: {'成功' if result['success'] else '失败'}")
        print(f"   - 执行时长: {result.get('duration_seconds', 0):.2f}秒")
        details = result.get('details', {})
        print(f"   - 创建任务数: {details.get('tasks_created', 0)}")
        print(f"   - 升级任务数: {details.get('escalated_tasks', 0)}")
        print(f"   - 培训计划数: {details.get('training_plans_created', 0)}")
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n📋 步骤 9: 查看待处理任务...")
    try:
        tasks = cms.get_pending_tasks()
        print(f"   ✅ 待处理任务获取成功")
        print(f"   - 待处理任务总数: {len(tasks)}")
        for t in tasks[:5]:
            print(f"     * [{t['priority']}] {t['title']} - {t['assignee_name']} - 截止: {t['deadline']}")
        if len(tasks) > 5:
            print(f"     ... 还有 {len(tasks) - 5} 个任务")
    except Exception as e:
        print(f"   ❌ 失败: {e}")
    
    print("\n🔍 步骤 10: 测试证书组合查询...")
    try:
        result = cms.query_certificates(only_expired=True)
        print(f"   ✅ 过期证书查询成功")
        print(f"   - 过期证书数: {result['total']}")
        for cert in result['certificates']:
            print(f"     * {cert['employee_name']} - {cert['cert_name']} - 过期于: {cert['expiry_date']}")
    except Exception as e:
        print(f"   ❌ 失败: {e}")
    
    print("\n📊 步骤 11: 测试月度报告生成...")
    try:
        result = cms.run_monthly_report()
        print(f"   ✅ 月度报告生成完成")
        print(f"   - 报告月份: {result.get('details', {}).get('report_month')}")
        print(f"   - 执行状态: {'成功' if result['success'] else '失败'}")
        if result.get('details', {}).get('excel_path'):
            print(f"   - Excel报告: {result['details']['excel_path']}")
        if result.get('details', {}).get('pdf_path'):
            print(f"   - PDF报告: {result['details']['pdf_path']}")
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n📚 步骤 12: 检查培训需求...")
    try:
        result = cms.check_training_needs()
        print(f"   ✅ 培训需求检查完成")
        print(f"   - 低合规部门数: {len(result)}")
        for dept in result:
            print(f"     * {dept['department_name']} - 连续{dept['consecutive_months']}个月低于80%")
            print(f"       当前合规率: {dept['current_rate'] * 100:.2f}%")
    except Exception as e:
        print(f"   ❌ 失败: {e}")
    
    print("\n📋 步骤 13: 查看定时任务...")
    try:
        jobs = cms.get_scheduled_jobs()
        print(f"   ✅ 定时任务列表获取成功")
        for job in jobs:
            print(f"   - [{job.get('id')}] {job.get('name')} - {job.get('schedule', job.get('next_run_time'))}")
    except Exception as e:
        print(f"   ❌ 失败: {e}")
    
    print("\n📤 步骤 14: 测试证书数据导出...")
    try:
        result = cms.export_certificates()
        print(f"   ✅ 证书数据导出成功")
        print(f"   - 导出记录数: {result['total']}")
        print(f"   - Excel文件: {result['excel_path']}")
        print(f"   - CSV文件: {result['csv_path']}")
    except Exception as e:
        print(f"   ❌ 失败: {e}")
    
    print("\n🔍 步骤 15: 测试即将到期证书查询...")
    try:
        result = cms.query_certificates(only_expiring=True)
        print(f"   ✅ 即将到期证书查询成功")
        print(f"   - 即将到期证书数: {result['total']}")
        for cert in result['certificates']:
            days = cert.get('days_to_expiry', 'N/A')
            print(f"     * {cert['employee_name']} - {cert['cert_name']} - 剩余{days}天")
    except Exception as e:
        print(f"   ❌ 失败: {e}")
    
    print("\n📝 步骤 16: 测试审计日志记录...")
    try:
        cms.audit_logger.log(
            action="system_test",
            user_id=1,
            user_name="测试管理员",
            resource_type="system",
            resource_id=None,
            details={"test_case": "audit_log_test"},
            status="success",
            sync=True,
        )
        
        logs = cms.query_engine.query_audit_logs(action="system_test")
        logs = logs[:5]
        print(f"   ✅ 审计日志测试成功")
        print(f"   - 查询到日志数: {len(logs)}")
    except Exception as e:
        print(f"   ❌ 失败: {e}")
    
    print("\n⚡ 步骤 17: 测试高并发处理...")
    try:
        processor = cms.concurrent_processor
        
        task_ids = []
        for i in range(5):
            task_id = f"test_task_{i}"
            processor.submit(
                task_id,
                lambda x: x * 2,
                i
            )
            task_ids.append(task_id)
        
        processor.wait_all()
        
        print(f"   ✅ 并发任务处理成功")
        print(f"   - 提交任务数: 5")
    except Exception as e:
        print(f"   ❌ 失败: {e}")
    
    print("\n" + "=" * 80)
    print("✅ 所有测试步骤完成!")
    print("=" * 80)
    
    print("\n📁 生成的文件:")
    for f in os.listdir(Config.REPORT_DIR):
        fpath = os.path.join(Config.REPORT_DIR, f)
        size = os.path.getsize(fpath) / 1024
        print(f"   - {f} ({size:.2f} KB)")
    
    print("\n📁 数据文件:")
    for f in os.listdir(Config.DATA_DIR):
        fpath = os.path.join(Config.DATA_DIR, f)
        size = os.path.getsize(fpath) / 1024
        print(f"   - {f} ({size:.2f} KB)")
    
    print("\n📁 日志文件:")
    for f in os.listdir(Config.LOG_DIR):
        fpath = os.path.join(Config.LOG_DIR, f)
        size = os.path.getsize(fpath) / 1024
        print(f"   - {f} ({size:.2f} KB)")
    
    return True


if __name__ == "__main__":
    success = test_system()
    sys.exit(0 if success else 1)
