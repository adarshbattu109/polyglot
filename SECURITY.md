# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Reporting a Vulnerability

If you discover a security vulnerability in Polyglot, please report it responsibly:

1. **Do NOT open a public issue.**
2. Use [GitHub Private Vulnerability Reporting](https://github.com/adarshbattu109/polyglot/security/advisories/new) to submit a report.
3. Include: description, reproduction steps, impact assessment, and suggested fix (if any).

### Response Timeline

- **Acknowledgment:** Within 72 hours
- **Assessment:** Within 7 days
- **Fix/Disclosure:** Within 90 days (coordinated disclosure)

## Scope

Polyglot runs a local web server that forwards text to an OpenAI-compatible LLM endpoint. We
take the following seriously:

- **`/translate` connects wherever the caller tells it to — this is server-side request
  forgery by design.** `host`, `port`, `model` and `api_key` are accepted in the request body
  so the UI can point Polyglot at any OpenAI-compatible server; omitted fields fall back to
  the defaults in `src/polyglot/constants/constants.py`. There is no allowlist, so anyone who
  can reach `/translate` can make the server open a connection to any address it can route
  to — including `169.254.169.254` and other link-local metadata endpoints, and internal
  services behind a firewall the caller can't reach directly. The response reveals whether
  the connection succeeded, which makes it usable as a port scanner.

  This is an accepted trade-off **only** because the server binds loopback: `main()` defaults
  to `host="127.0.0.1"`, so the surface is limited to processes on your machine. Passing
  `host="0.0.0.0"` hands the capability to everyone on your network. Don't do that on a
  network you don't control, and don't expose Polyglot through a reverse proxy without
  putting an allowlist in front of `host`/`port` first.
- **`API_KEY` is a bearer credential and is read from the environment**, not committed:
  `API_KEY = os.getenv("POLYGLOT_API_KEY", "")`. Keep it in `.env.local`, which is gitignored,
  and load it with `uv run --env-file .env.local`. `.env.example` holds placeholders only. It
  is empty by default because a local Ollama doesn't need one.
- **A key sent from the UI travels over the `/translate` connection.** The browser posts it in
  the request body on every translate, and it is never stored client-side. `GET /config`
  deliberately returns only `host`/`port`/`model` — echoing a credential back to a caller
  would be a leak, and `tests/test_translate.py` asserts it isn't in the response. If you ever
  serve the UI over anything but `http://localhost`, that body needs TLS.
- **Logging runs at `DEBUG`** — `logging.basicConfig(level=logging.DEBUG)` in
  `src/polyglot/app/__init__.py` sets the *root* logger, so `openai` and `httpx` log at DEBUG too. That
  includes outbound request headers, which carry the `Authorization` header. `logs/` is
  gitignored, but treat log files as containing your key, and don't attach them to an issue
  without reading them first.
- **Text leaves the machine if you point it off-box.** With the default localhost Ollama,
  nothing does. Set Host to a remote provider — in the UI or in `constants.py` — and every
  string you translate goes to that party. Check their retention and training policy first,
  and note that any port other than 443 sends the text *and the key* in the clear:
  `query_llm` selects `https` only for port 443, and the UI's endpoint preview shows which
  scheme you'll get.
- **No authentication and no rate limiting.** `/translate` is open to anyone who can reach
  the port, and each call costs an LLM inference against whatever key it is given.
- **Untrusted text reaches the model as a prompt.** The input is interpolated into a JSON
  payload alongside the translation instructions, so a caller can attempt prompt injection to
  make the model ignore them. The blast radius is a wrong or non-compliant translation — the
  model has no tools and no side effects — but don't treat output as trustworthy or render it
  as HTML. The UI sets it via `textContent`, never `innerHTML`; keep it that way.
- **`/mcp` is mounted and unauthenticated.** `FastApiMCP` exposes the translate operation as
  a Model Context Protocol tool on the same server, with the same open access.
- **Supply chain** — dependencies are monitored via Dependabot and `pip-audit` in CI.

## Non-Goals

- Polyglot does not authenticate callers, rate-limit requests, or budget inference spend. It
  is a local translation service, not a multi-tenant API gateway.
- Polyglot does not restrict which LLM endpoint a request may name. Per-request routing is a
  feature here; on a shared or exposed deployment it is a vulnerability. See Scope.
- Polyglot does not guarantee translation accuracy. Output comes from an LLM and is not
  reviewed; don't rely on it for legal, medical, or safety-critical text.
- Polyglot does not sandbox the model's output. It is text from a third party, handled as
  text.
