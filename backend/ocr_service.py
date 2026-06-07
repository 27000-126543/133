import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ocr_engine import OCREngine, get_ocr_engine


class OCRService:
    def __init__(self):
        self.engine = get_ocr_engine()
    
    def is_paddle_available(self) -> bool:
        return self.engine._ocr_instance is not None and self.engine.engine_type == "paddle"
    
    def process_image(self, image_path: str):
        return self.engine.process_image(image_path)
    
    def parse_text(self, text: str):
        return self.engine.parse_certificate_info(text)
    
    def extract_text(self, image_path: str):
        return self.engine.extract_text(image_path)


_ocr_service_singleton = None


def get_ocr_service() -> OCRService:
    global _ocr_service_singleton
    if _ocr_service_singleton is None:
        _ocr_service_singleton = OCRService()
    return _ocr_service_singleton


def install_paddleocr():
    import subprocess
    import sys
    
    print("Installing PaddleOCR...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            "paddleocr>=2.7.0", "paddlepaddle>=2.5.0"
        ])
        print("PaddleOCR installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install PaddleOCR: {e}")
        print("Falling back to mock OCR mode")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="OCR Service")
    parser.add_argument("--install", action="store_true", help="Install PaddleOCR")
    parser.add_argument("--test", type=str, help="Test OCR with an image file")
    
    args = parser.parse_args()
    
    if args.install:
        install_paddleocr()
    
    if args.test:
        service = get_ocr_service()
        print(f"PaddleOCR available: {service.is_paddle_available()}")
        
        ocr_result, metadata = service.process_image(args.test)
        print("\nOCR Result:")
        print(f"  Certificate Name: {ocr_result.cert_name}")
        print(f"  Certificate Number: {ocr_result.cert_number}")
        print(f"  Issuing Authority: {ocr_result.issuing_authority}")
        print(f"  Issue Date: {ocr_result.issue_date}")
        print(f"  Expiry Date: {ocr_result.expiry_date}")
        print(f"  Holder Name: {ocr_result.holder_name}")
        print(f"  Score: {ocr_result.score}")
        print(f"  Confidence: {ocr_result.confidence:.2f}")
