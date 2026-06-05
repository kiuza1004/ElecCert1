# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**VoltPass** — single-file web app for Korean Electrical Engineer Certification (전기기능사) CBT 필기 mock exams. Live at https://github.com/kiuza1004/ElecCert1.

## Run / Deploy

No build step. Open `index.html` directly in a browser, or serve statically (`python -m http.server`, GitHub Pages, etc.). Tailwind and Pretendard load from CDN. There is no test suite, no linter, no package manager.

## Architecture

Everything lives in `index.html` (~1430 lines), organized as numbered sections inside one `<script>` block:

- `[1]` `QUESTIONS` — master question pool. 25 per subject × 3 subjects (`1=전기이론`, `2=전기기기`, `3=전기설비`). Question IDs follow `<subject><index>` (e.g. `3111`).
- `[2]` `STUDY_NOTES` — subject notes keyed `1`/`2`/`3` for written exam, key `9` reserved for 실기 reference content.
- `[3]` State + LocalStorage under `STORAGE_KEY = 'voltpass_cbt_v2'`. `toggleWrong(id, force)` accepts `true`/`false`/`undefined` for set/remove/toggle.
- `[4]` `mulberry32` seeded PRNG + `buildRound(round)`: deterministic 60-question paper per round using `seedBase = round * 7919 + 13`. **Bump the seed formula and `STORAGE_KEY` together if you change paper composition** — saved rounds reference stored `ids` arrays, so existing localStorage stays compatible.
- `[6]` `navigate(view)` + `render()` switch: views are `home | setup | exam | result | notes | note | wrong`. Single global `timerHandle` is cleared on every navigation.
- `[7]`–`[8]` Exam flow: `renderHome` → `renderSetup` (mode picker, **immutable after start**) → `renderExam` → `renderResult`. `renderSetup` redirects to `exam` if the round already exists; `renderExam` redirects to `setup` if not. This indirect routing is how "다시 응시" (delete record → navigate exam) resets a round.
- `[9]`–`[11]` Result/review/wrong-note rendering.

## State shape

```js
state = {
  rounds: { [round]: {
    ids, answers, flags, cursor, startedAt, durationSec,
    countdownThreshold,  // null = normal, 10|20|30|40|50 = countdown alert seconds
    finished, score, passed, correct, subjectCorrect, subjectTotal, finishedAt, autoSubmitted
  }},
  wrongIds: [],
  activeRound: null
}
```

## Timer & countdown

- One `setInterval` (`timerHandle`), 1-second tick, set in `attachTimer()` inside `renderExam`.
- Total timer is `startedAt + durationSec` (durable across reloads).
- Per-question timer uses **in-memory** `questionEnteredAt` — resets on every `enterQuestion()` call (including reload, prev/next, flag toggle). This is intentional: re-entering a question grants a fresh 60s.
- Countdown mode triggers when `qLeft <= countdownThreshold`: adds `body.countdown-active` (edge pulse) / `countdown-critical` (last 5s), shows `#countdown-overlay` (positioned **bottom-right** to avoid blocking the question), fires `navigator.vibrate`.
- At `qElapsed >= 60`, `autoAdvance()` moves to next question. **Q60 is exempt**: it never auto-submits — termination only via manual submit button or 60-min total expiry.
- `deactivateCountdown()` is the single cleanup point — call it from any new exit path.

## Conventions

- All user-facing strings are Korean; keep that consistent.
- All user-supplied or question text rendered via `escapeHtml()`; `STUDY_NOTES` bodies are trusted raw HTML (use `formula` class for inline equations).
- Korean Electrical Engineer cert moved to **KEC (한국전기설비규정)** in 2021. When adding/editing 3과목 questions, use current KEC values, not the deprecated 내선규정 (e.g., 절연저항 1.0MΩ for FELV ≤500V — not 0.2MΩ).
- Adding questions: append to `QUESTIONS`, keep 25-per-subject balance or update the `slice(0,20)` logic in `buildRound`.
- Schema-breaking changes to round records: bump `STORAGE_KEY` (e.g. `_v3`) so old saves don't crash `renderExam`.
