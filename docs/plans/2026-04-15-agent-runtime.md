# Agent Runtime Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a single-agent runtime with a ReAct loop, provider-agnostic LLM interface, dynamic tool execution, session/checkpoint storage, and centralized runtime types.

**Architecture:** The runtime will be a small Python package organized into five modules: `engine`, `llm`, `tools`, `storage`, and `types`. The engine will own the ReAct loop and state machine, while the other modules provide replaceable adapters and pure data contracts so future multi-agent work can layer on top without reshaping the core loop.

**Tech Stack:** Python 3.13, pytest, standard library (`asyncio`, `dataclasses`, `typing`, `subprocess`-safe interfaces by contract only)

---

### Task 1: Project Skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `src/agent_runtime/__init__.py`
- Create: `tests/__init__.py`

**Step 1: Create Python package metadata**

Create a minimal `pyproject.toml` with package metadata, `src` layout, and pytest configuration.

**Step 2: Create empty package entrypoint**

Expose the main runtime surface from `src/agent_runtime/__init__.py`.

**Step 3: Create test package marker**

Add `tests/__init__.py` to keep imports predictable.

**Step 4: Run test discovery**

Run: `python -m pytest`
Expected: collection succeeds or reports missing tests cleanly.

### Task 2: Runtime Contracts

**Files:**
- Create: `src/agent_runtime/types.py`
- Test: `tests/test_types.py`

**Step 1: Write failing tests for message and tool contracts**

Cover message roles, tool call signatures, runtime states, and protocol helpers that enforce assistant `tool_calls` immediately followed by `tool_result`.

**Step 2: Run tests to verify failure**

Run: `python -m pytest tests/test_types.py -v`
Expected: FAIL because contracts are not implemented yet.

**Step 3: Implement minimal shared types**

Add dataclasses/enums/protocol helpers for messages, tool calls, tool results, checkpoints, and event statuses.

**Step 4: Re-run tests**

Run: `python -m pytest tests/test_types.py -v`
Expected: PASS.

### Task 3: Tool Registry and Output Handling

**Files:**
- Create: `src/agent_runtime/tools.py`
- Create: `src/agent_runtime/storage.py`
- Test: `tests/test_tools.py`

**Step 1: Write failing tests**

Cover dynamic tool reloading per step, output hard limits, and overflow handoff to external storage by ID.

**Step 2: Run tests to verify failure**

Run: `python -m pytest tests/test_tools.py -v`
Expected: FAIL because registry/storage behavior is missing.

**Step 3: Implement minimal registry and storage**

Add a provider-driven tool registry, per-tool output policies, session/checkpoint persistence, and blob overflow storage.

**Step 4: Re-run tests**

Run: `python -m pytest tests/test_tools.py -v`
Expected: PASS.

### Task 4: LLM Abstraction and Context Compression

**Files:**
- Create: `src/agent_runtime/llm.py`
- Test: `tests/test_llm.py`

**Step 1: Write failing tests**

Cover provider-neutral request/response contracts, `extra` passthrough, micro compression of old tool results, and auto-summary reinjection of system identity plus task goal.

**Step 2: Run tests to verify failure**

Run: `python -m pytest tests/test_llm.py -v`
Expected: FAIL because the abstraction layer does not exist yet.

**Step 3: Implement minimal LLM layer**

Add provider interface, summarizer contract, token estimator, and two-stage context compression utilities.

**Step 4: Re-run tests**

Run: `python -m pytest tests/test_llm.py -v`
Expected: PASS.

### Task 5: Engine Loop and State Machine

**Files:**
- Create: `src/agent_runtime/engine.py`
- Test: `tests/test_engine.py`

**Step 1: Write failing tests**

Cover the ReAct loop, assistant/tool message ordering, cancellation checks at turn start, loop detection, intervention queue flushing, and decision-point observability.

**Step 2: Run tests to verify failure**

Run: `python -m pytest tests/test_engine.py -v`
Expected: FAIL because the engine does not exist yet.

**Step 3: Implement minimal engine**

Add the state machine, runtime orchestration, decision events, cancellation checks, duplicate tool call detection, and safe engine checkout/return semantics for async execution.

**Step 4: Re-run tests**

Run: `python -m pytest tests/test_engine.py -v`
Expected: PASS.

### Task 6: Full Verification

**Files:**
- Verify: `src/agent_runtime/*.py`
- Verify: `tests/*.py`

**Step 1: Run the full suite**

Run: `python -m pytest -v`
Expected: all tests pass.

**Step 2: Review runtime API**

Confirm the package surface cleanly exports the runtime entrypoints needed by callers.

**Step 3: Summarize assumptions**

Document that the current implementation is single-agent, in-memory by default, and ready for external adapters.
