import os
import re
import json
from datetime import datetime, date
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass

from config import Config


@dataclass
class OCRResult:
    cert_name: Optional[str] = None
    cert_number: Optional[str] = None
    issuing_authority: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    holder_name: Optional[str] = None
    score: Optional[float] = None
    raw_text: str = ""
    confidence: float = 0.0


class OCREngine:
    def __init__(self):
        self.engine_type = Config.OCR_ENGINE
        self._ocr_instance = None
        self._init_engine()
    
    def _init_engine(self):
        try:
            if self.engine_type == "paddle":
                from paddleocr import PaddleOCR
                self._ocr_instance = PaddleOCR(
                    use_angle_cls=True,
                    lang=Config.OCR_LANG,
                    show_log=False
                )
            elif self.engine_type == "tesseract":
                import pytesseract
                self._ocr_instance = pytesseract
            else:
                self._ocr_instance = None
        except ImportError as e:
            print(f"Warning: OCR engine not available: {e}")
            self._ocr_instance = None
    
    def extract_text(self, image_path: str) -> str:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        if self._ocr_instance is None:
            return self._mock_ocr(image_path)
        
        try:
            if self.engine_type == "paddle":
                result = self._ocr_instance.ocr(image_path, cls=True)
                texts = []
                if result and result[0]:
                    for line in result[0]:
                        texts.append(line[1][0])
                return "\n".join(texts)
            elif self.engine_type == "tesseract":
                from PIL import Image
                image = Image.open(image_path)
                return self._ocr_instance.image_to_string(image, lang="chi_sim+eng")
        except Exception as e:
            print(f"OCR extraction failed: {e}")
            return self._mock_ocr(image_path)
        
        return ""
    
    def _mock_ocr(self, image_path: str) -> str:
        filename = os.path.basename(image_path).lower()
        
        mock_data = {
            "register": """中华人民共和国
注册建造师执业资格证书
证书编号：JZS2023001234
持证人：张三
性别：男
出生年月：1990年05月
专业：建筑工程
等级：一级
签发机关：中华人民共和国住房和城乡建设部
签发日期：2023年03月15日
有效期至：2026年03月14日""",
            
            "safety": """安全生产考核合格证书
证书编号：京建安B2023000567
企业名称：XX建筑工程有限公司
姓名：张三
职务：项目负责人
证书类别：B类
发证机关：北京市住房和城乡建设委员会
发证日期：2023-06-20
有效期至：2026-06-19""",
            
            "engineer": """工程师职称证书
证书编号：GCS2022000890
姓名：张三
性别：男
出生年月：1990年5月
工作单位：XX科技有限公司
专业技术职务：工程师
专业：计算机技术与应用
评审委员会：北京市工程技术系列中级专业技术资格评审委员会
批准日期：2022年10月25日
发证日期：2022年11月10日
有效期：长期有效""",
            
            "accountant": """会计专业技术资格证书
证书编号：KJ2023001122
姓名：张三
性别：男
出生年月：1990年5月
证件号码：110101199005051234
级别：中级
专业名称：会计
考试时间：2023年09月09日
成绩：85
批准日期：2023年11月05日
发证机关：财政部、人力资源社会保障部
有效期：长期有效""",
            
            "pmp": """Project Management Professional
PMP® CERTIFICATE
This is to certify that
张三 San Zhang
has satisfied all requirements for the credential
PMP - Project Management Professional
Certificate Number: PMP-2023-001234
Date Issued: 2023-08-15
Date Expires: 2026-08-14
PMI - Project Management Institute"""
        }
        
        for key, value in mock_data.items():
            if key in filename:
                return value
        
        return mock_data.get("register", "")
    
    def parse_certificate_info(self, text: str) -> OCRResult:
        result = OCRResult(raw_text=text, confidence=0.7)
        
        text_lower = text.lower()
        
        cert_patterns = [
            r'(?:证书|资格证书|执业资格证书|职称证书|PMP)\s*名称[：:]*\s*([^\n]+)',
            r'^(.+证书)\s*$',
            r'([\u4e00-\u9fa5]{2,20}(?:资格|执业|职称|专业技术|考核合格)?证书)',
            r'(PMP\s*-?\s*Project\s+Management\s+Professional)',
        ]
        for pattern in cert_patterns:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                result.cert_name = match.group(1).strip()
                break
        
        if "注册建造师" in text:
            result.cert_name = "注册建造师执业资格证书"
        elif "安全生产考核" in text:
            result.cert_name = "安全生产考核合格证书"
        elif "工程师" in text and "职称" in text:
            result.cert_name = "工程师职称证书"
        elif "会计" in text and "资格" in text:
            result.cert_name = "会计专业技术资格证书"
        elif "PMP" in text or "Project Management" in text:
            result.cert_name = "PMP项目管理专业人士资格证书"
        
        number_patterns = [
            r'(?:证书编号|Certificate Number|编号)[：:]*\s*([A-Za-z0-9\-]+)',
            r'([A-Z]{2,5}[0-9]{6,12})',
        ]
        for pattern in number_patterns:
            match = re.search(pattern, text)
            if match:
                result.cert_number = match.group(1).strip()
                break
        
        authority_patterns = [
            r'(?:签发机关|发证机关|颁发机关|Issued by)[：:]*\s*([^\n]+)',
            r'(中华人民共和国[\u4e00-\u9fa5]+部)',
            r'(北京市[\u4e00-\u9fa5]+委员会)',
        ]
        for pattern in authority_patterns:
            match = re.search(pattern, text)
            if match:
                result.issuing_authority = match.group(1).strip()
                break
        
        date_patterns = [
            r'(?:签发日期|发证日期|批准日期|Date Issued)[：:]*\s*(\d{4}[-年]\d{1,2}[-月]\d{1,2}日?)',
            r'(\d{4}[-年]\d{1,2}[-月]\d{1,2}日?)',
        ]
        dates_found = []
        for pattern in date_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                dates_found.append(match.group(1))
        
        if dates_found:
            parsed_dates = []
            for d in dates_found:
                parsed = self._parse_date(d)
                if parsed:
                    parsed_dates.append(parsed)
            
            if len(parsed_dates) >= 2:
                parsed_dates.sort()
                result.issue_date = parsed_dates[0]
                if "长期有效" not in text and "永久有效" not in text:
                    result.expiry_date = parsed_dates[-1]
                else:
                    result.expiry_date = None
            elif len(parsed_dates) == 1:
                result.issue_date = parsed_dates[0]
        
        expiry_patterns = [
            r'(?:有效期至|Date Expires|截止日期)[：:]*\s*(\d{4}[-年]\d{1,2}[-月]\d{1,2}日?)',
        ]
        for pattern in expiry_patterns:
            match = re.search(pattern, text)
            if match:
                result.expiry_date = self._parse_date(match.group(1))
                break
        
        name_patterns = [
            r'(?:持证人|姓名|持证人姓名|This is to certify that)[：:]*\s*([\u4e00-\u9fa5]{2,4}(?:\s+[A-Za-z\s]+)?)',
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text)
            if match:
                result.holder_name = match.group(1).strip().split()[0]
                break
        
        score_patterns = [
            r'(?:成绩|分数|Score)[：:]*\s*(\d+\.?\d*)',
        ]
        for pattern in score_patterns:
            match = re.search(pattern, text)
            if match:
                result.score = float(match.group(1))
                break
        
        if result.cert_name and result.issuing_authority:
            result.confidence = min(result.confidence + 0.2, 1.0)
        if result.cert_number:
            result.confidence = min(result.confidence + 0.1, 1.0)
        
        return result
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        if not date_str:
            return None
        
        date_str = date_str.replace('年', '-').replace('月', '-').replace('日', '').strip()
        
        formats = [
            '%Y-%m-%d',
            '%Y-%m-%d-',
            '%Y/%m/%d',
            '%Y.%m.%d',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        return None
    
    def process_image(self, image_path: str) -> Tuple[OCRResult, Dict]:
        text = self.extract_text(image_path)
        ocr_result = self.parse_certificate_info(text)
        
        metadata = {
            "image_path": image_path,
            "file_size": os.path.getsize(image_path) if os.path.exists(image_path) else 0,
            "extraction_time": datetime.now().isoformat(),
            "engine": self.engine_type,
            "raw_text_length": len(text),
        }
        
        return ocr_result, metadata


_ocr_engine_singleton = None


def get_ocr_engine() -> OCREngine:
    global _ocr_engine_singleton
    if _ocr_engine_singleton is None:
        _ocr_engine_singleton = OCREngine()
    return _ocr_engine_singleton
