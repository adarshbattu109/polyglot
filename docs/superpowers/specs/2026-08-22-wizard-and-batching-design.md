# Wizard, file upload, and batched translation

**Date:** 2026-08-22
**Status:** approved design, not yet implemented

## Problem

Three things, one change:

1. The UI is a single scrolling form. Components overlap, and the ordering constraint
   (connect before translate) is enforced by a disabled `<fieldset>` rather than by structure.
2. Translation only accepts pasted text. Users have spreadsheets.
3. A naive file loop is one LLM request per row. For a 200-row sheet that is 200 requests and
   ~23,000 tokens of repeated system prompt before a single word is translated.

The single-text path is already optimal: all N target languages travel in one request, because
`target_languages` is a list in the payload. Nothing about that changes.

## Scale and limits

| Limit | Value | Why |
|---|---|---|
| Rows per upload | 200 | Beyond this a sequential run stops feeling interactive and wants a job store, which is a different feature. |
| Words per pasted text | 2,000 | ~2,600 input tokens; at 5 languages ~13,000 output tokens, the point where a single reply risks truncating mid-sentence. Truncation is worse than refusal because it looks like success. |
| Rows per batch | 25 | ~1,900 output tokens per reply — inside every model's comfortable range. |
| Concurrent requests | 4 | Hosted providers rate-limit; 8 in flight on a free tier earns a 429 that costs more in retries than the concurrency saves. |

Both limits are enforced twice: in the browser for feedback, and on the server as the real
check. The server message names the actual count.

## Why batch 25 rather than 1 or all

200-row sheet, 5 languages, ~40% duplicate cells (135 distinct):

| Approach | Requests | Input tokens | Output tokens |
|---|---|---|---|
| Per row | 200 | 26,600 | 15,000 |
| Batch 25 | 8 | 3,368 | 15,000 |
| Batch 25 + dedupe | 6 | 2,346 | 10,125 |
| Whole file, one request | 1 | 2,521 | 15,000 |

Batching amortises the system prompt, which is the only genuinely wasteful part of the cost.
Output tokens are irreducible — every translation must be generated once.

One request for the whole file saves 7% of input over batch-25 and risks everything: a ~15,000
token single reply exceeds `gpt-4o-mini`'s 16k output cap, and one malformed character loses all
200 rows. Rejected.

Dedupe is free and independent of batch size: translate each distinct string once, map the
result back to every row that had it.

## Architecture

Three modules, each with one job.

### `helper/fileops.py` — pandas in, pandas out

Currently an empty file already named for this. Knows nothing about LLMs.

- `read_upload(data: bytes, filename: str) -> DataFrame` — dispatches on extension to
  `read_csv` / `read_excel` / `read_json`. pandas gives all three formats one interface, so the
  three formats are one code path.
- `text_columns(df) -> list[str]` — object-dtype columns, for the picker.
- `to_download(df, format) -> bytes` — `to_csv` / `to_excel` / `to_json`.
- `template(format) -> bytes` — a 3-row example with a `text` column, so a user never has to
  guess the expected shape.

### `helper/batching.py` — token logic, no I/O, no network

- `plan(strings, batch_size=25) -> list[list[str]]` — order-preserving dedupe, then chunk.
- `estimate(strings, target_languages, batch_size=25) -> dict` — returns `requests`,
  `input_tokens`, `output_tokens`, `distinct_rows`, `duplicate_rows`.
- `apply(df, column, translations, languages) -> DataFrame` — maps distinct results back onto
  every row, adding one column per language.

Estimation uses `len(s.encode()) / 4` — **UTF-8 bytes, not characters**. `chars/4` estimates a
Telugu string at 8 tokens when the reality is nearer 21. This number exists to warn about
spend, so erring high is correct; an estimate that lies low is worse than no estimate. Output
is `distinct × languages × 1.3`, since translations usually run slightly longer than the source.

**Chat framing overhead, measured.** A live probe against `gpt-oss:120b` showed bytes/4 alone
under-counting input by 82%: a 58-byte prompt estimated at 14 tokens actually cost 80. The gap
is per-message role and format scaffolding that the payload text does not contain. The
estimator therefore adds a flat `MESSAGE_OVERHEAD = 40` tokens per message (2 messages per
request: system + user) on top of the byte estimate. Without it the estimate systematically
lies low, which is the one direction a spend warning must never err.

The estimate stays an estimate. See "Estimate vs actual" below.

### `helper/helper.py` — one new function

`translate_batch(texts, target_languages, ...)`: one request, a numbered list in,
`{"rows": [{"i": 0, "translations": {...}}]}` out. Indices are how rows are reassembled, so a
model that reorders its reply cannot scramble the output.

`translate_to_languages` is untouched. The single-text path does not regress.

### Endpoints

- `POST /upload` — parse and inspect only. Returns columns, row count, first 3 rows. No LLM
  call, so a user can see what was understood before spending anything.
- `POST /translate-file` — the batched run. Returns the full table plus a `spent` summary:
  requests made, rows translated, rows deduped, rows failed, and `input_tokens` /
  `output_tokens` summed from each batch's `response.usage`.

  **The file is sent twice.** `/upload` is inspect-only and keeps no state; `/translate-file`
  receives the file again as multipart along with the chosen column and languages. The
  alternative — a server-side session holding parsed DataFrames between two calls — buys one
  saved upload of a ≤200-row file in exchange for eviction policy, a memory leak risk, and
  state that outlives the request. Not worth it at this scale. Both endpoints stay stateless.
- `GET /template.{csv,xlsx,json}` — the fill-in templates.

Each gets an `operation_id` so it surfaces as an MCP tool, matching the existing endpoints.

## Concurrency

```python
with ThreadPoolExecutor(max_workers=4) as pool:
    futures = {pool.submit(translate_batch, chunk, ...): i for i, chunk in enumerate(chunks)}
    for future in as_completed(futures):
        ...
```

Same request count and same tokens as sequential — purely wall clock. 6 chunks sequentially is
~24s; with 4 workers, ~8s.

- The chunk index travels with the future, so `as_completed` returning out of order cannot
  scramble row order. Results reassemble by index, not by arrival.
- `translate_batch` constructs its own `OpenAI` client, so there is no shared mutable state
  across threads.
- Retry happens inside the worker, so one bad chunk does not serialise the rest.
- The endpoint stays `def`, not `async def` — FastAPI runs sync endpoints in a threadpool
  already and this nests correctly.

## Estimate vs actual

The OpenAI-compatible response already carries the provider's own count in `response.usage`
(`prompt_tokens`, `completion_tokens`, `total_tokens`), verified live against `gpt-oss:120b`.
This is the authoritative number, computed by the provider's real tokeniser, and it costs **no
extra request** — it is already in every reply we get back and is currently discarded.

`query_llm`, `translate_batch` and `detect_language` each read `response.usage` and return it.
The file run sums usage across all batches. Both numbers then appear together:

```
Tokens   estimated ~2,300 in / ~10,100 out
         actual     2,655 in /   9,041 out   (6 requests)
```

Showing both is the point. The estimate is what you decide on before spending; the actual is
what you were charged. Seeing them side by side is also how the estimator's accuracy gets
audited in real use rather than assumed.

**Disclaimer, shown in the UI wherever an estimate appears** — not buried in a tooltip:

> Estimates are approximate. Actual token counts come from the provider after each request and
> will differ, sometimes substantially. Do not use estimates for billing.

The wording is deliberate about "substantially": a model that pads its reply with prose, or
reasons before answering, can exceed an output estimate several times over. The live probe saw
102 actual output tokens against 16 estimated for exactly that reason. An estimate that
promises precision it cannot deliver is worse than one that admits its error bars.

If `usage` is absent — some self-hosted servers omit it — the actual column reads
"not reported by this endpoint" rather than zero. A missing count must not render as a free
request.

## Partial failure

A batch whose reply is malformed or short by rows gets **one retry**. Still bad, and those rows
come back with `error` set on them: visible in the table with an error marker, and present in
the download. Nothing silently vanishes.

Falling back to per-row for a bad batch was rejected — a failing 25-row batch would become 25
requests, the exact cost blow-up batching exists to prevent.

## The wizard

Three steps, one panel in the DOM flow at a time. Single-panel display is also what fixes the
reported overlap: nothing competes for vertical space any more.

**Step 1 — Connect.** Today's step 01 unchanged. Next stays disabled until `/verify` returns a
green verdict, so model configuration cannot be skipped.

**Step 2 — Input.** Either/or, and choosing one hides the other:
- *Type or paste* — textarea, Detect, live word counter (`142 / 2,000 words`, amber at 90%, red
  and blocking past the cap).
- *Upload a file* — drop zone for `.csv/.xlsx/.json`, plus a template download row. On drop,
  `POST /upload` returns columns and a preview; the column picker appears, pre-selecting a
  column named `text` if one exists. Non-selected columns pass through untouched into the
  download, so IDs and keys survive.

Language chips are shared by both paths.

Above the Translate button, once a file is parsed and languages chosen:

```
Estimate: 6 requests · ~2,300 input + ~10,100 output tokens
135 distinct rows (65 duplicates skipped)
Approximate. Actual counts come from the provider and will differ.
```

Recomputed on every language toggle and column change, so ticking a sixth language visibly
moves the number. The cost is on screen before the button, not in a log afterwards.

**Step 3 — Results.** Register for single text — one string in many scripts reads better as
parallel text. Table for files: source column plus one column per language, scrollable, with
CSV / Excel / JSON download above it. The `spent` summary sits beside the estimate so the guess
can be checked against reality.

The token line appears on **both** paths. A single text is one request, so its actual usage is
just that reply's `usage` — cheap to show and the same code path as the file summary. It also
gives the estimator a constant stream of single-request accuracy checks.

`translate_to_languages` gains usage in its return value but keeps its existing keys, so the
`/translate` response stays backward compatible and existing tests continue to pass.

`estimate` is deliberately not an endpoint. It is a pure function called by `/translate-file`
for its summary, and reimplemented in ~10 lines of JS for the live display. Two small
implementations beat a network round-trip on every checkbox click.

## Testing

`fileops` and `batching` are pure and get direct unit tests — no stubs needed:

- round-trip each format through `read_upload` → `to_download`
- a CSV with a non-Latin column, to catch the UTF-8 BOM and encoding handling
- `plan` dedupes order-preservingly and chunks to the right sizes
- `estimate` counts bytes not chars (the Telugu case above, asserted explicitly)
- `apply` maps a distinct translation onto every duplicate row
- 201 rows is a 422 naming the count; 2,001 words is a 422 naming the count

`translate_batch` extends the existing `FakeOpenAI` pattern in `test_helper.py`, which gains a
`usage` attribute:

- a reply missing a row triggers exactly one retry, then marks those rows failed
- a reply with reordered indices still reassembles correctly
- a batch run makes `ceil(distinct / 25)` requests, asserted by counting stub calls — this is
  the test that would catch a regression back to per-row
- `usage` is read through to the response, and summed across batches on a file run
- a reply with **no** `usage` block yields `None`, not `0` — asserted, because a silent zero
  would render as a free request in the UI

No test reaches the network, per the existing `conftest.py` contract.

## Out of scope

- Progress streaming (SSE/websocket). A 6-request run finishing in ~8s does not need it.
- A job store, cancellation, or resumable uploads. That is what the 200-row cap buys.
- A real tokeniser (`tiktoken` or similar). It is a dependency that diverges per provider, and
  `response.usage` already gives the exact count for free after the fact. The estimate only has
  to be good enough to decide with.
- Cost in currency. Per-model pricing changes without notice and would go stale in the repo.
  Tokens are the honest unit.
- Translating multiple columns at once.
