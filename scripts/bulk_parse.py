"""
필기 PDF 디렉토리 전체를 순회하며 해설집 파일만 파싱.
출력:
  data/out/<code>.json (회차별)
  data/questions.json  (통합)
  data/parse_report.txt (이슈 리포트)
"""
import sys, io, json, re
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent))
from parse_pdf import parse_pdf  # noqa

ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "test_list" / "전기기능사 공개문제 필기"
OUT_DIR = ROOT / "data" / "out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 해설집(정답 포함)만 사용. 학생용/교사용은 정답 표가 없어 제외.
targets = sorted([p for p in PDF_DIR.glob("*.pdf") if "해설집" in p.name])
print(f"대상: {len(targets)}개\n")

sessions = []
report = []
for pdf in targets:
    try:
        res = parse_pdf(pdf)
    except Exception as e:
        report.append(f"FAIL {pdf.name}: {e}")
        print(f"  ✗ {pdf.name}: {e}")
        continue
    code = res["session_code"]
    out = OUT_DIR / f"{code}.json"
    out.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    nq = len(res["questions"])
    ni = len(res["parse_issues"])
    sessions.append(res)
    line = f"  {'✓' if ni==0 else '!'} {code}  q={nq:2d}  issues={ni}"
    print(line)
    if ni:
        report.append(f"{code}:")
        for i in res["parse_issues"]:
            report.append(f"  - {i}")

# 통합
total_q = sum(len(s["questions"]) for s in sessions)
print(f"\n총 {len(sessions)}회차 · 문제 {total_q}개")
combined = {"sessions": sessions, "summary": {
    "session_count": len(sessions),
    "total_questions": total_q,
}}
(ROOT / "data" / "questions.json").write_text(
    json.dumps(combined, ensure_ascii=False), encoding="utf-8"
)
(ROOT / "data" / "parse_report.txt").write_text(
    "\n".join(report) if report else "(이슈 없음)", encoding="utf-8"
)
print(f"→ data/questions.json")
print(f"→ data/parse_report.txt ({len(report)} 줄)")
