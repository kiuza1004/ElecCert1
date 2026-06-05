"""
전기기능사 해설집 PDF → 구조화 JSON 추출.

원칙 (저작권):
  - 추출: 문제 본문 + 선택지 4개 + 정답 (= Q-net 공개문제, 저작권 OK)
  - 제외: <문제 해설> 이하 해설 내용 (= comcbt.com 저작권)

출력 스키마:
  {
    "year": 2016, "session_code": "20160710",
    "session_label": "2016년 7월 10일",
    "questions": [
      {"qNum": 1, "subject": 1, "question": "...",
       "options": ["...","...","...","..."], "answer": 3}
    ],
    "parse_issues": ["q42 옵션 3개만 발견" ...]
  }
"""
import sys, io, re, json, fitz, argparse
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

OPTION_MARKS = ["①", "②", "③", "④"]
ANSWER_MAP = {"①":1, "②":2, "③":3, "④":4}
SUBJECT_FROM_QNUM = lambda n: 1 if n<=20 else (2 if n<=40 else 3)


def extract_full_text(pdf_path: Path) -> str:
    """페이지마다 좌측→우측 column 순으로 텍스트 결합."""
    doc = fitz.open(str(pdf_path))
    out = []
    for page in doc:
        mid = page.rect.width / 2
        left  = page.get_text("text", clip=fitz.Rect(0, 0, mid, page.rect.height))
        right = page.get_text("text", clip=fitz.Rect(mid, 0, page.rect.width, page.rect.height))
        out.append(left)
        out.append(right)
    doc.close()
    return "\n".join(out)


def parse_answer_key(text: str) -> dict:
    """
    마지막 페이지 정답표:
      1 2 3 4 5 6 7 8 9 10
      ③②③①①④③③④②
    """
    result = {}
    # 패턴: 숫자 줄(공백 구분) + 다음 줄에 4가지 마크가 10개
    pattern = re.compile(
        r"(\d+(?:\s+\d+){9})\s*\n\s*([①②③④\s]{10,30})"
    )
    for m in pattern.finditer(text):
        nums = [int(x) for x in m.group(1).split()]
        marks = [c for c in m.group(2) if c in ANSWER_MAP]
        if len(nums) == len(marks) == 10:
            for n, mk in zip(nums, marks):
                result[n] = ANSWER_MAP[mk]
    return result


# 문제 본문 시작: "1." ~ "60." 패턴 (라인 시작, 본문은 빈 줄 허용 — 공식·기호 시작 케이스 대응)
Q_HEADER = re.compile(r"^\s*(\d{1,2})\.\s*(.*)$")
# 옵션 줄: "① text" 또는 "①text"
OPT_LINE = re.compile(r"^\s*([①②③④])\s*(.*)$")
EXPL_MARK = "<문제 해설>"


def parse_questions(text: str, answer_key: dict):
    """
    텍스트를 문항 단위로 분리.
    - 본문은 q_header 이후 ~ 첫 옵션 직전까지
    - 옵션 4개 수집
    - <문제 해설> 만나면 해당 문항 종료
    """
    lines = text.split("\n")
    questions = []
    issues = []
    cur = None  # 현재 수집 중인 문항 dict
    mode = "idle"  # idle | q_body | options | drop_until_next

    def finalize(q):
        if not q:
            return
        # 옵션 4개 채워졌는지 확인
        if len(q["options"]) < 4:
            issues.append(f"q{q['qNum']}: 옵션 {len(q['options'])}개만 발견")
        else:
            q["options"] = q["options"][:4]
        # 본문 정리
        q["question"] = re.sub(r"\s+", " ", q["question"]).strip()
        q["options"] = [re.sub(r"\s+", " ", o).strip() for o in q["options"]]
        q["answer"] = answer_key.get(q["qNum"])
        if q["answer"] is None:
            issues.append(f"q{q['qNum']}: 정답 미발견")
        q["subject"] = SUBJECT_FROM_QNUM(q["qNum"])
        questions.append(q)

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            continue
        # 페이지 푸터/헤더 등 잡음 제외
        stripped = line.strip()
        if line.startswith("◐") or "www.comcbt.com" in line or "전자문제집 CBT" in line:
            continue
        if "기출문제 해설은" in line or "본 해설집" in line:
            continue
        # 푸터/헤더 연속 라인 필터
        FOOTER_PHRASES = (
            "의해서 만들어진 자료", "감사 드립니다", "기출문제 및 해설집",
            "오답 및 오탈자", "본 해설집의 저작권", "DB 저장", "이미지 찾아",
            "다운로드 :", "구글플레이", "전자문제집 CBT란", "인터넷으로 종이",
            "오답 노트", "교사용/학생용", "기타 금전적", "PC 버전",
        )
        if any(ph in line for ph in FOOTER_PHRASES):
            continue
        if re.match(r"^[1-3]\s*과목\s*[:：]", stripped):
            continue
        if stripped.startswith("전기기능사") and ("필기" in stripped or "기출" in stripped or len(stripped) < 12):
            continue
        if line.startswith("[해설작성자") or line.startswith("[참고") or line.startswith("[해설추가") \
                or line.startswith("[오류") or line.startswith("[본") or line.startswith("[플레밍"):
            continue
        if stripped in ("<문제 해설>", ""):
            pass  # <문제 해설>은 아래에서 별도 처리

        m_hdr = Q_HEADER.match(line)
        if m_hdr:
            qn = int(m_hdr.group(1))
            # 신규 헤더 조건: 1~60 범위 + 직전 번호 + 1 (해설 본문의 "1.", "2." 오인 방지)
            # cur가 None이면 무조건 q1 또는 시작 번호 허용
            is_next = cur is None or qn == cur["qNum"] + 1
            if 1 <= qn <= 60 and is_next:
                finalize(cur)
                cur = {"qNum": qn, "question": m_hdr.group(2) or "",
                       "options": [], "subject": None, "answer": None}
                mode = "q_body"
                continue

        # 옵션 마커 시작
        m_opt = OPT_LINE.match(line)
        if m_opt and cur is not None:
            cur["options"].append(m_opt.group(2))
            mode = "options"
            continue

        # 해설 시작 → 본 문항 수집 종료 (다음 문항 헤더까지 drop)
        if line.strip() == EXPL_MARK and cur is not None:
            mode = "drop_until_next"
            continue

        if mode == "q_body" and cur is not None:
            # 다음 줄이 문제 본문의 연속
            cur["question"] += " " + line.strip()
        elif mode == "options" and cur is not None and cur["options"]:
            # 옵션 텍스트가 다음 줄로 줄바꿈된 경우 → 마지막 옵션에 이어붙임
            # 단, 다음 옵션 마커가 아닐 때만
            cur["options"][-1] += " " + line.strip()
        # mode == "drop_until_next" → 무시

    finalize(cur)
    return questions, issues


def parse_pdf(pdf_path: Path) -> dict:
    fname = pdf_path.stem  # e.g. "전기기능사20160710(해설집)"
    m = re.search(r"(\d{8})", fname)
    code = m.group(1) if m else "unknown"
    year = int(code[:4]) if code != "unknown" else None
    text = extract_full_text(pdf_path)
    ans = parse_answer_key(text)
    qs, issues = parse_questions(text, ans)
    if len(ans) != 60:
        issues.insert(0, f"정답표 {len(ans)}/60개 추출")
    if len(qs) != 60:
        issues.insert(0, f"문제 {len(qs)}/60개 추출")
    return {
        "year": year,
        "session_code": code,
        "session_label": f"{code[:4]}년 {int(code[4:6])}월 {int(code[6:8])}일",
        "questions": qs,
        "parse_issues": issues,
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", help="해설집 PDF 경로")
    ap.add_argument("--out", help="JSON 출력 경로 (생략 시 stdout)")
    args = ap.parse_args()

    result = parse_pdf(Path(args.pdf))
    data = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(data, encoding="utf-8")
        print(f"→ {args.out} ({len(result['questions'])} questions, "
              f"{len(result['parse_issues'])} issues)")
        for i in result["parse_issues"][:10]:
            print(f"  ! {i}")
    else:
        print(data)
