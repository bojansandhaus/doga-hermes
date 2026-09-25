# Changelog

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
