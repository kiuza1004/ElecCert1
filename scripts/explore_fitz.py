"""
PyMuPDF로 한국어 PDF에서 column별 텍스트 추출 가능 여부 확인.
"""
import sys, io, fitz
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "test_list" / "전기기능사 공개문제 필기" / "전기기능사20160710(해설집).pdf"

doc = fitz.open(str(PDF))
print(f"pages: {doc.page_count}")
page = doc[0]
print(f"page1 size: {page.rect}")

# 좌측 절반(0~page.rect.width/2)
mid = page.rect.width / 2
left_clip = fitz.Rect(0, 0, mid, page.rect.height)
right_clip = fitz.Rect(mid, 0, page.rect.width, page.rect.height)

left_text = page.get_text("text", clip=left_clip)
right_text = page.get_text("text", clip=right_clip)

print("\n=== LEFT ===")
print(left_text[:1500])
print("\n=== RIGHT ===")
print(right_text[:1500])
