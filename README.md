# DOGA with Jev for Hermes

[![MIT License](https://img.shields.io/github/license/bojansandhaus/doga-hermes)](https://github.com/bojansandhaus/doga-hermes/blob/main/LICENSE)
[![Python 3.10 | 3.11 | 3.12](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://github.com/bojansandhaus/doga-hermes)
[![Last Commit](https://img.shields.io/github/last-commit/bojansandhaus/doga-hermes)](https://github.com/bojansandhaus/doga-hermes)

![DOGA](assets/DOGA.png)

**Probabilistic, goal-aware thinking layer for Hermes Agent.**

Built by [@0z1-ghb](https://github.com/0z1-ghb). This independent fork makes an adjustment to DOGA by adding Jev response contracts and OpenRouter primary routing with direct TypeSafe fallback.

DOGA (Doğa, Turkish for “nature”) adds scenario simulation, Monte Carlo reasoning, and goal detection to Hermes responses. It remains a plugin and does not modify Hermes core.

---

## Features

- **Goal Detection**  Identifies whether the user needs Information, Understanding, or Action before responding
- **Jev Response Contract**  Enabled by default. Jev classifies the user's goal, response mode, stakes, need for clarification, and scenario analysis. DOGA turns that assessment into answer requirements for the main model. OpenRouter is primary, with direct TypeSafe as fallback.
- **Scenario Generation**  Prompts the LLM to enumerate and weigh multiple interpretations
- **Monte Carlo Simulation**  Pure Python engine (10,000 to 50,000 iterations) for quantitative probability analysis, using 0 LLM tokens
- **Thinking Panel**  `<world_model>` reasoning blocks are extracted and displayed as a structured `[DOGA: Thinking Process]` panel before the final response
- **Auto Depth**  Automatic complexity assessment per query. It selects low, medium, or high using pure Python string analysis (0 LLM tokens)
- **Configurable Depth**  5 levels (1 = lightweight goal check, 5 = full probabilistic reasoning with simulation tool guidance)
- **Memory Integration (optional)**  Remembers goal patterns across sessions via Mnemosyne (`pip install doga-hermes[memory]`)
- **De Bono Thinking Hats**  Structured parallel reasoning through Six Thinking Hats lenses, depth aware (White, Black, Yellow, Green, Red), optional, enabled by default
- **Recursive Reasoning**  `reason_deeper` tool for multi-level self-critique; each recursion level uses a different De Bono hat lens; hierarchical panel output
- **Hard-Break Safety**  Automatic stop after 3 ignored `reason_deeper` calls prevents tool-loop starvation

---

## Installation

Copy the `doga/` directory into your Hermes plugins folder:

```bash
cp -r doga ~/.hermes/plugins/doga
```

For goal memory persistence across sessions (optional):

```bash
pip install doga-hermes[memory]
```

No configuration changes are needed. DOGA detects Mnemosyne at runtime.

### Jev setup

Jev response contracts are on by default. For live Jev assessments, make `OPENROUTER_API_KEY` available to the Hermes process. To enable TypeSafe failover, also provide `TYPESAFE_API_KEY`. DOGA reads keys from the process environment, not DOGA configuration or model prompts. Without either key, the Jev request cannot be evaluated and DOGA continues with its standard guidance.

DOGA sends the user's request to Jev through OpenRouter first, using model `typesafe/jev-1.13` at `https://openrouter.ai/api/alpha/decisions`. If that key is missing or the request fails, DOGA tries TypeSafe directly, using model `jev-latest` at `https://api.typesafe.ai/v1/systemone`. If only `TYPESAFE_API_KEY` is set, DOGA uses the direct TypeSafe route. If both calls fail, DOGA continues with its standard guidance. `JEV_PROVIDER_MODE` configures the separate `jev-decisions` Hermes plugin and does not control DOGA's provider route.

Enable the DOGA plugin in `~/.hermes/config.yaml`:

```yaml
plugins:
  enabled: [doga]

toolsets: [hermes-cli, doga]

doga:
  depth: 3
  show_simulation: true
  max_scenarios: 5
```

---

## Usage

### Slash Commands

| Command | Description |
|---------|-------------|
| `/doga on` | Enable DOGA |
| `/doga off` | Disable DOGA |
| `/doga status` | Show current settings |
| `/doga auto` | Automatic depth, selects low, medium, or high per query (default) |
| `/doga manual high` | Example: force high thinking depth. Use `low`, `medium`, or `high` |
| `/doga depth 4` | Example: set thinking depth to 4, from 1 to 5 |
| `/doga hats on` | Enable De Bono parallel thinking hats (default) |
| `/doga hats off` | Disable De Bono hats (reverts to standard goal/scenario prompts) |
| `/doga show` | Show simulation panel |
| `/doga hide` | Hide simulation panel |
| `/doga memory on` | Enable goal memory (requires Mnemosyne) |
| `/doga memory off` | Disable goal memory |
| `/doga jev off` | Disable Jev response contracts, which are on by default |
| `/doga jev on` | Re-enable Jev response contracts after turning them off |
| `/doga max_recursion 3` | Example: set maximum `reason_deeper` depth from 1 to 5 |

### Jev Response Contract

Jev is a typed decision model used here as a request classifier. It is enabled by default. For each user request, DOGA asks Jev for one structured assessment of five facets:

1. **Goal:** information, understanding, or action.
2. **Response mode:** answer, explain, recommend, or clarify.
3. **Stakes:** low, medium, or high.
4. **Clarification:** whether a missing fact materially changes the useful answer.
5. **Scenario need:** none, compare options, or analyze explicit uncertainty.

DOGA maps those judgments into a compact response contract. For example, an action request can require a recommendation and next step. High stakes add a request to address material risks and uncertainty. A clarification question is requested only when Jev selects clarify and the uncertainty signal is strong enough. The contract is added to DOGA's pre-model guidance; the main Hermes model still reasons through the task and writes the answer. Jev does not write the final response, and its judgments are guidance rather than verified facts or calibrated probabilities.

The primary request goes to OpenRouter. TypeSafe is tried only when OpenRouter is unavailable or its request fails, or when no OpenRouter key is configured. The same user request may therefore be sent to TypeSafe during failover. Use this feature only when sending that request to those providers is acceptable; provider usage may incur charges. If both routes fail, DOGA silently keeps its ordinary goal and scenario guidance rather than blocking the answer.

### Simulate Tool

A `simulate` tool is registered in the `doga` toolset for Monte Carlo analysis. The LLM can call it when quantitative probability weighing is needed:

```json
{
  "scenarios": [
    {
      "name": "contract_valid",
      "variables": {"signature_authorized": 0.8, "no_duress": 0.95},
      "conditions": ["signature_authorized and no_duress"]
    }
  ],
  "n_iterations": 10000
}
```

Returns probability distribution, entropy, and uncertainty level. Scenarios can include nested `children` for hierarchical sub-simulations.

### Reason Deeper Tool

A `reason_deeper` tool is registered for recursive self-critique. The LLM calls it after the initial `<world_model>` analysis to identify missed aspects:

```json
{
  "focus": "black hat risk cascade"
}
```

Each recursion level applies a different De Bono thinking lens. The tool returns a structured instruction for deeper analysis. After `max_recursion` depth is reached, DOGA returns a stop signal; if the LLM ignores it 3 times, a hard-break terminates the loop.

---

## Architecture

DOGA uses three Hermes plugin hooks:

| Hook | Purpose |
|------|---------|
| `pre_llm_call` | Inject goal detection, scenario guidance, and the optional Jev response contract |
| `transform_llm_output` | Extract `<world_model>` blocks, format as thinking panel |
| `post_tool_call` | Log tool usage; track `reason_deeper` recursion depth and stack |

No Hermes core files are modified. DOGA is a pure plugin.

---

## About

This repository is an independent fork and adjustment of [DOGA by @0z1-ghb](https://github.com/0z1-ghb/doga-hermes), released under the upstream MIT license. It retains DOGA's original probabilistic reasoning, simulation, and Hermes plugin behavior, and adds a Jev response contract with OpenRouter primary and direct TypeSafe fallback. Jev classifies the user's request; the main Hermes model remains responsible for reasoning through it and writing the answer.

Original DOGA was built by [@0z1-ghb](https://github.com/0z1-ghb). This community maintained fork adds Jev response contracts and is not an official Hermes, TypeSafe, or OpenRouter project.

---

## License

MIT
