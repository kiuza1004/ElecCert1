"""
2277문항(사용 가능)을 난이도 초/중/고로 분류.
출력: data/questions_classified.json
"""
import sys, io, json, re
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "questions.json"
OUT = ROOT / "data" / "questions_classified.json"

UNITS_RE = re.compile(r"(\d+\s*)?(V|A|Ω|W|Hz|μ|π|kW|kV|kHz|mA|mm|cm|m\^|rad|deg|°|kVA|MVA)")
OPT_MATH_RE = re.compile(r"(×\s*10|√|\\frac|\^|10\^|\bπ\b|sin|cos|tan)")
CALC_KW = ("구하시오", "얼마인가", "몇 ", "값은", "이라고 하면")
RECALL_KW = ("옳은 것은", "다음 중", "틀린 것은", "명칭", "약호", "기호", "잘못된 것은", "맞는 것은", "어떤 것")
ANALYSIS_KW = ("회로", "위상", "벡터", "임피던스", "역률", "리액턴스", "유도", "정전용량",
               "정류기", "변압기", "유도전동기", "동기전동기", "발전기")


def score_question(q):
    text = q["question"] or ""
    opts = q["options"] or []
    s = 0
    if UNITS_RE.search(text):
        s += 1
    if any(OPT_MATH_RE.search(o) for o in opts):
        s += 2
    if any(k in text for k in CALC_KW):
        s += 1
    if any(k in text for k in ANALYSIS_KW):
        s += 1
    if any(k in text for k in RECALL_KW):
        s -= 1
    if opts:
        avg_len = sum(len(o) for o in opts) / len(opts)
        if avg_len <= 6:
            s -= 1
    return s


def label_from_score(s):
    if s <= 0: return "beginner"
    if s <= 2: return "intermediate"
    return "advanced"


def main():
    d = json.loads(SRC.read_text(encoding="utf-8"))
    enriched = []
    for s in d["sessions"]:
        sess_meta = {"year": s["year"], "session_code": s["session_code"],
                     "session_label": s["session_label"]}
        for q in s["questions"]:
            # 사용 가능한 문항만
            if (len(q["options"]) != 4
                or not all((o or "").strip() for o in q["options"])
                or not q["question"].strip()
                or not q["answer"]):
                continue
            sc = score_question(q)
            enriched.append({
                **sess_meta,
                "qNum": q["qNum"],
                "subject": q["subject"],
                "question": q["question"],
                "options": q["options"],
                "answer": q["answer"],
                "score": sc,
                "level": label_from_score(sc),
            })
    # 균형 보정: 각 레벨이 너무 적으면 인접 점수에서 재분배
    from collections import Counter
    cnt = Counter(q["level"] for q in enriched)
    print(f"초기 분포: {dict(cnt)}")
    # 점수 분포 히스토그램
    score_hist = Counter(q["score"] for q in enriched)
    print(f"점수 히스토그램: {sorted(score_hist.items())}")

    # 33%씩 맞도록 점수 컷오프 재계산
    sorted_qs = sorted(enriched, key=lambda x: x["score"])
    n = len(sorted_qs)
    t1 = n // 3
    t2 = (n * 2) // 3
    s_easy_max = sorted_qs[t1 - 1]["score"] if t1 else 0
    s_mid_max = sorted_qs[t2 - 1]["score"] if t2 else 0
    print(f"균형 컷오프: ≤{s_easy_max}=초급, ≤{s_mid_max}=중급, >{s_mid_max}=고급")
    for q in enriched:
        if q["score"] <= s_easy_max:
            q["level"] = "beginner"
        elif q["score"] <= s_mid_max:
            q["level"] = "intermediate"
        else:
            q["level"] = "advanced"
    cnt2 = Counter(q["level"] for q in enriched)
    print(f"균형 후 분포: {dict(cnt2)}")

    # 안정 ID 부여 (year+session+qNum)
    for q in enriched:
        q["id"] = f"{q['session_code']}-{q['qNum']:02d}"
        # score는 디버깅용으로만 보관 (앱 빌드 시 제거)

    OUT.write_text(json.dumps({"questions": enriched}, ensure_ascii=False),
                   encoding="utf-8")
    print(f"\n→ {OUT.relative_to(ROOT)} ({len(enriched)}문항)")


if __name__ == "__main__":
    main()
