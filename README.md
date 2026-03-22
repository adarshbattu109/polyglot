# 🗣️ Polyglot: Multi-Language Translation API

A powerful, locally-hosted machine learning translation service that leverages state-of-the-art language models for accurate, offline text translation into multiple languages simultaneously. Built with FastAPI, integrated with OpenAI-compatible APIs, and designed for seamless deployment with Ollama.

## Table of Contents

- [Project Overview](#project-overview)
- [Feature Highlights](#feature-highlights)
- [Directory Structure](#directory-structure)
- [Architecture & Data Flow](#architecture--data-flow)
- [Installation Guide](#installation-guide)
- [Environment Configuration](#environment-configuration)
- [Filters & Controls Reference](#filters--controls-reference)
- [Usage Examples](#usage-examples)
- [API Reference](#api-reference)
- [Testing & Troubleshooting](#testing--troubleshooting)
- [Contributing Guidelines](#contributing-guidelines)
- [Authors & Maintainers](#authors--maintainers)
- [License](#license)

---

## Project Overview

### What is Polyglot?

Polyglot is a lightweight, microservice-ready translation API that enables applications to translate text into multiple target languages with a single API request. Unlike cloud-based translation services that require internet connectivity and incur API costs, Polyglot runs entirely on your local machine using open-source language models via Ollama.

### The Problem It Solves

- **Cost**: Eliminates per-request charges from cloud translation services (Google Translate API, AWS Translate, Azure Translator, etc.)
- **Privacy**: Keeps sensitive documents and user data on your infrastructure without sending to third-party servers
- **Latency**: Achieves lower response times by eliminating network round-trips to cloud providers
- **Reliability**: Functions offline without dependence on external service availability
- **Flexibility**: Allows model swapping and customization without API constraints

### Why Polyglot Was Built

Organizations increasingly need to handle multilingual content—from e-commerce platforms supporting customers worldwide to international documentation systems and content localization workflows. Polyglot bridges the gap between the simplicity of single-request APIs and the control of self-hosted infrastructure, providing:

1. **Concurrent translation**: Translate to multiple languages in parallel using thread pools
2. **Standardized HTTP API**: RESTful endpoints compatible with any client or programming language
3. **Zero vendor lock-in**: Swap underlying models or translation engines without API changes
4. **Development-friendly**: FastAPI auto-generated documentation and Model Context Protocol (MCP) integration for AI-assisted development
5. **Production-ready**: Error handling, logging, structured response formats, and containerization support

---

## Feature Highlights

- ✅ **Multi-Language Translation**: Translate a single text into multiple target languages with one HTTP request
- ✅ **Concurrent Processing**: Thread-based parallel execution for optimal performance when translating to many languages
- ✅ **Offline-First Architecture**: No internet required; runs entirely on local hardware using Ollama
- ✅ **OpenAI-Compatible API**: Uses OpenAI Python client library for seamless integration with Ollama's compatible endpoint
- ✅ **FastAPI Framework**: RESTful API with automatic Swagger/OpenAPI documentation (available at `/docs`)
- ✅ **Structured Logging**: Centralized, timestamped logging system with separate log files per execution session
- ✅ **Error Handling**: Graceful exception handling with informative error messages in API responses
- ✅ **Model Context Protocol (MCP) Integration**: Built-in support for AI-assisted development workflows
- ✅ **Configurable LLM Backend**: Easy switching between Ollama models without code changes
- ✅ **Python 3.12+ Support**: Built with the latest Python standard library features and performance improvements
- ✅ **uv Package Manager**: Lightning-fast dependency management with deterministic builds via uv
- ✅ **Development-Ready**: Hot-reloading enabled during development for rapid iteration

---

## Directory Structure

```
polyglot/
├── src/                              # Main source code directory
│   ├── app/                          # FastAPI application module
│   │   ├── __init__.py              # Server launcher with uvicorn entry point
│   │   ├── main.py                  # FastAPI application instance and /translate endpoint
│   │   └── __pycache__/             # Python bytecode cache (auto-generated)
│   │
│   ├── constants/                    # Application configuration module
│   │   ├── __init__.py              # Logging configuration setup
│   │   ├── constants.py             # LLM settings and translation prompt templates
│   │   ├── filepaths.py             # Artifact and log directory definitions
│   │   └── __pycache__/             # Python bytecode cache (auto-generated)
│   │
│   ├── helper/                       # Core translation logic module
│   │   ├── __init__.py              # Empty module init
│   │   ├── helper.py                # Translation engine with concurrent processing
│   │   ├── fileops.py               # File operations utility (reserved for future use)
│   │   └── __pycache__/             # Python bytecode cache (auto-generated)
│   │
│   └── polyglot/                     # Main package entry point
│       ├── __init__.py              # CLI command entry point
│       └── __pycache__/             # Python bytecode cache (auto-generated)
│
├── logs/                             # Application runtime logs directory
│   └── polyglot_YYYYMMDD_HHMMSS.log # Timestamped log files (auto-created)
│
├── artifacts/                        # Output artifacts directory (reserved for future use)
│
├── .venv/                            # Python virtual environment (local development)
│
├── .git/                             # Git version control repository
│
├── .gitignore                        # Git ignore rules
│
├── .python-version                   # Python version specification (3.12)
│
├── pyproject.toml                    # Project metadata, dependencies, and entry points
│
├── uv.lock                           # Dependency lock file (uv package manager)
│
└── README.md                         # This file


### Module Descriptions

| Module | File | Purpose |
|--------|------|---------|
| **app** | `main.py` | FastAPI application with `/translate` POST endpoint for handling translation requests and MCP integration |
| **app** | `__init__.py` | Launches uvicorn server; serves as `polyglotapi` command entry point for starting the API server |
| **constants** | `constants.py` | Configuration: `HOST`, `PORT`, `MODEL`, `API_KEY` for Ollama connection; `PROMPT` template for LLM instructions |
| **constants** | `filepaths.py` | Defines `LOG_DIR` and `ARTIFACTS_DIR` paths; creates directories on first import |
| **constants** | `__init__.py` | Sets up centralized logging with timestamps; configures root logger for all modules |
| **helper** | `helper.py` | Core translation engine: payload preparation, concurrent LLM querying, translation orchestration |
| **helper** | `fileops.py` | Reserved for file I/O operations (currently empty; available for bulk file translation features) |
| **polyglot** | `__init__.py` | Simple CLI entry point; serves as `polyglot` command entry point |

---

## Architecture & Data Flow

### System Architecture

```

┌─────────────────────────────────────────────────────────────────────┐
│ CLIENT APPLICATION │
│ (e.g., Web Browser, Script) │
└────────────────────────────┬────────────────────────────────────────┘
│
HTTP POST Request
(JSON Payload)
│
▼
┌─────────────────────────────────────────────────────────────────────┐
│ FASTAPI SERVER │
│ (uvicorn, localhost:8000) │
│ │
│ ┌───────────────────────────────────────────────────────────────┐ │
│ │ POST /translate Endpoint Handler │ │
│ │ │ │
│ │ • Receives JSON request: { │ │
│ │ "text": "Hello World", │ │
│ │ "target_languages": ["Spanish", "French"] │ │
│ │ } │ │
│ │ • Validates input parameters │ │
│ │ • Passes to translation engine │ │
│ └───────────────────────────────────────────────────────────────┘ │
│ │ │
│ (function call) │
│ │ │
│ ┌───────────────────────────────────────────────────────────────┐ │
│ │ translate_to_languages() - Helper Module │ │
│ │ │ │
│ │ • Prepares payload for LLM │ │
│ │ • Creates ThreadPoolExecutor for parallel processing │ │
│ │ • Submits query_llm() tasks (one per job) │ │
│ │ • Collects results as they complete │ │
│ └───────────────────────────────────────────────────────────────┘ │
│ │ │
│ (concurrent threads executed in parallel) │
│ │ │
│ ┌───────────────────────────────────────────────────────────────┐ │
│ │ query_llm() - Core Query Function (runs in thread) │ │
│ │ │ │
│ │ • Creates OpenAI client pointing to Ollama endpoint │ │
│ │ • Serializes payload to JSON string │ │
│ │ • Sends chat completion request with: │ │
│ │ - System message (translation instructions) │ │
│ │ - User message (JSON payload to translate) │ │
│ │ • Parses JSON response from LLM │ │
│ │ • Returns structured translation result │ │
│ │ • On error: catches exceptions, returns error object │ │
│ └───────────────────────────────────────────────────────────────┘ │
│ │ │
│ (HTTP request to OpenAI-compatible endpoint) │
│ │ │
└─────────────────────────────┼───────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────────┐
│ OLLAMA LOCAL SERVICE │
│ (localhost:11434, OpenAI-compatible API) │
│ │
│ ┌───────────────────────────────────────────────────────────────┐ │
│ │ POST /v1/chat/completions (OpenAI-compatible endpoint) │ │
│ │ │ │
│ │ • Receives chat request with model "qwen3-coder:480b" │ │
│ │ • Loads model from local disk (if not in memory) │ │
│ │ • Processes messages through LLM │ │
│ │ • Generates translation JSON response │ │
│ │ • Returns structured message content │ │
│ └───────────────────────────────────────────────────────────────┘ │
│ │ │
│ (LLM inference execution) │
│ │ │
│ ┌───────────────────────────────────────────────────────────────┐ │
│ │ QWEN3-CODER:480B Language Model │ │
│ │ (Local model, ~480B parameters, on-device) │ │
│ │ │ │
│ │ • Reads translation system prompt │ │
│ │ • Analyzes source text and target languages │ │
│ │ • Generates accurate translations for each language │ │
│ │ • Formats output as JSON with requested structure │ │
│ └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
│
HTTP JSON Response
(structured translations)
│
▼
┌─────────────────────────────────────────────────────────────────────┐
│ FASTAPI SERVER │
│ (Response Construction) │
│ │
│ • Receives LLM response from Ollama │
│ • Aggregates thread results into single response │
│ • Wraps in JSONResponse │
│ • Returns to client with HTTP 200 │
└─────────────────────────────────────────────────────────────────────┘
│
HTTP JSON Response
│
▼
┌─────────────────────────────────────────────────────────────────────┐
│ CLIENT APPLICATION │
│ (Receives Result) │
│ │
│ { │
│ "id": "polyglot_3847", │
│ "text": "Hello World", │
│ "translations": [ │
│ {"language": "Spanish", "translation": "Hola Mundo"}, │
│ {"language": "French", "translation": "Bonjour le monde"} │
│ ] │
│ } │
└─────────────────────────────────────────────────────────────────────┘

````

### Data Flow Summary

1. **Input**: Client sends HTTP POST request to `/translate` with `text` and `target_languages`
2. **Validation**: FastAPI endpoint validates input existence and non-emptiness
3. **Preparation**: Helper module creates payload with unique ID for tracking
4. **Concurrency**: ThreadPoolExecutor spawns parallel threads, one per translation task
5. **LLM Query**: Each thread independently queries Ollama via OpenAI-compatible client
6. **Processing**: Ollama's qwen3-coder model processes requests (on local GPU/CPU)
7. **Response**: LLM returns JSON with translations; threads aggregate results
8. **Output**: FastAPI returns aggregated response with all translations and metadata

### Key Design Decisions

- **Thread-based Concurrency**: Python's ThreadPoolExecutor allows parallel network I/O without GIL blocking
- **OpenAI Client Library**: Ollama is OpenAI-compatible, so we use the official client without modifications
- **Stateless Design**: No session management; each request is independent and can be load-balanced
- **Error Isolation**: Failed translations don't block successful ones; errors are returned in response
- **Local-First**: All processing happens locally; internet required only for external LLM imports

---

## Installation Guide

### Prerequisites

Before installing Polyglot, ensure you have:

- **Python 3.12 or higher** (check with `python3 --version`)
- **pip** (Python package installer) or **uv** (faster alternative)
- **Ollama** service running locally on port 11434
- **git** (for cloning the repository)

### Step 1: Verify Python Version

```bash
python3 --version
# Expected output: Python 3.12.x or higher
````

If you have multiple Python versions, ensure you're using 3.12+:

```bash
python3.12 --version
```

### Step 2: Clone the Repository

```bash
git clone https://github.com/adarsh-battu/polyglot.git
cd polyglot
```

### Step 3: Create a Virtual Environment

#### Option A: Using venv (Standard Python)

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate          # On Linux/macOS
# OR
.venv\Scripts\activate             # On Windows

# Verify activation (prompt should show (.venv) prefix)
which python                       # Should show path inside .venv
```

#### Option B: Using uv (Recommended - Faster)

If you have `uv` installed:

```bash
# uv automatically creates and manages environments
uv venv .venv

# Activate virtual environment
source .venv/bin/activate          # On Linux/macOS
# OR
.venv\Scripts\activate             # On Windows
```

### Step 4: Install Dependencies

#### Option A: Using pip with local editable install

```bash
# Activate virtual environment first (if not already activated)
source .venv/bin/activate

# Install in editable mode with all dependencies
pip install -e .

# Verify installation
pip list | grep -E "fastapi|openai|uvicorn"
```

#### Option B: Using uv (Recommended - Much Faster)

```bash
# uv automatically detects and installs from pyproject.toml
uv pip install -e .

# Or use uv sync instead (even faster)
uv sync
```

#### Option C: Direct dependency installation with pip

```bash
pip install fastapi>=0.135.1 \
            uvicorn>=0.42.0 \
            fastapi-mcp>=0.4.0 \
            openai>=2.29.0 \
            pandas>=2.3.3 \
            streamlit>=1.55.0 \
            httpx
```

### Step 5: Verify Installation

```bash
# Check that polyglot commands are available
polyglot --help        # Should show hello message
polyglotapi --help     # Should show uvicorn help text (if using as module)

# Or check directly
python -c "import fastapi; import openai; print('✓ All dependencies installed')"
```

### Step 6: Install/Start Ollama

If you don't have Ollama running yet:

#### macOS/Linux

```bash
# Download and install Ollama from https://ollama.ai
# Or use package manager:

# macOS (via Homebrew)
brew install ollama

# Linux (via official script)
curl https://ollama.ai/install.sh | sh
```

#### Start Ollama Service

```bash
# In a separate terminal, start Ollama service
ollama serve

# Should output: Listening on 127.0.0.1:11434
```

#### Pull the Required Model

In another terminal:

```bash
# Download qwen3-coder model (required for translation)
ollama pull qwen3-coder:480b-cloud

# Verify model is available
ollama list
# Should show: qwen3-coder:480b-cloud
```

### Step 7: Verify Full Setup

```bash
# Test Ollama connectivity
curl -X POST http://localhost:11434/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3-coder:480b-cloud",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": false
  }'

# Should return a chat response (not an error)
```

---

## Environment Configuration

### Configuration File: `src/constants/constants.py`

The application behavior is controlled via constants defined in the constants module:

```python
# LLM Connection Settings
HOST: str = "localhost"              # Ollama server hostname
PORT: int = 11434                    # Ollama server port
MODEL: str = "qwen3-coder:480b-cloud"  # LLM model identifier
API_KEY: str = "ollama"              # API key for Ollama (usually "ollama")

# Translation Prompt Template
PROMPT = """
You are a helpful assistant that translates text into multiple languages.
...
[Full prompt template for LLM instructions]
"""
```

### File Paths Configuration: `src/constants/filepaths.py`

```python
LOG_DIR = "logs"        # Directory for application logs
ARTIFACTS_DIR = "artifacts"  # Directory for output artifacts
```

These directories are automatically created on first run.

### Logging Configuration: `src/constants/__init__.py`

The application uses Python's standard logging module with centralized configuration:

```python
# Log files are created with timestamps in format:
# polyglot_YYYYMMDD_HHMMSS.log

# Example: polyglot_20240322_143022.log

# Log level: INFO (shows info, warnings, and errors; hides debug messages)
# Format: [TIMESTAMP] [LOGGER_NAME] [LEVEL] message
```

### Customization Guide

#### Change Ollama Connection Details

Edit `src/constants/constants.py`:

```python
# To connect to remote Ollama server
HOST: str = "192.168.1.100"  # Remote server IP
PORT: int = 11434            # Must be same port

# To use different model
MODEL: str = "llama2"        # Any model available via ollama pull
```

#### Change Model and Performance

```python
# For faster (less accurate) translation
MODEL: str = "mistral"            # Smaller, faster model

# For better (slower) translation
MODEL: str = "neural-chat"        # Larger, more accurate model

# Check available models
ollama list
```

#### Adjust Logging Level

Edit `src/constants/__init__.py`:

```python
# Change from INFO to DEBUG for more verbose logs
logging.getLogger().setLevel(logging.DEBUG)  # Shows all messages

# Change to WARNING to show only warnings and errors
logging.getLogger().setLevel(logging.WARNING)
```

#### Run on Different Port

Edit `src/app/__init__.py`:

```python
def main(host: str = "0.0.0.0", port: int = 9000):  # Changed from 8000
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
```

---

## Filters & Controls Reference

### POST `/translate` Endpoint

**Description**: Translates a given text into multiple target languages simultaneously.

**Request Format**

| Parameter          | Type             | Required | Description                              | Example                           |
| ------------------ | ---------------- | -------- | ---------------------------------------- | --------------------------------- |
| `text`             | string           | ✅ Yes   | The text content to translate            | `"Hello, how are you?"`           |
| `target_languages` | array of strings | ✅ Yes   | List of language names to translate into | `["Spanish", "French", "German"]` |

**Request Example**

```bash
curl -X POST http://localhost:8000/translate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "This is my first project",
    "target_languages": ["Spanish", "French", "German"]
  }'
```

**Response Format**

| Field                        | Type             | Description                                                           |
| ---------------------------- | ---------------- | --------------------------------------------------------------------- |
| `id`                         | string           | Unique identifier for this translation task (format: `polyglot_XXXX`) |
| `text`                       | string           | The original input text (echoed back for verification)                |
| `translations`               | array of objects | Array of translation results                                          |
| `translations[].language`    | string           | Target language name                                                  |
| `translations[].translation` | string           | Translated text in target language                                    |
| `error` (if applicable)      | string           | Error message if translation failed                                   |

**Response Example - Success**

```json
{
  "id": "polyglot_4521",
  "text": "This is my first project",
  "translations": [
    {
      "language": "Spanish",
      "translation": "Este es mi primer proyecto"
    },
    {
      "language": "French",
      "translation": "C'est mon premier projet"
    },
    {
      "language": "German",
      "translation": "Dies ist mein erstes Projekt"
    }
  ]
}
```

**Response Example - Error (Missing Parameters)**

```json
{
  "error": "Invalid input. 'text' and 'target_languages' are required."
}
```

**Response Example - Error (LLM Failure)**

```json
{
  "id": "polyglot_4521",
  "text": "This is my first project",
  "translations": [],
  "error": "Connection refused: Failed to connect to Ollama at localhost:11434"
}
```

**HTTP Status Codes**

| Code  | Meaning               | Scenario                                                          |
| ----- | --------------------- | ----------------------------------------------------------------- |
| `200` | Success               | Translation completed (check response for errors in translations) |
| `400` | Bad Request           | Invalid JSON format or missing required parameters                |
| `422` | Unprocessable Entity  | Request body doesn't match expected schema                        |
| `500` | Internal Server Error | Unexpected server error (check logs)                              |

**Advanced Parameters (URL Query)**

These optional query parameters can be appended to the URL:

| Parameter     | Type    | Default | Description                                      |
| ------------- | ------- | ------- | ------------------------------------------------ |
| `max_tokens`  | integer | 512     | Maximum tokens in LLM response                   |
| `temperature` | float   | 0.7     | LLM creativity (0.0=deterministic, 1.0=creative) |

**Example with Advanced Parameters**

```bash
curl -X POST "http://localhost:8000/translate?temperature=0.5" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Be creative and translate this",
    "target_languages": ["Spanish", "French"]
  }'
```

**Rate Limiting & Concurrency**

- **Current**: No rate limiting enforced
- **Recommended for Production**: Implement requests/minute limits (e.g., 100 req/min per IP)
- **Concurrent Translations**: Processing 1-5 target languages typically completes within 5-15 seconds

---

## Usage Examples

### Example 1: Basic Single Language Translation

**Scenario**: Translate English text to Spanish.

```bash
curl -X POST http://localhost:8000/translate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, world!",
    "target_languages": ["Spanish"]
  }'
```

**Expected Output**:

```json
{
  "id": "polyglot_7382",
  "text": "Hello, world!",
  "translations": [
    {
      "language": "Spanish",
      "translation": "¡Hola, mundo!"
    }
  ]
}
```

---

### Example 2: Multiple Language Translation

**Scenario**: Translate a product description to multiple languages for international e-commerce.

```bash
curl -X POST http://localhost:8000/translate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Premium wireless headphones with active noise cancellation",
    "target_languages": ["Spanish", "French", "German", "Japanese", "Mandarin Chinese"]
  }'
```

**Expected Output**:

```json
{
  "id": "polyglot_1234",
  "text": "Premium wireless headphones with active noise cancellation",
  "translations": [
    {
      "language": "Spanish",
      "translation": "Auriculares inalámbricos premium con cancelación de ruido activa"
    },
    {
      "language": "French",
      "translation": "Casques sans fil premium avec réduction active du bruit"
    },
    {
      "language": "German",
      "translation": "Premium-Wireless-Kopfhörer mit aktiver Geräuschunterdrückung"
    },
    {
      "language": "Japanese",
      "translation": "アクティブノイズキャンセレーション機能付きプレミアムワイヤレスヘッドフォン"
    },
    {
      "language": "Mandarin Chinese",
      "translation": "具有主动降噪功能的优质无线耳机"
    }
  ]
}
```

**Expected Performance**: 8-15 seconds for 5 languages (depends on model and hardware)

---

### Example 3: Using Python Client

**Scenario**: Integrate translation into a Python application.

```python
import requests
import json

def translate_text(text, target_languages):
    """
    Translate text to multiple languages using Polyglot API.

    Args:
        text (str): Text to translate
        target_languages (list): List of target language names

    Returns:
        dict: Translation result with structure:
            {
                "id": "polyglot_XXXX",
                "text": "original text",
                "translations": [
                    {"language": "Spanish", "translation": "..."},
                    ...
                ]
            }
    """

    url = "http://localhost:8000/translate"

    payload = {
        "text": text,
        "target_languages": target_languages
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()  # Raise exception for HTTP errors
        return response.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Failed to connect to Polyglot API at http://localhost:8000"}
    except requests.exceptions.Timeout:
        return {"error": "Request timeout after 30 seconds"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP error: {e.response.status_code}"}


# Usage
result = translate_text(
    "Welcome to our application",
    ["Spanish", "French", "German"]
)

if "error" in result:
    print(f"Error: {result['error']}")
else:
    print(f"Translation ID: {result['id']}")
    for translation in result['translations']:
        print(f"{translation['language']}: {translation['translation']}")
```

**Expected Output**:

```
Translation ID: polyglot_5647
Spanish: Bienvenido a nuestra aplicación
French: Bienvenue dans notre application
German: Willkommen in unserer Anwendung
```

---

### Example 4: Error Handling

**Scenario**: Handle errors gracefully when Ollama is not running.

```python
import requests
import json

payload = {
    "text": "Translation attempt",
    "target_languages": ["Spanish", "French"]
}

try:
    response = requests.post(
        "http://localhost:8000/translate",
        json=payload,
        timeout=5
    )

    result = response.json()

    # Check if translation succeeded
    if "error" in result:
        print(f"Translation failed: {result['error']}")
    else:
        # Process successful translations
        for translation in result['translations']:
            print(f"{translation['language']}: {translation['translation']}")

except requests.exceptions.ConnectionError:
    print("Error: Cannot connect to API. Is the server running?")
    print("Start with: polyglotapi")

except requests.exceptions.Timeout:
    print("Error: Request timed out. Server may be busy.")

except json.JSONDecodeError:
    print("Error: Server returned invalid JSON")
    print(f"Raw response: {response.text}")
```

---

### Example 5: Batch Processing File

**Scenario**: Translate content from a text file to multiple languages.

```python
import requests
import json
from pathlib import Path

def translate_file(input_file, output_file, target_languages):
    """
    Translate text from a file and write results to output file.

    Args:
        input_file (str): Path to input text file
        output_file (str): Path to output JSON file
        target_languages (list): Target language names
    """

    # Read input text
    with open(input_file, 'r', encoding='utf-8') as f:
        text = f.read().strip()

    # Call translation API
    response = requests.post(
        "http://localhost:8000/translate",
        json={
            "text": text,
            "target_languages": target_languages
        }
    )

    result = response.json()

    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"✓ Translation complete. Results saved to {output_file}")

    # Summary
    if "translations" in result:
        print(f"  Original ID: {result['id']}")
        print(f"  Languages translated: {len(result['translations'])}")
        for t in result['translations']:
            print(f"    - {t['language']}")


# Usage
translate_file(
    "input.txt",
    "translations.json",
    ["Spanish", "French", "German", "Portuguese"]
)
```

---

### Example 6: Using Direct Python Functions

**Scenario**: Call translation functions directly without HTTP server.

```python
# Ensure virtual environment is activated
# Make sure Ollama is running (ollama serve in another terminal)

import sys
sys.path.insert(0, 'src')

from helper.helper import translate_to_languages
from constants.constants import HOST, PORT, MODEL

# Direct function call (bypasses FastAPI)
result = translate_to_languages(
    text="Good morning, how are you today?",
    target_languages=["Spanish", "French", "Italian"],
    host=HOST,
    port=PORT,
    model=MODEL
)

print(json.dumps(result, indent=2, ensure_ascii=False))
```

**Expected Output**:

```json
[
  {
    "id": "polyglot_9234",
    "text": "Good morning, how are you today?",
    "translations": [
      {
        "language": "Spanish",
        "translation": "Buenos días, ¿cómo estás hoy?"
      },
      {
        "language": "French",
        "translation": "Bonjour, comment allez-vous aujourd'hui?"
      },
      {
        "language": "Italian",
        "translation": "Buongiorno, come stai oggi?"
      }
    ]
  }
]
```

---

## API Reference

### Core Functions

#### `translate_to_languages()`

**Module**: `src/helper/helper.py`

**Description**: Main translation orchestration function. Handles concurrent translation requests to LLM.

**Signature**:

```python
def translate_to_languages(
    text: str,
    target_languages: list[str],
    host: str = HOST,
    port: int = PORT,
    model: str = MODEL,
    api_key: str = API_KEY
) -> dict
```

**Parameters**:

| Parameter          | Type      | Default                    | Description                              |
| ------------------ | --------- | -------------------------- | ---------------------------------------- |
| `text`             | str       | -                          | Source text to translate (required)      |
| `target_languages` | list[str] | -                          | List of target language names (required) |
| `host`             | str       | `"localhost"`              | Ollama server hostname                   |
| `port`             | int       | `11434`                    | Ollama server port                       |
| `model`            | str       | `"qwen3-coder:480b-cloud"` | LLM model identifier                     |
| `api_key`          | str       | `"ollama"`                 | API key for Ollama authentication        |

**Returns**:

```python
list[dict]  # List containing single dict with structure:
# [
#   {
#     "id": "polyglot_XXXX",
#     "text": "original text",
#     "translations": [
#       {"language": "Spanish", "translation": "..."},
#       {"language": "French", "translation": "..."}
#     ]
#   }
# ]
```

**Raises**:

- `Exception`: If LLM query fails; error is caught and returned in response

**Example**:

```python
from helper.helper import translate_to_languages

result = translate_to_languages(
    text="Hello world",
    target_languages=["Spanish", "French"]
)

print(result)
# Output: [{'id': 'polyglot_1234', 'text': 'Hello world', 'translations': [...]}]
```

---

#### `query_llm()`

**Module**: `src/helper/helper.py`

**Description**: Sends a single translation query to the LLM via Ollama's OpenAI-compatible endpoint.

**Signature**:

```python
def query_llm(
    host: str,
    port: int,
    payload: dict,
    model: str = MODEL,
    api_key: str = API_KEY
) -> dict
```

**Parameters**:

| Parameter | Type | Description                                                    |
| --------- | ---- | -------------------------------------------------------------- |
| `host`    | str  | Ollama server hostname                                         |
| `port`    | int  | Ollama server port                                             |
| `payload` | dict | Translation task payload with `id`, `text`, `target_languages` |
| `model`   | str  | LLM model identifier (default: from constants)                 |
| `api_key` | str  | API key for authentication (default: from constants)           |

**Returns**:

```python
dict  # Structure:
# {
#   "id": "polyglot_XXXX",
#   "text": "original text",
#   "translations": [
#     {"language": "Spanish", "translation": "..."},
#     ...
#   ]
# }
# OR on error:
# {
#   "id": "polyglot_XXXX",
#   "text": "original text",
#   "translations": [],
#   "error": "error message"
# }
```

**Raises**:

- `openai.APIError`: If OpenAI/Ollama API request fails
- `openai.AuthenticationError`: If API key is invalid
- `openai.APIConnectionError`: If cannot connect to Ollama server
- `json.JSONDecodeError`: If response cannot be parsed as JSON

**Example**:

```python
from helper.helper import query_llm

payload = {
    "id": "polyglot_001",
    "text": "Hello",
    "target_languages": ["Spanish"]
}

result = query_llm(
    host="localhost",
    port=11434,
    payload=payload,
    model="qwen3-coder:480b-cloud"
)

if "error" in result:
    print(f"Error: {result['error']}")
else:
    print(result['translations'])
```

---

#### `prepare_payload()`

**Module**: `src/helper/helper.py`

**Description**: Prepares a translation task payload with unique ID for tracking.

**Signature**:

```python
def prepare_payload(text: str, target_languages: list[str]) -> dict
```

**Parameters**:

| Parameter          | Type      | Description              |
| ------------------ | --------- | ------------------------ |
| `text`             | str       | Source text to translate |
| `target_languages` | list[str] | Target language names    |

**Returns**:

```python
dict  # Structure:
# {
#   "id": "polyglot_XXXX",  # Unique ID from generate_id()
#   "text": "source text",
#   "target_languages": ["Spanish", "French", ...]
# }
```

**Example**:

```python
from helper.helper import prepare_payload

payload = prepare_payload(
    text="Good morning",
    target_languages=["Spanish", "French"]
)

print(payload)
# Output: {
#   'id': 'polyglot_7382',
#   'text': 'Good morning',
#   'target_languages': ['Spanish', 'French']
# }
```

---

#### `generate_id()`

**Module**: `src/helper/helper.py`

**Description**: Generates unique identifier for translation tasks.

**Signature**:

```python
def generate_id() -> str
```

**Returns**:

```python
str  # Format: "polyglot_XXXX" where XXXX is random 4-digit number
```

**Example**:

```python
from helper.helper import generate_id

id1 = generate_id()
id2 = generate_id()

print(id1)  # Output: polyglot_3847
print(id2)  # Output: polyglot_5921
```

---

### FastAPI Endpoints

#### POST `/translate`

**Module**: `src/app/main.py`

**Description**: HTTP endpoint for submitting translation requests.

**Signature**:

```python
@app.post("/translate", operation_id="translate")
async def translate_text(
    payload: dict = Body(
        default={"text": "", "target_languages": []}
    )
) -> JSONResponse
```

**Request Body**:

```json
{
  "text": "Text to translate",
  "target_languages": ["Language1", "Language2"]
}
```

**Response Body**:

```json
{
  "id": "polyglot_XXXX",
  "text": "original text",
  "translations": [{ "language": "Spanish", "translation": "..." }]
}
```

**Status Codes**:

- `200 OK`: Translation processed (check response for errors)
- `400 Bad Request`: Missing required parameters
- `422 Unprocessable Entity`: Invalid request format
- `500 Internal Server Error`: Server error (check logs)

**Example**:

```bash
curl -X POST http://localhost:8000/translate \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello", "target_languages": ["Spanish"]}'
```

---

### Configuration Constants

**Module**: `src/constants/constants.py`

```python
HOST: str = "localhost"              # Ollama server hostname
PORT: int = 11434                    # Ollama server port
MODEL: str = "qwen3-coder:480b-cloud"  # Model identifier
API_KEY: str = "ollama"              # API key for Ollama

PROMPT: str = """
You are a helpful assistant...
[System prompt for translation instruction]
"""
```

---

## Testing & Troubleshooting

### Manual Testing

#### Test 1: Verify API Server is Running

```bash
# Check if FastAPI server is accessible
curl -s http://localhost:8000/docs > /dev/null && echo "✓ Server running" || echo "✗ Server not running"

# Get formatted JSON response (pipe through jq if available)
curl -s http://localhost:8000 | jq .
```

#### Test 2: Verify Ollama Connection

```bash
# Check if Ollama is running
curl -s http://localhost:11434/api/tags | jq .

# Check if required model is available
curl -s http://localhost:11434/api/tags | jq '.models[] | select(.name | contains("qwen3"))'
```

#### Test 3: Basic Translation Request

```bash
# Simple English to Spanish translation
curl -X POST http://localhost:8000/translate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello",
    "target_languages": ["Spanish"]
  }' | jq .
```

#### Test 4: Multiple Language Translation

```bash
# Complex multi-language translation
curl -X POST http://localhost:8000/translate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "The quick brown fox jumps over the lazy dog",
    "target_languages": ["Spanish", "French", "German", "Italian", "Portuguese"]
  }' | jq '.translations[] | "\(.language): \(.translation)"'
```

#### Test 5: Error Scenarios

**Missing required parameter**:

```bash
curl -X POST http://localhost:8000/translate \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello"}'
# Expected: {"error": "Invalid input..."}
```

**Ollama not running**:

```bash
# Kill Ollama first: pkill ollama
curl -X POST http://localhost:8000/translate \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello", "target_languages": ["Spanish"]}'
# Expected: Error response with connection refused message
```

---

### Troubleshooting Common Issues

#### Issue 1: `ssl.SSLError: unknown error (_ssl.c:3036)`

**Symptom**:

```
ssl.SSLError: unknown error (_ssl.c:3036)
```

**Root Cause**: The OpenAI client attempts SSL context initialization even for HTTP localhost connections.

**Solution** (Already Applied):

The application includes workarounds in [src/helper/helper.py](src/helper/helper.py):

- Uses `httpx.Client` with `verify=False` for local connections
- Disables SSL/TLS verification for Ollama endpoint

If you encounter this, ensure you have certifi installed:

```bash
pip install certifi
# OR with uv
uv pip install certifi
```

---

#### Issue 2: Connection Refused to Ollama

**Symptom**:

```json
{
  "error": "Connection refused: Failed to connect to Ollama at localhost:11434"
}
```

**Solution**:

1. **Verify Ollama is running**:

```bash
ps aux | grep -i ollama
# Should show ollama serve process

# Or check port
lsof -i :11434
# Should show ollama listening
```

2. **Start Ollama if not running**:

```bash
ollama serve
# In macOS: Open Ollama.app from Applications
```

3. **Verify model is pulled**:

```bash
ollama list
# Should show qwen3-coder:480b-cloud

# If not present, pull it
ollama pull qwen3-coder:480b-cloud
```

4. **Check network connectivity**:

```bash
curl -v http://localhost:11434/api/tags
# Should show model tags without SSL/connection errors
```

---

#### Issue 3: Model Not Found

**Symptom**:

```json
{
  "error": "model 'qwen3-coder:480b-cloud' not found"
}
```

**Solution**:

```bash
# Check available models
ollama list

# If not shown, pull the model
ollama pull qwen3-coder:480b-cloud

# Or change to available model in constants
# Edit src/constants/constants.py
MODEL = "mistral"  # Or any available model
```

---

#### Issue 4: Translation Endpoint Returns Empty Translations

**Symptom**:

```json
{
  "id": "polyglot_1234",
  "text": "Hello",
  "translations": [],
  "error": "json.decoder.JSONDecodeError: ..."
}
```

**Root Cause**: LLM response is not valid JSON for some reason.

**Solution**:

1. **Check LLM directly**:

```bash
curl -X POST http://localhost:11434/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3-coder:480b-cloud",
    "messages": [{"role": "user", "content": "Translate \"Hello\" to Spanish"}],
    "stream": false
  }'
```

2. **Check logs for detailed error**:

```bash
# View latest log file
tail -100 logs/polyglot_*.log | grep -i "error\|exception"
```

3. **Check system resources**:

```bash
# Verify GPU/RAM availability
nvidia-smi  # For NVIDIA GPU
free -h     # Check memory
```

---

#### Issue 5: Server Slow or Timing Out

**Symptom**:

```
Request timeout after 30 seconds
```

**Root Cause**: Model inference is taking too long (common for large models on CPU).

**Solutions**:

1. **Check system resources**:

```bash
# Monitor CPU/memory while translation is running
top
# Check GPU usage
nvidia-smi watch -n 1
```

2. **Use faster model**:

```python
# Edit src/constants/constants.py
MODEL = "mistral"  # Faster than qwen3-coder:480b

# Or pull a smaller model
ollama pull phi
```

3. **Increase timeout**:

```python
# Edit src/helper/helper.py, line with timeout parameter
client = OpenAI(
    base_url=f"{schema}://{host}:{port}/v1",
    api_key=api_key,
    timeout=120,  # Increased from 90
)
```

4. **Increase server thread pool**:

```bash
# Start server with more workers
uvicorn src.app.main:app --workers 4 --reload
```

---

### Viewing Logs

**Log File Location**: `logs/polyglot_*.log`

```bash
# View latest log file
tail -f logs/polyglot_*.log

# View specific error
grep "ERROR" logs/polyglot_*.log

# View translation requests/responses
grep "Querying LLM\|LLM Response" logs/polyglot_*.log

# View all logs from today
find logs -name "polyglot_$(date +%Y%m%d)_*.log" -exec cat {} \;
```

---

### Getting Help

If you encounter issues:

1. **Collect diagnostic information**:

```bash
# System info
python --version
ollama --version
curl -s http://localhost:11434/api/tags | jq .

# Last 50 lines of logs
tail -50 logs/polyglot_*.log

# Last successful translation
grep "LLM Response" logs/polyglot_*.log | tail -1
```

2. **Create GitHub Issue** with:
   - Error message (full traceback)
   - Output of above diagnostic commands
   - Steps to reproduce
   - Expected vs actual behavior

---

## Contributing Guidelines

We welcome contributions from the community! This section explains how to contribute to Polyglot.

### Development Setup

1. **Clone and navigate to repo**:

```bash
git clone https://github.com/adarshbattu109/polyglot.git
cd polyglot
```

2. **Create development branch**:

```bash
git checkout -b feature/your-feature-name
# OR for bug fixes
git checkout -b bugfix/brief-description
```

3. **Create and activate virtual environment**:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

4. **Install in editable mode with dev dependencies**:

```bash
pip install -e ".[dev]"
# OR with uv
uv sync
```

### Code Style & Standards

We follow these conventions:

- **Language**: Python 3.12+
- **Style**: PEP 8 (Python Enhancement Proposal 8)
- **Docstrings**: Google-style docstrings with type hints
- **Line Length**: 100 characters max
- **Imports**: Organized with isort

### Making Changes

1. **Create feature branch** (from `main`):

```bash
git checkout -b feature/add-streaming-support
```

2. **Make changes to code**:

```bash
# Edit files in src/ directory
vim src/helper/helper.py
```

3. **Add/update tests** (when testing infrastructure is added):

```bash
# Create test file for your changes
touch tests/test_feature_name.py

# Run tests locally
pytest
```

4. **Update documentation**:

- If adding new functions: Update [API Reference](#api-reference) section in README
- If changing behavior: Update relevant sections in this README
- Add examples if applicable

5. **Commit changes with descriptive message**:

```bash
git add src/helper/helper.py README.md
git commit -m "feat: add streaming translation support

- Implement WebSocket endpoint for streaming translations
- Add incremental translation chunks
- Reduce response time for long texts
- Closes #42"
```

### Commit Message Convention

Follow conventional commits format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring (no behavior change)
- `perf`: Performance improvements
- `test`: Adding/updating tests
- `chore`: Maintenance (dependencies, configs, etc.)

**Example**:

```
feat(api): Add rate limiting middleware

- Implement token-bucket rate limiter
- Allow 100 requests per minute per IP
- Return 429 Too Many Requests on limit exceeded

Closes #35
```

### Pull Request Process

1. **Push branch to GitHub**:

```bash
git push origin feature/your-feature-name
```

2. **Create Pull Request**:

- Go to GitHub repository
- Click "New Pull Request"
- Select `main` as base branch
- Fill out PR template with:
  - **Description**: What changes were made and why
  - **Type**: feat/fix/docs/refactor
  - **Testing**: How was this tested
  - **Screenshots**: If UI changes (future when Streamlit UI added)

3. **PR Title Convention**:

```
[FEATURE] Add WebSocket streaming support
[FIX] Handle Ollama connection errors gracefully
[DOCS] Update README with troubleshooting guide
```

4. **PR Description Template**:

```markdown
## Description

Brief description of changes and motivation.

## Type of Change

- [ ] New feature
- [ ] Bug fix
- [ ] Documentation update
- [ ] Refactoring (no behavior change)
- [ ] Performance improvement

## Testing

How was this tested? Describe the test scenarios.

## Checklist

- [ ] Code follows style guidelines (PEP 8)
- [ ] Changes include documentation updates
- [ ] Self-reviewed the code
- [ ] Added/updated comments for complex logic
- [ ] No new warnings generated
- [ ] Tested locally with Python 3.12+
- [ ] Existing functionality still works
```

5. **Address review feedback**:

```bash
# Make requested changes
vim src/helper/helper.py

# Commit changes
git commit -m "refactor: address PR review feedback"

# Push updates (no need for another PR)
git push origin feature/your-feature-name
```

6. **Merge after approval**:

Maintainers will merge PR once approved.

### Bug Reporting

Found a bug? Please report it:

1. **Check if issue already exists** on GitHub Issues
2. **Create new issue** with:
   - **Title**: Brief description of bug
   - **Environment**: Python version, OS, Python dependencies list
   - **Steps to Reproduce**: Clear steps to reproduce the issue
   - **Expected Behavior**: What should happen
   - **Actual Behavior**: What actually happened
   - **Error Message**: Full traceback if applicable
   - **Screenshots**: If relevant

### Feature Requests

Have an idea? Suggest it:

1. **Create GitHub Issue** with label `enhancement`
2. **Title**: Brief description of feature
3. **Motivation**: Why is this feature needed?
4. **Proposed Solution**: How might it work?
5. **Alternatives**: Other approaches you considered

### Getting Help During Development

- **Questions**: Create GitHub Discussion
- **Documentation**: See README and inline code comments
- **Debugging**: Check logs in `logs/` directory
- **Testing**: Run manual tests as described in [Testing & Troubleshooting](#testing--troubleshooting)

---

## Authors & Maintainers

### Project Creator

- **Adarsh Battu** - [@adarsh-battu](https://github.com/adarsh-battu)
  - Email: adarsh.battu109@gmail.com
  - Role: Original Author & Primary Maintainer

### Metadata

This information is sourced from [pyproject.toml](pyproject.toml):

```toml
[project]
name = "polyglot"
version = "0.1.0"
description = "Polyglot helps you translate text into multiple languages at once"
authors = [
    { name = "Adarsh Battu", email = "adarsh.battu109@gmail.com" }
]
```

### Contributing Team

We recognize all contributors who have helped improve Polyglot. Contributors will be listed here (to be updated as community grows).

---

## License

This project is licensed under the [MIT License](LICENSE) - see LICENSE file for details.

The MIT License permits:

- ✅ Commercial use
- ✅ Modification
- ✅ Distribution
- ✅ Private use

With conditions:

- © License and copyright notice must be included

---

## Acknowledgments

- **Ollama** (https://ollama.ai) - For making LLM inference simple and accessible
- **FastAPI** (https://fastapi.tiangolo.com) - For the modern Python web framework
- **OpenAI** (https://openai.com) - For the Python client library
- **Qwen Team** - For the qwen3-coder language model
- The open-source community for tools and libraries that made this possible

---

## Future Roadmap

### Planned Features (v0.2.0+)

- 🔄 **Streaming Responses**: WebSocket support for real-time incremental translations
- 🎨 **Streamlit UI**: Web interface for non-technical users
- 📁 **Batch File Processing**: Translate entire documents/directories
- ⚡ **Caching Layer**: Redis-based caching for repeated translations
- 🔐 **Authentication**: API key management and rate limiting per user
- 📊 **Metrics & Monitoring**: Prometheus metrics for production observability
- 🐘 **PostgreSQL Backend**: Persist translation history and analytics
- 🐳 **Docker Support**: Pre-built Docker images for easy deployment
- 🌐 **Multi-LLM Support**: Easy switching between multiple local LLM providers
- 🎯 **Domain-Specific Models**: Fine-tuned models for specialized vocabulary
- 📱 **GraphQL API**: Alternative to REST API for flexible queries

---

## Support

- 📖 **Documentation**: See README (this file)
- 🐛 **Bug Reports**: GitHub Issues
- 💡 **Feature Requests**: GitHub Issues with label `enhancement`
- 💬 **Discussions**: GitHub Discussions
- 🤖 **Community Help**: Stack Overflow tag `polyglot-translation`

---

## Citation

If you use Polyglot in your research or project, please cite:

```bibtex
@software{battu2026polyglot,
  title={Polyglot: Multi-Language Translation API},
  author={Battu, Adarsh},
  year={2026},
  url={https://github.com/adarshbattu109/polyglot}
}
```

---

**Last Updated**: March 22, 2024  
**Version**: 0.1.0  
**Status**: Beta (Production-ready with active development)

For the latest updates, visit the [GitHub repository](https://github.com/adarshbattu109/polyglot).
