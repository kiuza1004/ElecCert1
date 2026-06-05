"""
PDF 구조 탐색: 한 페이지의 column 분리 + 답안 표 위치 확인.
"""
import pdfplumber, sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "test_list" / "전기기능사 공개문제 필기" / "전기기능사20160710(해설집).pdf"

with pdfplumber.open(str(PDF)) as pdf:
    print(f"page count: {len(pdf.pages)}")
    for i, page in enumerate(pdf.pages[:2]):
        print(f"\n=== page {i+1} (w={page.width:.0f}, h={page.height:.0f}) ===")
        words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
        xs = sorted({round(w["x0"]) for w in words})
        print(f"  unique x0 buckets (first 30): {xs[:30]}")
        # left-col / right-col 추정: x0 분포 히스토그램
        from collections import Counter
        c = Counter(round(w["x0"]/10)*10 for w in words)
        print(f"  x0 histogram (top 10): {c.most_common(10)}")
    print("\n=== last page (answer key) ===")
    last = pdf.pages[-1]
    text = last.extract_text(x_tolerance=2)
    print(text[-800:] if text else "(no text)")
