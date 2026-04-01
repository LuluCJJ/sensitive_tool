import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.redactor import Redactor

def test_integration():
    print("开始集成功能测试...")
    redactor = Redactor()
    
    samples_dir = os.path.join(os.path.dirname(__file__), 'tests', 'samples')
    word_sample = os.path.join(samples_dir, 'sample_bank_receipt.docx')
    excel_sample = os.path.join(samples_dir, 'sample_bank_receipt.xlsx')
    image_sample = os.path.join(samples_dir, 'sample_bank_receipt.png')
    pdf_sample = os.path.join(samples_dir, 'sample_bank_receipt.pdf')
    
    # 验证样本文件存在
    samples = [word_sample, excel_sample, image_sample, pdf_sample]
    if not all(os.path.exists(f) for f in samples):
        print("错误：样本文件缺失！请先运行 generate_samples.py")
        sys.exit(1)
        
    def progress_callback(current, total, text):
        print(f"[{current}/{total}] {text}")
        
    def file_callback(log):
        if log.status == 'success':
            print(f"成功: {log.filename} -> {log.output_path} (脱敏处: {log.redaction_count})")
            for entry in log.entries:
                print(f"  - [{entry.rule_name}] '{entry.original_text}' @ {entry.location}")
        else:
            print(f"失败: {log.filename} - {log.error_message}")
            if hasattr(log, 'traceback') and log.traceback:
                print(log.traceback)
            # 有时错误可能是字符串形式的异常，记录在 error_message 里

    print("测试处理 Word, Excel, 图片和 PDF...")
    logs = redactor.process_files(samples, progress_callback, file_callback)
    
    success_count = sum(1 for log in logs if log.status == 'success')
    if success_count == len(logs):
        print("\n集成测试通过！所有文件处理成功。")
    else:
        print("\n集成测试失败！有文件未能成功处理。")
        sys.exit(1)

if __name__ == '__main__':
    test_integration()
