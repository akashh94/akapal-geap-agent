# Session Handoff — 2026-09-17

Analysis-only session. **No code changed, nothing deployed, no commits made.**
One new document was added (untracked).

> This is a new handoff. The previous one — `SESSION_HANDOFF.md` — is from
> 2026-08-17/18 and documents the **Model A / Cloud Run** era against project
> `adk-tut-499512`. It is still referenced by `AGENT_RUNTIME_A2A.md`, so it was
> deliberately left untouched. Treat it as history, not current state.
>
> **Further change (2026-09-18).** The supervisor's app-served A2A surface was
> removed, and the planner's Cloud Run deployment was deleted. So §1's "public
> card" column and its rollback row are historical too — no Approach B
> deployment remains. See
> [`docs/AGENT_RUNTIME_A2A.md`](docs/AGENT_RUNTIME_A2A.md) for the current design.

---

## 1. Current state (verified this session)

### Identifiers

| Piece | Value |
|---|---|
| Project | `adk-tut-508714` (number `238721448932`), `us-central1` |
| MCP portfolio | `https://mcp-portfolio-238721448932.us-central1.run.app` |
| MCP registry entry | `projects/adk-tut-508714/locations/us-central1/mcpServers/agentregistry-00000000-0000-0000-bd9d-1747fbf2c9c1` |
| Planner engine | `.../reasoningEngines/6854616621567180800` |
| Supervisor engine | `.../reasoningEngines/5324518648168054784` |
| Staging bucket | `gs://geap-staging-238721448932` |

Note this is a **different project** from the old handoff. Everything in
`SESSION_HANDOFF.md` referencing `adk-tut-499512` / `...947331501288...` /
engine `5062056426524901376` is outdated.

### The three deployments

| Deployment | Approach | Repo | Public card | Role |
|---|---|---|---|---|
| Supervisor on Agent Runtime | app-served container | `akapal-geap-agent` | **Yes** | Inbound entry point |
| Planner on Agent Runtime | platform-native `A2aAgent` | `akapal-geap-financial-planner` | **No** | Answers the supervisor |
| Planner on Cloud Run | app-served container | `akapal-geap-financial-planner` | **Yes** | Rollback path, currently unused |

### The live call chain

```
client ──JSON-RPC──▶ supervisor (Agent Runtime, app-served A2A)
                          │  LLM decides to call call_financial_planner
                          ▼
                     app/tools/a2a_planner_tool.py
                          │  vertexai.Client().agent_engines.get(name=FINANCIAL_PLANNER_ENGINE)
                          │  await remote.on_message_send(SendMessageRequest(...))
                          ▼
                     planner (Agent Runtime, platform-native A2A)
                          │  A2aAgentExecutor → Runner
                          ▼
                     MCP portfolio (Cloud Run) — resolved via Agent Registry
```

### Deploy entry points

- **Supervisor**: `./deploy.personal.sh` → `agents-cli deploy --deployment-target agent_runtime` (manifest has `is_a2a: true`)
- **Planner**: `./deploy.personal.a2a.sh` → `uv run python deploy_a2a.py` (SDK object deploy)
- **Planner rollback**: `./deploy.personal.cloudrun.sh` (gcloud + docker)

---

## 2. Artifacts produced this session

| File | Status | Notes |
|---|---|---|
| `docs/AGENT_RUNTIME_A2A_APPROACHES.md` | **new, untracked** | First-principles comparison of the two deploy approaches |
| `docs/A2UI_BEGINNER_GUIDE.md` | untracked (pre-existing) | Not touched this session |
| `docs/A2UI_LEARNING_GUIDE.md` | untracked (pre-existing) | Not touched this session |

Verification run on the new doc:

```bash
ruff format --check docs/AGENT_RUNTIME_A2A_APPROACHES.md   # 1 file already formatted
ruff check docs/AGENT_RUNTIME_A2A_APPROACHES.md            # All checks passed
```

This matters — see §7 gotchas.

---

## 3. Questions answered this session

Short answers, in case any come up again.

**Q: How does the supervisor reach the planner?**
It doesn't import planner code. `call_financial_planner` resolves the planner
engine by resource name through the Agent Platform SDK and calls
`on_message_send`. Two separate cloud services speaking A2A.

**Q: How is the planner *discovered*?**
**It isn't.** There is no discovery. `_planner_engine()` reads
`FINANCIAL_PLANNER_ENGINE` from the environment — a value a human copied by hand
from deploy output into `deploy.personal.env`. `agent_engines.get(name=...)` is a
fetch-by-known-name, not a search. No card is fetched, no registry is queried.
The planner's own MCP hop *does* use real discovery (Agent Registry), but the
supervisor→planner hop does not.

**Q: What exactly is copied from the planner to the supervisor — a URL?**
**No URL. A resource name.** `deploy_a2a.py` prints three lines; only the
`A2A engine :` one is used:

```
projects/adk-tut-508714/locations/us-central1/reasoningEngines/6854616621567180800
```

The `A2A base` URL printed below it is debug output. The SDK rewrites the URL
from the resource name at connect time.

**Q: `deploy_a2a.py` or `deploy_a2a.sh`?**
Never run the `.py` directly — it needs `GOOGLE_CLOUD_PROJECT`,
`GOOGLE_CLOUD_LOCATION`, `STAGING_BUCKET` already exported. The `.sh` sources the
env file and sets those. Use `./deploy.personal.a2a.sh`.

**Q: Why is there a `.py` at all — previously only `.sh`?**
The old `.sh` scripts did `docker build` + `gcloud run deploy`, which shell can
do because a container is opaque. The A2A path is an **object deploy** — it
pickles a live Python object (`a2a_agent`) and uploads it. Shell cannot produce
that. The `.sh` still does the shell-shaped work (source env, translate var
names, `gcloud config set project`, `uv run python ...`).

**Q: What does the supervisor actually send on the wire?**
**Plain prose.** A single A2A `Message` with `role=ROLE_USER`, a fresh
`message_id="supervisor-<uuid4>"`, and one `Part(text=<the LLM's sentence>)`.
No function schemas, no structured parameters, no history, no `context_id`.
The executor's translation is mechanical: unwrap → `context.get_user_input()` →
re-wrap as a genai `Content` → `runner.run_async()`.

**Q: Is the current design the best option?**
Not as a whole. The deploy *method* is correct *given* the `A2aAgent` template —
object deploy is the only path that gets `agent_framework="a2a"` auto-detection
(source-files deploy defaults to `custom`, and `a2a` is not in the documented
supported-values list). But the template choice itself is questionable. See §4.

**Q: What is Agent Gateway?**
The networking component of GEAP — the entry/exit point for all agent traffic.
*"Agent Runtime and Gemini Enterprise automatically route agent traffic through
Agent Gateway,"* so both hops already traverse it. Two modes: Client-to-Agent
(ingress) and Agent-to-Anywhere (egress). IAP is the default enforcement layer
and is on by default (can run audit-only). Supports HTTP/MCP/A2A, but **only MCP
traffic is parsed for attribute-based policy** — A2A is passthrough, so no
per-message policy on the supervisor→planner hop.

---

## 4. Core finding: one fork explains both repos

The two repos look arbitrarily different. They aren't. Everything follows from a
single question — **who owns the HTTP surface?**

- **Approach A** (platform owns it): supply a card + executor, platform generates
  the server → `A2aAgent` → object deploy → no public card → must be addressed
  by name → pickling constraints → staging bucket → `extra_packages`.
- **Approach B** (we own it): supply a container → Dockerfile/image →
  `attach_a2a_routes()` → public card → discoverable → no serialization
  constraints → `agents-cli`.

The decisive asymmetry: **B can express everything A can** (we mount
`A2aAgentExecutor` ourselves — the executor is the same in both), but A cannot
express what B can, because A's operation set is closed and its card is not
public.

### Recommendation

Unify on **Approach B**, still on Agent Runtime. The planner's
`app/fast_api_app.py` + `Dockerfile` already *is* an Approach B deployment and
its Dockerfile already satisfies the runtime contract (`EXPOSE 8080`, binds
`${PORT:-8080}`). Moving it to Agent Runtime via `agents-cli` would remove:

- hardcoded `FINANCIAL_PLANNER_ENGINE` (→ real card discovery)
- `deploy_a2a.py` and the object-deploy machinery
- the GCS staging bucket
- `extra_packages` and the `No module named 'app.a2a_app'` failure class
- the pickling constraints on `build_runner` / `build_agent_executor`
- the `test-agent-engine` placeholder card URL
- the second deploy toolchain

**Bearing on the constraint "both agents must stay on GEAP":** this proposal
keeps both on Agent Runtime. App-served ≠ Cloud Run. The runtime contract
explicitly permits custom endpoints — *"Your container can expose any custom
HTTP endpoints"* — and the supervisor is already proof, since it is app-served
and deployed to Agent Runtime by agents-cli.

---

## 5. Open questions — verify before acting

None of these are settled. Do not treat the recommendation as ready.

1. **Does a containerised `A2aAgentExecutor` + custom routes behave identically
   to the object-deployed version?** This is the one experiment standing between
   §4 and action. Strong indirect evidence (the supervisor), but the planner's
   combination is untested.
2. **What does `is_a2a: true` in `agents-cli-manifest.yaml` actually generate?**
   Determines whether the platform registers its own A2A surface alongside ours.
3. **Are the app-served A2A routes GA or Preview?** Only the `A2aAgent`
   template's Pre-GA status is explicitly documented.
4. **Is `handle_authenticated_agent_card()` available in our pin
   (`google-cloud-aiplatform==1.163.0`)?** Current docs list it as a supported
   operation, contradicting `AGENT_RUNTIME_A2A.md` §9. If it works, Approach A's
   discovery gap narrows from "impossible" to "authenticated only".

---

## 6. Stale claims in `AGENT_RUNTIME_A2A.md` to fix

| Location | Claim | Reality |
|---|---|---|
| §9 | "`handle_authenticated_agent_card` does not exist" | Listed as a supported operation in current docs; likely a pin-version artefact |
| §9 | "the planner's card is not retrievable by any route we found" | Same; three documented retrieval paths exist |
| §2 | Two A2A kinds framed as a forced dichotomy | It's one design fork, and B is the superset |
| §4.1 | "The card is the *only* discovery mechanism A2A has" | True about A2A, misleading about this system — neither side reads the other's card |

`AGENT_RUNTIME_A2A_APPROACHES.md` §8 carries the same table.

---

## 7. Gotchas discovered this session

1. **`ruff format` reformats Python code blocks inside `.md` files**, and
   `agents-cli lint` runs it across the whole repo. A new doc with a
   hand-formatted Python block **will block the deploy**. Always run
   `ruff format --check <file>` after writing docs with code blocks.
   (This already bit the repo once — commit `58346ff`.)
2. **`geap.deploy.env` (planner repo) has no `STAGING_BUCKET`**, but
   `deploy_a2a.py` does `STAGING_BUCKET = os.environ["STAGING_BUCKET"]`. So
   `./deploy.a2a.sh` (the office wrapper) raises `KeyError` as-is. The personal
   script works because `deploy.personal.env` defines it.
3. **Any change to the planner's A2A surface now needs thinking about twice** —
   there are two live A2A deployments of the same agent, with different card
   availability and different deploy mechanics.
4. Shell `;` chaining was mangled when running `ruff` commands via the tool;
   run them as separate invocations.

---

## 8. Suggested starting point for next session

Pick one:

**(a) Verify the recommendation** — the highest-value item. Deploy the planner's
existing Dockerfile to Agent Runtime via `agents-cli` under a *new* engine name
(leave the current one alone), then confirm the public card serves and
`on_message_send` works. That answers Open Question 1 and either unlocks the
migration or kills it.

**(b) Cheap partial win** — bump `google-cloud-aiplatform` past `1.163.0` in the
planner, test `handle_authenticated_agent_card()`, and see whether Approach A's
discovery gap is real or a pin artefact (Open Question 4). Low risk, narrow
scope.

**(c) Documentation hygiene** — apply the corrections in §6, and commit the
three untracked docs.

No work was started on any of these. Nothing is in a half-finished state.
