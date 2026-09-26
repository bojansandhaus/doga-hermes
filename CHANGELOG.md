# Changelog

## v1.2.0 (2026-09-26)

### Added
- Optional local Laya classifier for the existing five-facet DOGA response contract. Select it for the current process with `/doga provider laya`, or start Hermes with `DOGA_DECISION_PROVIDER=laya` for a persistent choice. Jev remains the default.
- Explicit opt-in Jev fallback when local Laya errors. Use `/doga fallback on` for this process or `DOGA_LAYA_JEV_FALLBACK=1` at process startup. Jev then tries OpenRouter first and direct TypeSafe if necessary. With fallback off, a local error never sends the request remotely.
- `laya` optional Python dependency group. The model loads once per process and its predictions are serialized to prevent concurrent model calls.

### Changed
- The selected classifier now supplies typed judgments to the same contract builder and ambiguity handling. `/doga jev on|off` continues to toggle response contracts for backward compatibility, including when Laya is selected.
- Healthy local Laya never calls Jev. If Laya errors, DOGA either tries Jev when explicitly opted in or retains ordinary guidance without a typed contract. A failed Jev fallback also retains ordinary guidance.

### Limitations
- The first local load can download model weights from Hugging Face. Cache them before requiring offline operation. The main Hermes model and other plugins have separate network behavior.
- Laya's classification accuracy and its ambiguity probability on DOGA's questions are not calibrated against Jev; the shared 0.7 threshold is a starting behavior, not a validated decision threshold.
- A local checkpoint smoke test emitted a Laya runtime warning about invalid saved choice temperatures; Laya clamped them. Treat affected confidence values as uncalibrated until the checkpoint is recalibrated.

### Verification
- Full local suite: 144 passed. Wheel and source distribution built.
- With the Laya checkpoint cached and `HF_HUB_OFFLINE=1`, a local five-facet prediction and a Hermes `pre_llm_call` hook both returned a contract without invoking Jev's provider path.

---

## v1.1.1 (2026-09-25)

### Fixed
- Preserve Jev's high ambiguity signal when its selected response mode is not `clarify`. DOGA now requires a conditional answer that states material assumptions and identifies missing information that could change the answer.
- Keep the focused clarification path when Jev selects `clarify` and the ambiguity score is at least 0.7.
- Correct setuptools' build backend and package discovery so the DOGA Python distribution builds without treating the `assets` directory as a package.

### Tests
- Add regression coverage for the conflicting `recommend` plus high ambiguity result, explicit clarification, and low ambiguity recommendation.

### Verification
- Full test suite: 133 passed.
- Python compilation, version consistency, and `git diff --check` passed.
- Wheel build passed.

---

## v1.1.0 (2026-05-24)

### Features
- De Bono Six Thinking Hats — 5 structured thinking lenses, depth-aware
- Recursive reasoning via `reason_deeper` tool with per-level hat rotation
- Hard-break safety mechanism — 3 ignored stop signals terminate the tool loop
- Auto depth — complexity-based depth selection (pure Python, 0 LLM tokens)
- Mnemosyne memory integration (optional, `pip install doga-hermes[memory]`)
- Content swallowing prevention — unclosed `<world_model>` tags no longer hide content

### Fixes
- `ast.Load` missing from AST whitelist — ALL condition expressions silently returned False
- `_default_engine` thread safety — fresh `MonteCarloEngine` per call
- Double-checked locking removed — always-lock pattern for `_ConditionCache`
- `RecursionError` catch in `_compile` — deep nested parentheses no longer crash
- `_simulate_tool_handler` now respects `_stop_sent` — simulate bypass vector closed
- `assess_complexity` type guard — non-string input safely returns `"low"`
- Test state contamination — `setup_method` → `@pytest.fixture(autouse=True)`

### Chores
- Repo restructured: source files moved into `doga/` subdirectory
- `plugin.yaml` added (Hermes best practice)
- 116 tests across 7 modules, 0 failures
- CI workflow added (GitHub Actions, Python 3.10–3.12)

---

## v1.0.0 (2026-05-22)

Initial release.
- Plugin registration with 3 Hermes hooks
- Monte Carlo simulation engine with AST whitelist safety
- Goal detection (Information / Understanding / Action)
- Thinking panel formatting
- `/doga` slash commands
