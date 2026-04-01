"""生成模拟银行水单样本文件（用于测试）"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from PIL import Image, ImageDraw, ImageFont


SAMPLES_DIR = os.path.join(os.path.dirname(__file__), 'tests', 'samples')
os.makedirs(SAMPLES_DIR, exist_ok=True)


def generate_word_sample():
    """生成模拟银行水单 Word 文件"""
    doc = Document()

    # 标题
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run('中国工商银行电子回单')
    run.font.size = Pt(18)
    run.font.bold = True

    doc.add_paragraph()  # 空行

    # 回单信息表格
    table = doc.add_table(rows=8, cols=4)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    data = [
        ('回单编号', 'HD202403260001', '交易日期', '2024-03-26'),
        ('付款人', '张三丰', '付款账号', '6222021234567890123'),
        ('付款方开户行', '工商银行北京分行营业部', '币种', '人民币'),
        ('收款人', '李四光', '收款账号', '6217001234567891234'),
        ('收款方开户行', '建设银行上海分行', '交易金额', '￥50,000.00'),
        ('汇款用途', '货款支付', '手续费', '￥10.00'),
        ('摘要', '合同编号CT2024-001', '交易状态', '交易成功'),
        ('备注', '联系电话：13812345678', '', ''),
    ]

    for r_idx, row_data in enumerate(data):
        for c_idx, text in enumerate(row_data):
            cell = table.cell(r_idx, c_idx)
            cell.text = text
            # 标签列加粗灰底
            if c_idx % 2 == 0 and text:
                for para in cell.paragraphs:
                    for run in para.runs:
                        run.font.bold = True

    # 底部声明
    doc.add_paragraph()
    footer = doc.add_paragraph()
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer.add_run('此回单由系统自动生成，无需签章')
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(128, 128, 128)

    output_path = os.path.join(SAMPLES_DIR, 'sample_bank_receipt.docx')
    doc.save(output_path)
    print(f'Word 样本已生成: {output_path}')
    return output_path


def generate_excel_sample():
    """生成模拟银行水单 Excel 文件"""
    wb = Workbook()
    ws = wb.active
    ws.title = '电子回单'

    # 样式
    header_font = Font(size=16, bold=True)
    label_font = Font(bold=True)
    label_fill = PatternFill(start_color='D9E1F2', end_color='D9E1F2', fill_type='solid')
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin'),
    )

    # 标题
    ws.merge_cells('A1:D1')
    ws['A1'] = '中国建设银行电子回单'
    ws['A1'].font = header_font
    ws['A1'].alignment = Alignment(horizontal='center')

    # 数据
    data = [
        ('回单编号', 'HD202403260002', '交易日期', '2024-03-26'),
        ('付款人', '王五', '付款账号', '6227881234567890567'),
        ('付款方开户行', '建设银行广州分行', '身份证号', '440102199001011234'),
        ('收款人', '赵六', '收款账号', '6222031234567893456'),
        ('收款方开户行', '农业银行深圳分行', '交易金额', '￥100,000.00'),
        ('汇款用途', '工程款', '手续费', '￥15.00'),
        ('联系电话', '13987654321', '交易状态', '交易成功'),
    ]

    for r_idx, row_data in enumerate(data, start=3):
        for c_idx, text in enumerate(row_data, start=1):
            cell = ws.cell(row=r_idx, column=c_idx, value=text)
            cell.border = thin_border
            if c_idx % 2 == 1:  # 标签列
                cell.font = label_font
                cell.fill = label_fill
            cell.alignment = Alignment(vertical='center')

    # 调整列宽
    ws.column_dimensions['A'].width = 15
    ws.column_dimensions['B'].width = 25
    ws.column_dimensions['C'].width = 15
    ws.column_dimensions['D'].width = 25

    output_path = os.path.join(SAMPLES_DIR, 'sample_bank_receipt.xlsx')
    wb.save(output_path)
    print(f'Excel 样本已生成: {output_path}')
    return output_path


def generate_image_and_pdf_sample():
    """使用 Pillow 生成模拟图片和 PDF 水单样本"""
    width, height = 800, 600
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # 由于不同系统内置字体不同，尽量使用默认字体或不依赖外部字体文件
    # 但 PIL 默认字体极小且不支持中文，我们需要尝试加载常见中文字体
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",     # 微软雅黑
        "C:/Windows/Fonts/simhei.ttf",   # 黑体
        "C:/Windows/Fonts/simsun.ttc",   # 宋体
    ]
    
    title_font = None
    text_font = None
    
    for path in font_paths:
        if os.path.exists(path):
            title_font = ImageFont.truetype(path, 32)
            text_font = ImageFont.truetype(path, 20)
            break
            
    if not title_font:
        # 如果找不到中文字体，只能回退（但这在 Windows 上极少发生）
        title_font = ImageFont.load_default()
        text_font = ImageFont.load_default()

    # 绘制标题
    draw.text((300, 30), "招商银行电子回单", font=title_font, fill='black')
    
    # 绘制外框
    draw.rectangle([50, 100, 750, 500], outline='black', width=2)
    
    # 绘制表格线
    draw.line([50, 150, 750, 150], fill='black', width=1)
    draw.line([50, 200, 750, 200], fill='black', width=1)
    draw.line([50, 250, 750, 250], fill='black', width=1)
    draw.line([50, 300, 750, 300], fill='black', width=1)
    draw.line([50, 400, 750, 400], fill='black', width=1)
    
    draw.line([200, 100, 200, 500], fill='black', width=1)
    draw.line([400, 100, 400, 300], fill='black', width=1)
    draw.line([550, 100, 550, 300], fill='black', width=1)
    
    # 数据内容
    texts = [
        # 行 1
        ((60, 115), "回单编号"), ((210, 115), "HD202403260003"), 
        ((410, 115), "交易日期"), ((560, 115), "2024-03-26"),
        # 行 2
        ((60, 165), "付款人"), ((210, 165), "孙七"), 
        ((410, 165), "付款账号"), ((560, 165), "6214831234567890"),
        # 行 3
        ((60, 215), "付款方开户行"), ((210, 215), "招商银行杭州分行"), 
        ((410, 215), "金额"), ((560, 215), "￥88,888.00"),
        # 行 4
        ((60, 265), "收款人"), ((210, 265), "周八"), 
        ((410, 265), "收款账号"), ((560, 265), "6222021234567899999"),
        # 行 5 (大格)
        ((60, 335), "汇款用途"), ((210, 335), "采购款项支付"),
        # 行 6 (大格)
        ((60, 435), "备注信息"), ((210, 435), "联系手机：13799998888  身份：440106198808081234")
    ]
    
    for pos, text in texts:
        draw.text(pos, text, font=text_font, fill='black')
        
    # 保存为 PNG
    png_path = os.path.join(SAMPLES_DIR, 'sample_bank_receipt.png')
    img.save(png_path)
    print(f'图片样本已生成: {png_path}')
    
    # 保存为 PDF
    pdf_path = os.path.join(SAMPLES_DIR, 'sample_bank_receipt.pdf')
    img.save(pdf_path, "PDF", resolution=100.0)
    print(f'PDF 样本已生成: {pdf_path}')


if __name__ == '__main__':
    generate_word_sample()
    generate_excel_sample()
    generate_image_and_pdf_sample()
    print('\n所有样本文件已生成完毕！')
