# Contributing to Polyglot

Thanks for your interest. Polyglot is a small project — about 250 lines of real code — and
the aim is to keep it that way.

## Getting set up

Polyglot uses [uv](https://docs.astral.sh/uv/) for dependency management and Python 3.12.

```bash
git clone https://github.com/adarshbattu109/polyglot.git
cd polyglot
uv sync
```

You also need an OpenAI-compatible LLM server. [Ollama](https://ollama.com) is the default,
either locally:

```bash
ollama serve               # listens on localhost:11434
ollama pull gpt-oss:20b    # or whatever MODEL names in src/polyglot/constants/constants.py
```

…or against Ollama's hosted API, which needs a key:

```bash
cp .env.example .env.local     # then put your key in POLYGLOT_API_KEY
uv run --env-file .env.local polyglot
```

`.env.local` is gitignored; `.env.example` holds placeholders only. Set
`POLYGLOT_HOST=ollama.com` and `POLYGLOT_PORT=443` in it to make the cloud the default, or
just fill the UI's connection panel per request. Note that not every model listed by
`GET /v1/models` is available on every plan — a 403 saying "this model requires a
subscription" means pick another.

The UI's Provider list comes from `PROVIDERS` in `constants/constants.py`, so adding one is a
nine-field dict, not a code change. `path` is the field to watch: most providers serve their
OpenAI-compatible API under `/v1`, but Gemini uses `/v1beta/openai` and Groq `/openai/v1`.
`POLYGLOT_PATH` sets the server-side default for the same thing.

Run the server:

```bash
uv run polyglot                                # defaults to 127.0.0.1:8000
```

`main(host, port, reload)` in `src/polyglot/app/__init__.py` is the entry point. It binds
loopback and reloads on edit by default; see [SECURITY.md](SECURITY.md) before binding
`0.0.0.0`. Then open <http://localhost:8000> for the UI, or <http://localhost:8000/docs> for
the API.

The UI's **Model connection** panel sets Host, Port, Model and API key per request, prefilled
from `GET /config` with the defaults in `constants.py`. Leave a field blank to use its default.

### `CERTIFICATE_VERIFY_FAILED` on a corporate network

If a translation fails with `Connection error.` and the log shows `[SSL:
CERTIFICATE_VERIFY_FAILED] self-signed certificate in certificate chain`, you are behind a
TLS-intercepting proxy. `curl` works because it trusts the macOS keychain; `httpx` (under the
`openai` client) trusts certifi's bundle, which doesn't have your proxy's root CA. Export the
system roots and point Python at them:

```bash
security find-certificate -a -p /System/Library/Keychains/SystemRootCertificates.keychain > /tmp/roots.pem
security find-certificate -a -p /Library/Keychains/System.keychain >> /tmp/roots.pem
SSL_CERT_FILE=/tmp/roots.pem uv run --env-file .env.local polyglot
```

## Running the tests

```bash
uv run pytest
```

No test touches the network — `query_llm` is stubbed everywhere, including the cases that
assert on upstream-failure handling. A test that needs a running Ollama does not belong in
`tests/`; the suite finishes in well under a second and should stay that way.

## Before you open a PR

```bash
uv tool run ruff check .
uv tool run ruff format --check .
uv run pytest
```

CI runs exactly these three, plus `pip-audit` against the locked dependency set.

### PR titles

Titles must follow [Conventional Commits](https://www.conventionalcommits.org/) — CI rejects
anything else, and the title decides the version bump:

| Type | Bump | Example |
|------|------|---------|
| `feat` | minor | `feat: add a language allowlist` |
| `fix`, `perf`, `refactor` | patch | `fix(helper): handle a null message body` |
| `docs`, `style`, `test`, `build`, `ci`, `chore` | none | `docs: correct the response shape` |

A `!` after the type (`feat!:`) means a breaking change and bumps major. The version in
`pyproject.toml` is bumped automatically on your branch — don't edit it by hand.

## What gets merged

Polyglot deliberately does very little. A change that adds a dependency, a build step, or a
layer of indirection needs to justify its keep. Some specifics:

- **The frontend is one static HTML file** with inline CSS and vanilla JS, no build step and
  no CDN. It must work on a machine with no internet. Please don't introduce a framework.
- **`host`, `port`, `model` and `api_key` are caller-supplied, and that is deliberate** — the
  UI needs to aim at any OpenAI-compatible server. It also means `/translate` will connect
  wherever it is told to, which is why `main()` binds loopback by default. Don't change that
  default, and don't add a way to expose the server without an allowlist in front of
  `host`/`port`. See [SECURITY.md](SECURITY.md).
- **New behaviour needs a test.** One focused test that fails if the logic breaks is enough —
  no fixtures-for-the-sake-of-fixtures.
- **Keep the README honest.** It currently overstates things in places (it describes
  ThreadPoolExecutor-based concurrency that does not exist, and a `?temperature=` parameter
  the endpoint does not accept). If you touch a documented behaviour, fix the doc to match
  the code rather than the other way around.

## Reporting things

- **Bugs and features** — use the issue templates.
- **Security vulnerabilities** — don't open a public issue; see [SECURITY.md](SECURITY.md).
- **Never paste an `api_key`** into an issue or PR. Note that logging currently runs at
  `DEBUG`, so `logs/polyglot_*.log` may contain request headers — check before sharing.

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).
