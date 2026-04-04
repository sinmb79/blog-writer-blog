# Blog Publishing Platform Port Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the validated WordPress and Naver publishing core from `blog-writer-mcp` into `blog-writer-blog`, including platform routing, CLI support, config, docs, and regression tests.

**Architecture:** Keep `bots/publisher_bot.py` as the stable publishing entrypoint and extend it into a small router. Add dedicated `wp_publisher_bot.py`, `naver_publisher_bot.py`, and `image_bot.py` modules for platform-specific work. Update CLI and pending-review approval to preserve requested platforms across manual-review workflows.

**Tech Stack:** Python, Click CLI, requests, Playwright, pytest

---

### Task 1: Lock The Expected Behavior With Tests

**Files:**
- Create: `tests/test_publish_platforms.py`
- Create: `tests/test_wp_publisher_bot.py`
- Create: `tests/test_naver_publisher_bot.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write the failing tests**
- [ ] **Step 2: Run the targeted pytest commands and confirm failure**
- [ ] **Step 3: Keep failures focused on missing platform routing and missing publisher modules**

### Task 2: Add Platform-Specific Publishers And Shared Image Helper

**Files:**
- Create: `bots/wp_publisher_bot.py`
- Create: `bots/naver_publisher_bot.py`
- Create: `bots/image_bot.py`
- Modify: `requirements.txt`
- Modify: `pyproject.toml`

- [ ] **Step 1: Port WordPress publisher with matching module-level `publish(article)` interface**
- [ ] **Step 2: Port Naver publisher with persistent-profile Playwright flow**
- [ ] **Step 3: Port the minimal image helper needed for Naver representative image generation**
- [ ] **Step 4: Add Playwright dependency metadata**
- [ ] **Step 5: Run targeted tests for the new modules**

### Task 3: Extend The Main Publisher Router And CLI

**Files:**
- Modify: `bots/publisher_bot.py`
- Modify: `blogwriter/cli.py`
- Modify: `dashboard/backend/api_content.py`

- [ ] **Step 1: Add platform routing while preserving Blogger default behavior**
- [ ] **Step 2: Persist requested platforms into pending review payloads**
- [ ] **Step 3: Make approval reuse the stored platform set**
- [ ] **Step 4: Add CLI `--platform` support**
- [ ] **Step 5: Ensure dashboard approval still works with the default path**
- [ ] **Step 6: Run targeted router and CLI tests**

### Task 4: Update Runtime Config And Public Docs

**Files:**
- Modify: `.env.example`
- Create: `config/platforms.json`
- Modify: `.gitignore`
- Create: `pytest.ini`
- Modify: `README.md`

- [ ] **Step 1: Add WordPress, Naver, and BananaPro env examples**
- [ ] **Step 2: Add platform defaults config**
- [ ] **Step 3: Ignore generated pytest temp and image files**
- [ ] **Step 4: Document multi-platform publishing and Naver setup in README**
- [ ] **Step 5: Keep README bilingual where new sections are added**

### Task 5: Verify, Commit, Push, And Release

**Files:**
- Modify: release metadata through GitHub only

- [ ] **Step 1: Run the full verification suite for touched areas**
- [ ] **Step 2: Stage only the intended files**
- [ ] **Step 3: Commit with a focused message**
- [ ] **Step 4: Push the branch and fast-forward `main` if appropriate**
- [ ] **Step 5: Create a GitHub release with Korean-first release notes**
