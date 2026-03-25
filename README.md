# U-Ask QA Automation Framework

> End-to-end AI/ML test automation for the **U-Ask UAE Government Chatbot** (`beta-ask.u.ae/en/uask`) —
> validating UI behaviour, AI-generated response quality, and security resilience in both **English** and **Arabic**.

---

## Table of Contents

1. [What Is This Framework?](#1-what-is-this-framework)
2. [Quick Start — Get Running in 5 Steps](#2-quick-start--get-running-in-5-steps)
3. [Project Structure — What Each File Does](#3-project-structure--what-each-file-does)
4. [How Testing Works — The Full Flow](#4-how-testing-works--the-full-flow)
5. [Test Coverage](#5-test-coverage)
6. [AI Validation Deep Dive](#6-ai-validation-deep-dive)
7. [Setup & Installation (Detailed)](#7-setup--installation-detailed)
8. [Environment Variables Reference](#8-environment-variables-reference)
9. [Commands to Run Tests](#9-commands-to-run-tests)
10. [Configuring Test Language](#10-configuring-test-language)
11. [Understanding the Allure Report](#11-understanding-the-allure-report)
12. [Finding the Real Locators (Required Before First Run)](#12-finding-the-real-locators-required-before-first-run)
13. [CI/CD Integration](#13-cicd-integration)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. What Is This Framework?

U-Ask is the UAE Government's generative AI chatbot hosted at **`https://beta-ask.u.ae/en/uask`**.
It answers citizens' questions in English and Arabic using a GPT-backed model.
The application is built with **Angular** and renders entirely client-side.

This framework automatically validates three dimensions of quality every time U-Ask is tested:

| Dimension | What breaks if this is missing |
|---|---|
| **UI Behaviour** | Broken layout, missing widget, wrong text direction for Arabic |
| **AI Response Quality** | Hallucinated facts, off-topic answers, inconsistent EN vs AR responses |
| **Security** | XSS execution, prompt injection, jailbreaks, SQL/template injection |

The framework is written in **Python + pytest + Selenium** and produces a visual **Allure HTML report**
with per-test AI validation scores, inline failure screenshots, and triage categories.

---

## 2. Quick Start — Get Running in 5 Steps

This section is designed for someone who has never used this repository before.
Follow these steps in order and you will have tests running locally in under 10 minutes.

### Step 1 — Clone the repository

```bash
git clone git@github.com:dipand141/framework.git
cd framework
```

> **No SSH key?** Use HTTPS instead:
> ```bash
> git clone https://github.com/dipand141/framework.git
> cd framework
> ```

### Step 2 — Install prerequisites

You need three tools before running the setup script:

| Tool | Version | Install |
|---|---|---|
| **Python** | 3.10 or higher | [python.org/downloads](https://python.org/downloads) |
| **Google Chrome** | Latest | [google.com/chrome](https://google.com/chrome) |
| **Allure CLI** | 2.27+ | See below |

**Install Allure CLI:**

```bash
# macOS
brew install allure

# Windows (using Scoop)
scoop install allure

# Windows (using Chocolatey)
choco install allure

# Linux (Debian/Ubuntu)
sudo apt-get install allure
```

> Don't have `brew` / `scoop` / `choco`? Install them first:
> - macOS: [brew.sh](https://brew.sh)
> - Windows: [scoop.sh](https://scoop.sh) or [chocolatey.org](https://chocolatey.org)

### Step 3 — Run the setup script

```bash
bash setup_venv.sh
```

This single command will:
- Create a Python virtual environment in `./venv/`
- Install all Python dependencies listed in `requirements.txt`
- Copy `.env.example` → `.env` (if `.env` does not already exist)
- Pre-download the 118 MB multilingual AI model from HuggingFace
- Check that Allure CLI is installed

> **Windows users:** Run this in Git Bash or WSL. PowerShell is not supported.

### Step 4 — Configure your environment

Open the `.env` file that was just created and set the target URL:

```bash
# macOS / Linux
nano .env

# Windows (Notepad)
notepad .env
```

The minimum required setting:

```dotenv
CHATBOT_URL=https://beta-ask.u.ae/en/uask
```

Everything else has sensible defaults. See [Section 8](#8-environment-variables-reference) for the full list.

### Step 5 — Activate the virtual environment and run tests

```bash
# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

Then run the tests:

```bash
# Run the full test suite
make test

# OR run a quick smoke check (fastest, ~2 minutes)
make test-smoke
```

After the tests finish, open the report:

```bash
make report
```

Your browser will open automatically with the Allure HTML report.

---

## 3. Project Structure — What Each File Does

```
framework/
│
├── config/
│   └── settings.py              All runtime configuration in one place.
│                                Reads from .env file. Every other module
│                                imports Settings from here — never from
│                                os.environ directly.
│
├── data/
│   └── test-data.json           The test corpus. Contains every prompt,
│                                expected semantic concept, forbidden pattern,
│                                and security payload used by the tests.
│                                Add new test cases here without touching code.
│
├── pages/
│   ├── base_page.py             Foundation for all page objects. Provides
│   │                            WebDriver primitives (click, type, wait),
│   │                            Arabic BiDi text normalisation, scrolling,
│   │                            accessibility (axe-core), and screenshot helpers.
│   │                            Contains NO test assertions — only interactions.
│   │
│   └── chatbot_page.py          The only file that knows about the chatbot's
│                                DOM structure. All CSS selectors live here.
│                                Exposes high-level methods like send_message(),
│                                get_last_response(), switch_language().
│                                When U-Ask's UI changes, update only this file.
│
├── utils/
│   ├── ai_validator.py          The semantic intelligence layer. Loads a
│   │                            multilingual sentence-transformer model and
│   │                            validates chatbot responses for relevance,
│   │                            hallucination, language consistency, and quality.
│   │
│   ├── driver_factory.py        Creates configured Selenium WebDriver instances.
│   │                            Supports Chrome, Firefox, Edge (local) and
│   │                            Selenium Grid (remote/CI). Handles mobile emulation
│   │                            and headless mode.
│   │
│   ├── logger.py                Colour-coded structured logger used across
│   │                            all modules. Call get_logger(__name__) in any file.
│   │
│   └── screenshot_helper.py     Captures failure screenshots, saves them to
│                                reports/screenshots/, and attaches them inline
│                                to the Allure report automatically.
│
├── tests/
│   ├── conftest.py              The fixture hub. Defines how the browser starts
│   │                            and stops, how the chatbot page is opened, how
│   │                            the AI validator is created, and how screenshots
│   │                            are taken on failure. All tests depend on this.
│   │
│   ├── base_test.py             Shared assertion helpers inherited by all test
│   │                            classes. Contains methods like assert_semantic_
│   │                            relevance(), assert_no_forbidden_content(), and
│   │                            assert_rtl_layout(). Wraps every assertion in
│   │                            an Allure step for traceability.
│   │
│   ├── test_ui_behavior.py      Suite A — 15 tests covering the chatbot's
│   │                            visual and interactive behaviour.
│   │
│   ├── test_ai_response_        Suite B — 13 tests validating the quality and
│   │   validation.py            accuracy of AI-generated responses.
│   │
│   └── test_security_           Suite C — 16 tests probing the chatbot for
│       injection.py             XSS, SQL injection, prompt injection, and more.
│
├── reports/
│   ├── allure-results/          Raw Allure JSON files written by pytest after
│   │                            each test run. Input to the HTML report generator.
│   └── screenshots/             Timestamped PNG screenshots captured on failure.
│
├── .env.example                 Template for your .env file. Copy and fill in values.
├── requirements.txt             All Python dependencies with pinned versions.
├── pytest.ini                   Pytest configuration: markers, log format, timeouts.
├── Makefile                     Shortcut commands: make test, make report, etc.
└── setup_venv.sh                One-command setup: creates venv, installs deps,
                                 pre-downloads the 118 MB AI model.
```

---

## 4. How Testing Works — The Full Flow

Understanding this flow helps you debug failures and extend the framework.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         pytest session starts                       │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │   conftest.py: SESSION SETUP │
                    │                              │
                    │  1. settings loaded from .env│
                    │  2. test-data.json parsed    │
                    │  3. AI model loaded (~3 s)   │
                    │  4. Allure env.properties    │
                    │     written to reports/      │
                    └──────────────┬───────────────┘
                                   │
              ┌────────────────────▼────────────────────┐
              │         For each test function:          │
              │                                          │
              │  SETUP (function scope)                  │
              │  ┌─────────────────────────────────┐    │
              │  │ 1. WebDriver created             │    │
              │  │    (Chrome / Firefox / Edge)     │    │
              │  │ 2. chatbot_page.open() called    │    │
              │  │    → browser navigates to u.ae   │    │
              │  │    → chat widget activated       │    │
              │  └──────────────┬──────────────────┘    │
              │                 │                        │
              │  TEST EXECUTION │                        │
              │  ┌──────────────▼──────────────────┐    │
              │  │ 1. Test method runs              │    │
              │  │ 2. Sends prompt to chatbot       │    │
              │  │ 3. Waits for AI response         │    │
              │  │ 4. Runs assertions:              │    │
              │  │    · UI checks (direction, DOM)  │    │
              │  │    · AI validation (similarity)  │    │
              │  │    · Security checks (patterns)  │    │
              │  │ 5. Each step logged to Allure    │    │
              │  └──────────────┬──────────────────┘    │
              │                 │                        │
              │  TEARDOWN       │                        │
              │  ┌──────────────▼──────────────────┐    │
              │  │ 1. If test FAILED:               │    │
              │  │    → screenshot captured         │    │
              │  │    → attached to Allure report   │    │
              │  │ 2. driver.quit() called          │    │
              │  └─────────────────────────────────┘    │
              └─────────────────────────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │   pytest session ends        │
                    │   Allure JSON written to     │
                    │   reports/allure-results/    │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │   allure generate            │
                    │   → HTML report opened in    │
                    │     browser                  │
                    └─────────────────────────────┘
```

### Key design rules

- **Fresh browser per test.** Every test gets its own WebDriver instance. This prevents
  injection payloads or auth state from one test affecting another.

- **Session-scoped AI model.** The sentence-transformer model is expensive to load (~3 seconds).
  It loads once per pytest session and is shared across all AI validation tests.

- **Data-driven.** Test parameters (prompts, expected concepts, security payloads) come from
  `data/test-data.json`. Adding a new test case requires only a new JSON entry — no code change.

- **Single locator file.** All CSS selectors for the chatbot UI live only in `chatbot_page.py`.
  When the live site changes, one file is updated and all tests automatically pick up the change.

---

## 5. Test Coverage

### Suite A — UI Behaviour (`test_ui_behavior.py`) — 15 tests

Tests that the chatbot works as a functional user interface, independently of what the AI says.

| Test | What it checks |
|---|---|
| `test_widget_loads_desktop` | Chat widget is visible on a 1920×1080 screen |
| `test_input_field_accessible_desktop` | Input field is present and not disabled |
| `test_widget_loads_mobile` | Widget visible on an iPhone 12 emulated viewport |
| `test_page_title_present` | Page has a non-empty title |
| `test_send_message_via_input` | Typing and submitting a message works |
| `test_ai_response_rendered` | A bot response bubble appears after sending |
| `test_input_cleared_after_send` | Input box is empty after message is submitted |
| `test_send_button_visible` | The send button is present |
| `test_multiple_messages_render` | Multiple sequential exchanges work |
| `test_english_ltr_layout` | English UI uses left-to-right text direction |
| `test_arabic_rtl_layout` | Arabic UI uses right-to-left text direction |
| `test_arabic_response_direction` | Arabic response bubbles render RTL |
| `test_conversation_scrolls_to_latest` | Chat panel scrolls after multiple messages |
| `test_input_aria_label` | Input field has an ARIA label (screen readers) |
| `test_no_critical_accessibility_violations` | axe-core finds no critical a11y issues |

### Suite B — AI Response Validation (`test_ai_response_validation.py`) — 13 tests

Tests the quality and trustworthiness of the AI's answers using semantic similarity.

| Test | What it checks |
|---|---|
| `test_english_response_relevance` (×5) | Each English public service query gets a relevant, on-topic response |
| `test_english_response_formatting` | Response contains no raw HTML tags or truncated sentences |
| `test_arabic_response_relevance` (×4) | Each Arabic query gets a semantically relevant response |
| `test_arabic_response_language_detection` | Arabic response is actually in Arabic |
| `test_response_consistency` (×2) | Same intent in EN and AR yields semantically consistent responses |
| `test_wording_variation_consistency` | Paraphrased English queries yield similar answers |
| `test_loading_indicator_appears` | Typing indicator shows while AI is thinking |
| `test_graceful_fallback_gibberish` | Nonsense input gets a polite, non-crashing response |
| `test_long_input_handled_gracefully` | Very long input does not break the widget |

**How hallucination is detected:**
The response is embedded using a multilingual AI model. Its cosine similarity to the
expected semantic concepts is computed. A score below **0.40** flags the response as
potentially off-topic or hallucinated. A score below the configured **threshold (default 0.65)**
fails the test.

### Suite C — Security & Injection (`test_security_injection.py`) — 16 tests

Tests that the chatbot cannot be exploited via its input field.

| Test | What it checks |
|---|---|
| `test_script_tag_not_executed` | `<script>` tag does not run and does not appear in the DOM |
| `test_xss_variant_sanitised` (×4) | `onerror`, `onload`, `javascript:`, `<iframe src='javascript:'>` payloads are blocked |
| `test_html_not_rendered` | Injected `<h1>` tags do not appear as real DOM elements |
| `test_sql_injection_no_db_error` (×4) | SQL strings produce no database error messages |
| `test_ignore_instructions_rejected` | "Ignore all previous instructions" prompt is resisted |
| `test_system_prompt_not_revealed` | System prompt contents are not exposed |
| `test_dan_jailbreak_blocked` | DAN / unrestricted-mode jailbreak does not work |
| `test_newline_injection_blocked` | Hidden instructions via newlines are ignored |
| `test_arabic_prompt_injection_rejected` | Arabic injection payloads are also blocked |
| `test_ssti_not_evaluated` | `{{7*7}}` expressions are not evaluated to `49` |
| `test_data_driven_security_case` (×7) | All security cases + variants from test-data.json |

**Total: 44 tests across 3 suites**

---

## 6. AI Validation Deep Dive

The framework uses **`paraphrase-multilingual-MiniLM-L12-v2`** from HuggingFace sentence-transformers.

**Why this model?**
- Trained on 50+ languages — Arabic and English share the **same vector space**
- This means an Arabic response can be compared to an English-language expected concept
  without any translation step
- 118 MB, runs on CPU in milliseconds per query
- Downloaded automatically during `setup_venv.sh`

**Validation pipeline for every AI response:**

```
Step 1 — Forbidden Pattern Check
  Scan response text for regex patterns that must never appear:
  e.g. <script>, onerror=, DROP TABLE, raw template expressions {{...}}
  → Any match = FAIL immediately

Step 2 — Semantic Similarity Scoring
  Embed the response and each expected concept using the model.
  Compute cosine similarity between the response and every concept.
  Take the highest score.
  → Score < 0.40  = potential hallucination (flagged, test FAIL)
  → Score < 0.65  = off-topic response (test FAIL)
  → Score >= 0.65 = test PASS

Step 3 — Language Detection
  Use langdetect to check if the response is in the expected language.
  An Arabic prompt should yield an Arabic response.
  → Mismatch = warning logged, test FAIL

Step 4 — Quality Checks
  · Is the response too short (< 10 chars)?
  · Does it contain unescaped HTML in the text?
  · Does it end abruptly mid-word (truncation)?
  → Issues attached to Allure as warnings or failures

Step 5 — Allure Report Attachment
  A structured validation report is attached to every test showing:
  · The original prompt
  · The response (first 300 chars)
  · Per-concept similarity scores
  · Max score vs threshold
  · Any violations found
```

**Adjusting the threshold:**
Set `SIMILARITY_THRESHOLD` in your `.env` file. A higher value is stricter:
- `0.50` — permissive (accept loosely related responses)
- `0.65` — default (recommended for government service validation)
- `0.80` — strict (require responses to closely match expected concepts)

---

## 7. Setup & Installation (Detailed)

### Prerequisites

| Tool | Version | macOS | Windows | Linux |
|---|---|---|---|---|
| Python | 3.10+ | `brew install python` | [python.org](https://python.org/downloads) | `apt install python3` |
| Google Chrome | Latest | [google.com/chrome](https://google.com/chrome) | [google.com/chrome](https://google.com/chrome) | [google.com/chrome](https://google.com/chrome) |
| Allure CLI | 2.27+ | `brew install allure` | `scoop install allure` | `apt install allure` |
| Git | Any | `brew install git` | [git-scm.com](https://git-scm.com) | `apt install git` |

### One-command setup

```bash
# Clone the repository
git clone git@github.com:dipand141/framework.git
cd framework

# Run the setup script — this does everything:
#   · Creates a Python virtual environment in ./venv/
#   · Installs all dependencies from requirements.txt
#   · Copies .env.example → .env (if not already present)
#   · Pre-downloads the 118 MB sentence-transformer AI model
#   · Checks for Allure CLI
bash setup_venv.sh
```

### Activate the virtual environment

```bash
# macOS / Linux
source venv/bin/activate

# Windows (Command Prompt)
venv\Scripts\activate.bat

# Windows (PowerShell)
venv\Scripts\Activate.ps1
```

> You will see `(venv)` at the start of your terminal prompt when the environment is active.
> You must activate it every time you open a new terminal window.

### Configure your environment

```bash
# Open .env and set at minimum:
#   CHATBOT_URL  — the URL of the U-Ask chatbot
#   BROWSER      — chrome, firefox, or edge
#   TEST_LANGUAGE — en, ar, or both
nano .env          # macOS / Linux
notepad .env       # Windows
```

---

## 8. Environment Variables Reference

All variables live in your `.env` file (copied from `.env.example` during setup).
You never need to set environment variables manually in your shell — the framework reads `.env` automatically.

| Variable | Default | Required | Description |
|---|---|---|---|
| `CHATBOT_URL` | `https://beta-ask.u.ae/en/uask` | **Yes** | Target chatbot URL |
| `BROWSER` | `chrome` | No | `chrome`, `firefox`, or `edge` |
| `HEADLESS` | `false` | No | Set `true` to run without a visible browser window (required for CI) |
| `IMPLICIT_WAIT` | `10` | No | Seconds Selenium waits before raising NoSuchElementException |
| `EXPLICIT_WAIT` | `30` | No | Seconds WebDriverWait waits for a specific condition |
| `TEST_LANGUAGE` | `both` | No | `en`, `ar`, or `both` |
| `MOBILE_EMULATION` | `false` | No | Enable Chrome device emulation |
| `MOBILE_DEVICE` | `iPhone 12` | No | Device name (Chrome DevTools device list) |
| `SIMILARITY_THRESHOLD` | `0.65` | No | Minimum cosine similarity score to pass AI validation (range 0–1) |
| `SENTENCE_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | No | HuggingFace model name |
| `OPENAI_API_KEY` | *(empty)* | No | Optional — enables LLM-based deep validation (comment out if unused) |
| `SCREENSHOT_ON_FAILURE` | `true` | No | Auto-capture screenshot on test failure |
| `SCREENSHOTS_DIR` | `reports/screenshots` | No | Directory where failure screenshots are saved |
| `ALLURE_RESULTS_DIR` | `reports/allure-results` | No | Directory where Allure writes JSON results |
| `SELENIUM_GRID_URL` | *(empty)* | No | Remote Selenium Grid URL for CI/distributed execution |
| `INTER_MESSAGE_DELAY` | `1.5` | No | Seconds to pause between chat messages (avoids rate-limiting) |
| `RETRY_DELAY` | `2.0` | No | Seconds to wait between retry attempts |
| `MAX_RETRIES` | `3` | No | Retry attempts for flaky element interactions |
| `LOG_LEVEL` | `INFO` | No | `DEBUG`, `INFO`, `WARNING`, or `ERROR` |

### Minimal `.env` to get started

```dotenv
CHATBOT_URL=https://beta-ask.u.ae/en/uask
BROWSER=chrome
HEADLESS=false
TEST_LANGUAGE=both
SIMILARITY_THRESHOLD=0.65
```

---

## 9. Commands to Run Tests

Make sure your virtual environment is active (`source venv/bin/activate`) before running any command.

### Full test suite

```bash
make test
```
Runs all three suites (UI + AI Validation + Security) in both English and Arabic.

---

### By suite

```bash
make test-ui          # Suite A — UI behaviour only
make test-ai          # Suite B — AI response validation only
make test-security    # Suite C — Security injection only
```

---

### By language

```bash
make test-en          # English test cases only
make test-ar          # Arabic test cases only
```

---

### Smoke / quick sanity check

```bash
make test-smoke
```
Runs only the most critical tests (marked `@pytest.mark.smoke`).
Use this as a fast pre-deployment gate — completes in under 2 minutes.

---

### Mobile viewport

```bash
make test-mobile
```
Runs tests with Chrome's iPhone 12 device emulation enabled.

---

### Parallel execution

```bash
make test-parallel    # 4 workers in parallel
```
Significantly faster for large suites. Security tests still use function-scoped
browsers so they remain isolated.

---

### Generate and open the Allure report

```bash
make report           # Generates HTML report and opens it in your browser
make report-serve     # Live-serve the report from the results directory
```

---

### Lint and format code

```bash
make lint             # Check with flake8 + black
make format           # Auto-format with black
```

---

### Clean generated files

```bash
make clean            # Remove reports, screenshots, .pytest_cache, __pycache__
make clean-all        # Also remove the virtual environment
```

---

### Using pytest directly (advanced)

```bash
# Run a specific test file
pytest tests/test_security_injection.py

# Run tests matching a marker combination
pytest -m "ui and smoke"
pytest -m "ai_validation and english"
pytest -m "security"

# Run a single test by name
pytest tests/test_ui_behavior.py::TestMessageSending::test_send_message_via_input

# Run with visible browser (override headless)
HEADLESS=false pytest -m smoke

# Run in Arabic only, headless
TEST_LANGUAGE=ar HEADLESS=true pytest -m arabic

# Verbose output with no capture
pytest -v -s tests/test_ai_response_validation.py
```

---

### All available make targets at a glance

```bash
make help
```

Output:
```
install              Create venv and install all dependencies
test                 Run the full test suite
test-smoke           Run smoke tests only
test-ui              Run UI behaviour tests
test-ai              Run AI response validation tests
test-security        Run security / injection tests
test-en              Run English-language tests
test-ar              Run Arabic-language tests
test-mobile          Run mobile viewport tests
test-parallel        Run full suite in parallel (4 workers)
report               Generate & open Allure HTML report
report-serve         Serve live Allure report from results directory
lint                 Run flake8 and black check
format               Auto-format code with black
clean                Remove generated reports, cache, and pyc files
clean-all            Also remove the virtual environment
```

---

## 10. Configuring Test Language

Edit `.env` to control which language suite runs:

```dotenv
TEST_LANGUAGE=en      # English tests only
TEST_LANGUAGE=ar      # Arabic tests only
TEST_LANGUAGE=both    # Both (default)
```

Or pass inline without editing `.env`:

```bash
TEST_LANGUAGE=ar make test-ai
TEST_LANGUAGE=en pytest -m english
```

**What changes per language:**
- Arabic tests switch the chatbot to Arabic before sending prompts
- Arabic responses are validated for RTL text direction
- Arabic responses are checked using the same multilingual AI model
  against the same English-language semantic concepts (cross-language embedding)
- Language detection confirms the response is actually in Arabic

---

## 11. Understanding the Allure Report

After running `make report`, the HTML report opens in your browser with:

### Suites view
Tests grouped by feature and story (e.g., "AI Response Quality > English Public Service Queries").

### Per-test detail
Each test shows:
- Every `with allure.step(...)` block executed, in order
- The AI Validation Report attachment (similarity scores, threshold, violations)
- The Prompt & Response attachment showing what was sent and received
- A failure screenshot (if the test failed), attached inline

### Triage categories
The report automatically groups failures into:
- **AI Validation Failures** — tests where semantic similarity was too low
- **Security Violations** — tests where forbidden patterns were found
- **UI / Layout Failures** — RTL/LTR direction mismatches or missing widgets
- **Timeout Failures** — tests where WebDriverWait expired

### Environment panel
Shows browser, URL, AI model, similarity threshold, language setting, and platform —
so every report is fully reproducible.

---

## 12. Finding the Real Locators (Required Before First Run)

### Why this step is needed

`https://beta-ask.u.ae/en/uask` is an **Angular Single-Page Application**.

When the browser fetches the page, it receives only this in the HTML:

```html
<app-root class="vh-100"></app-root>
```

Angular then bootstraps in the browser and **injects the entire chat UI into the DOM at runtime**.
This means the chat input, send button, response bubbles, and all other elements do not exist in
the page source — they only appear after JavaScript runs. The framework handles Angular's boot time
automatically, but the **CSS selectors must be discovered manually** by inspecting the live rendered DOM.

---

### How to find the selectors (one-time setup, ~15 minutes)

**Step 1 — Open the page in Chrome**
```
https://beta-ask.u.ae/en/uask
```
Wait 2–3 seconds for Angular to finish loading.

**Step 2 — Open Chrome DevTools**
Press `F12` → click the **Elements** tab.

**Step 3 — Find each element using this priority**

For each element below, right-click it in the browser → **Inspect**, then look for
attributes in this order of preference:

| Priority | Attribute | Example | Why |
|---|---|---|---|
| 1st | `data-testid` | `data-testid="send-button"` | Never changes with styling |
| 2nd | `id` | `id="chat-input"` | Stable if not auto-generated |
| 3rd | `aria-label` | `aria-label="Send message"` | Accessible and stable |
| 4th | Angular component tag | `app-chat-input` | Stable across style changes |
| Last | class name | `.send-btn` | Only use if unique and not dynamic |

> **Avoid** Angular-generated attributes like `_ngcontent-abc-c123` — these change with every build.

---

**Step 4 — Fill in these 8 selectors in `pages/chatbot_page.py`**

| Constant | Element to find |
|---|---|
| `INPUT_FIELD` | The textarea/input where the user types |
| `SEND_BUTTON` | The button that submits the message |
| `RESPONSE_BUBBLE` | Each AI response message bubble |
| `TYPING_INDICATOR` | The loading animation while AI responds |
| `LANG_TOGGLE_EN` | The English language switch button |
| `LANG_TOGGLE_AR` | The Arabic language switch button |
| `CHAT_CONTAINER` | The outer wrapper panel for the whole chat |
| `CLEAR_BUTTON` | "New chat" or "Clear conversation" button |

**Angular Material tip:** If the app uses Angular Material components, these selectors
are reliable:
```python
INPUT_FIELD      = (By.CSS_SELECTOR, "mat-form-field textarea")
SEND_BUTTON      = (By.CSS_SELECTOR, "button[mat-icon-button][aria-label*='send' i]")
RESPONSE_BUBBLE  = (By.CSS_SELECTOR, "app-bot-message, .bot-message")
TYPING_INDICATOR = (By.CSS_SELECTOR, "app-typing-indicator, .typing-animation")
```

---

**Step 5 — Verify selectors work**
```bash
make test-smoke
```
If the smoke tests pass, all critical selectors are correct.

---

### DevTools quick-find trick

Press `Ctrl+F` inside the DevTools Elements panel and search for:
- `textarea` — finds input fields
- `send` — finds send-related elements
- `bot` or `assistant` — finds AI response containers
- `typing` or `loading` — finds loading indicators
- `lang` or `ar` — finds language toggles

---

## 13. CI/CD Integration

```yaml
# .github/workflows/qa.yml
name: U-Ask QA

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 6 * * *'          # Daily at 06:00 UTC

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Cache HuggingFace AI model
        uses: actions/cache@v3
        with:
          path: ~/.cache/huggingface/
          key: hf-model-${{ hashFiles('requirements.txt') }}

      - name: Setup and run tests
        env:
          HEADLESS: "true"
          TEST_LANGUAGE: "both"
          CHATBOT_URL: ${{ secrets.CHATBOT_URL }}
        run: |
          bash setup_venv.sh
          source venv/bin/activate
          make test

      - name: Upload Allure results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: allure-results
          path: reports/allure-results/
```

> **Tip:** Cache `~/.cache/huggingface/` between runs — the 118 MB model only needs
> to be downloaded once.

---

## 14. Troubleshooting

**ChromeDriver version mismatch**
```bash
pip install --upgrade webdriver-manager
```

**AI model download fails (offline / restricted environment)**
```bash
# On a machine with internet access:
python -c "
from sentence_transformers import SentenceTransformer
SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
"
# Then copy ~/.cache/huggingface/ to the target machine
```

**Tests time out waiting for a chatbot response**
- Increase `EXPLICIT_WAIT` in `.env` (e.g., `60`)
- Increase `INTER_MESSAGE_DELAY` to slow down message sending and avoid rate-limiting

**Arabic RTL direction assertion fails**
- The site may put `dir="rtl"` on the chat container rather than `<html>`
- Inspect the live DOM and update `BasePage.get_page_text_direction()` if needed

**Allure report shows no tests**
- Ensure you ran `make test` before `make report`
- Check `reports/allure-results/` contains `.json` files

**Browser opens but chatbot widget never appears**
- Verify `CHATBOT_URL` in `.env` points to the correct page
- Open the URL manually and check if the chat widget requires a cookie consent click first
- Add a cookie consent dismissal step to `ChatbotPage.open_and_activate()` if needed

**`make` command not found on Windows**
- Install Make via Chocolatey: `choco install make`
- Or run the pytest commands directly (see [Using pytest directly](#using-pytest-directly-advanced))

**`venv\Scripts\Activate.ps1` is blocked on Windows**
- Run PowerShell as Administrator and execute:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```
