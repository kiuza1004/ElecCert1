"""
classified JSON → 앱 임베드용 JS 파일 생성.
출력: data/questions.js  (window.EXAM_QUESTIONS = [...], window.EXAM_SESSIONS = [...])
"""
import sys, io, json
from collections import defaultdict
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "questions_classified.json"
OUT = ROOT / "data" / "questions.js"

d = json.loads(SRC.read_text(encoding="utf-8"))
qs = d["questions"]

# 앱이 쓰는 최소 필드만 보존 (score 제거)
trimmed = []
for q in qs:
    trimmed.append({
        "id": q["id"],
        "code": q["session_code"],
        "label": q["session_label"],
        "year": q["year"],
        "qNum": q["qNum"],
        "subject": q["subject"],
        "question": q["question"],
        "options": q["options"],
        "answer": q["answer"],
        "level": q["level"],
    })

# 회차 메타 (UI에서 연도별 메뉴 구성용)
sess_map = defaultdict(lambda: {"qCount": 0})
for q in trimmed:
    s = sess_map[q["code"]]
    s["code"] = q["code"]
    s["label"] = q["label"]
    s["year"] = q["year"]
    s["qCount"] += 1
sessions = sorted(sess_map.values(), key=lambda x: x["code"], reverse=True)

# JS 파일 작성
header = (
    "// Auto-generated. 전기기능사 공개문제(2006~2016) — Q-net 공개 데이터 기반.\n"
    "// 해설은 저작권 보호를 위해 제외됨.\n"
)
content = (
    header +
    "window.EXAM_QUESTIONS = " + json.dumps(trimmed, ensure_ascii=False, separators=(",", ":")) + ";\n" +
    "window.EXAM_SESSIONS = "  + json.dumps(sessions, ensure_ascii=False, separators=(",", ":")) + ";\n"
)
OUT.write_text(content, encoding="utf-8")

# 통계
from collections import Counter
lvl_cnt = Counter(q["level"] for q in trimmed)
print(f"문항: {len(trimmed)}")
print(f"회차: {len(sessions)}")
print(f"레벨: {dict(lvl_cnt)}")
print(f"→ {OUT.relative_to(ROOT)} ({OUT.stat().st_size//1024} KB)")
