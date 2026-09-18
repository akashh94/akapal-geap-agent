# Two Ways to Put an A2A Agent on Agent Runtime

A first-principles comparison of the two ways we have deployed A2A agents to
Agent Runtime, why they behave so differently, and how to choose between them.

> **Status (2026-09-18).** Two things changed since this was written:
>
> 1. **The supervisor is no longer app-served at all.** `app/app_utils/a2a.py`,
>    `app/fast_api_app.py` and the `Dockerfile` were removed; it is now deployed
>    as a `vertexai.agent_engines.AdkApp` object and the platform serves its
>    operations (`:query` / `:streamQuery`). That is a *third* shape — neither A
>    (platform-native `A2aAgent`) nor B (we own the container) — so read both
>    columns below as techniques rather than as the current supervisor design.
> 2. **§7.3's first bullet was wrong.** Live Agent Registry evidence shows the
>    pendulum swings the other way: the platform-native planner is registered as
>    `Framework: a2a` / `A2A_AGENT` with an indexed card and 3 skills, while the
>    app-served supervisor was registered as `Framework: google-adk` / `CUSTOM`
>    with **no card and no skills**. Unifying on B would *lose* registry A2A
>    discovery unless a manual registration step is added — see §10.
>
> The first-principles analysis below (the design fork, why the shapes differ)
> still holds. The *recommendation* in §7 does not.

Companion docs:

- [`AGENT_RUNTIME_A2A.md`](./AGENT_RUNTIME_A2A.md) — how the supervisor currently
  reaches the planner, end to end
- [`MEMORY_BANK.md`](./MEMORY_BANK.md) / [`LEARNING_MEMORY_BANK.md`](./LEARNING_MEMORY_BANK.md)
- [`TRANSFER_TOOL_NOT_FOUND.md`](./TRANSFER_TOOL_NOT_FOUND.md)

---

## 0. What this document is for

We have two agents and, confusingly, two totally different deployment shapes:

| Repo | Shape | Deployed by |
|---|---|---|
| `akapal-geap-agent` (supervisor) | SDK object deploy, no server | `deploy_adk.py` |
| `akapal-geap-financial-planner` | platform-native object | `deploy_a2a.py` (SDK) |

Both are on Agent Runtime and both are now deployed the same way — an SDK object
deploy with no server of our own. Historically both spoke A2A; as of 2026-09-18
only the planner does. The two *techniques* below still differ in the ways that
matter: in B you own the HTTP surface, get a public card, and ship files; in A the
platform owns the surface, your card is not public, and you ship a pickled Python
object with serialization constraints attached.

That gap is not accidental, and it is not because "the platform works this way."
It falls out of **one design decision** — who owns the HTTP surface — and
everything else is downstream of it.

This document derives both shapes from first principles so the trade-offs are
visible instead of memorised.

---

## 1. First principles: what must be true for one agent to call another?

Strip away all product names. Two agents on two machines want to have a
conversation. What is *necessarily* true?

**P1 — Reachability.** Some process must accept an HTTP request. An agent is a
program; to be called over a network it must be listening on a socket.

**P2 — Hosting.** Something must run that process, restart it, scale it, and
keep it alive. We are choosing *not* to do that ourselves, so a platform does
it. To run our code the platform needs a **contract**: what we hand it, and
what it expects back.

**P3 — Addressing.** The caller must be able to name the callee. Either the
caller is *told* the address, or it can *look it up*. There is no third option.

**P4 — Protocol.** Both sides must agree on the shape of the bytes: what a
"message" is, what a "task" is, how a reply is framed. This is what A2A
standardises.

**P5 — Description.** A caller that has only an address knows *where* to knock
but not *what to ask*. Something must describe the callee's capabilities. In A2A
that artefact is the **agent card**.

**P6 — Registration.** If the platform is routing traffic to us, the platform
must know which surface to expose and how to map it onto its own API.

Now: notice that **P1 and P3–P5 are genuinely fixed**. Reachability is physics
of networking; protocol and card are A2A's job; description is required for
useful calling. There is very little design freedom there.

The freedom is concentrated in **P2 and P6** — the hosting contract. And within
that, exactly one question has leverage:

> **Who writes the HTTP server — us, or the platform?**

Answer "the platform" and you get Approach A. Answer "us" and you get
Approach B. Every observable difference between our two repos follows from that
single answer.

---

## 2. The fork, stated once

```
                    Who owns the HTTP surface?
                              │
            ┌─────────────────┴─────────────────┐
            │                                   │
    A: the platform                       B: us
    ─────────────────                     ────────────────
    We supply a card + an executor.       We supply a container
    The platform generates the server.    that already serves HTTP.
                                          The platform just runs it.
            │                                   │
            ▼                                   ▼
    A2aAgent (object deploy)              Dockerfile / image
    / container (object deploy)           (agents-cli or SDK)
```

Approach A is "**fill in a template**". Approach B is "**bring your own
server**".

Neither is wrong. They are answers to different constraints. The rest of this
document works out what each answer forces.

---

## 3. Approach A — platform-native (`A2aAgent`)

### 3.1 What we write

We provide exactly two things, and nothing that looks like a web server:

1. An **`AgentCard`** — the A2A business card (name, description, skills).
2. An **`AgentExecutor`** — the adapter that translates A2A's task/message world
   into ADK's runner/event world.

```python
# akapal-geap-financial-planner/app/a2a_app.py
a2a_agent = A2aAgent(
    agent_card=create_agent_card(
        agent_name="financial_planner",
        description="Goals-based financial planning: ...",
        skills=_SKILLS,  # hand-written, on purpose
    ),
    agent_executor_builder=build_agent_executor,
)
a2a_agent.set_up()
```

We never write a route, never call `uvicorn`, never mount anything.

### 3.2 What the platform does

Per the platform's own documentation, the `A2aAgent` template *"acts as a
wrapper, abstracting away the converting layer from you."* Concretely, the
platform:

- **Generates the HTTP server** (P1).
- **Injects the executor** as the place where requests land.
- **Exposes a fixed operation set** (P6) — `on_message_send`,
  `on_get_task`, `on_cancel_task`, `handle_authenticated_agent_card` — under
  `{engine}/a2a/v1/...`.
- **Serves no public agent card.** This is explicit in the docs: *"Agent Runtime
  does not serve the public agent card."* The card exists, but only behind the
  authenticated `{engine}/a2a/v1/card` route.

### 3.3 How it is deployed

This is the part that surprises people: **the deploy is an object deploy.**

```python
# akapal-geap-financial-planner/deploy_a2a.py
remote = client.agent_engines.create(
    agent=a2a_agent,                        # a live Python object
    config={
        "requirements": REQUIREMENTS,
        "extra_packages": ["app"],
        "staging_bucket": STAGING_BUCKET,
        ...
    },
)
```

The SDK serialises the in-memory `a2a_agent` to a `.pkl`, writes a
`requirements.txt`, tars up `extra_packages`, uploads the bundle to a GCS
staging bucket, and the service builds and starts a container from it.

**Why a Python script instead of a CLI?** Because the artefact is a live Python
object. Nothing else can produce it.

**Is object deploy the only method for a platform-native agent?** Yes, in
practice. `agent_framework` is auto-detected — and auto-detected *as `a2a`* —
only *"if you are deploying from an agent object."* From source files it
*"defaults to `custom`."* And the documented set of supported `agent_framework`
values is `google-adk`, `langchain`, `langgraph`, `ag2`, `llama-index`,
`custom` — **`a2a` is not among them.** So auto-detection is the only mechanism
that yields an A2A surface. Given the `A2aAgent` template, the object deploy is
forced.

### 3.4 Consequences, derived

Each of these follows *necessarily* from "the platform owns the surface":

- **No public card → no discovery.** The card is the only description
  mechanism A2A has (P5), and the platform will not serve it publicly. So a
  caller cannot look the agent up (P3). It must be **told** the address.
  In our case: `FINANCIAL_PLANNER_ENGINE`, a hardcoded `ReasoningEngine`
  resource name copied by hand from deploy output into an env file.
- **Fixed operation set.** We cannot add our own routes. If we needed a health
  endpoint, a debug route, or an extra protocol, there is nowhere to put it.
- **Serialization constraints leak into our code.** The object is pickled, so
  every callable it references must be picklable *by reference*. This is why
  `build_runner` and `build_agent_executor` are deliberately **module-level**
  (a lambda would be serialised by value, which is fragile) and why
  `build_runner` is **async** (the MCP toolset's `get_tools()` cannot be
  awaited at import time, and the executor awaits it on first use). These are
  not style preferences. They are pickle-shaped constraints.
- **Staging bucket required.** There is nowhere else to put the bundle.
- **`extra_packages` required.** Only the pickle and requirements ship by
  default, so our source must be named explicitly.
- **Preview status.** Both A2A doc pages currently carry the Pre-GA banner:
  *"available 'as is' and might have limited support."*

### 3.5 Failure modes we actually hit

These are all *consequences of §3.3*, not unrelated bugs:

| Symptom | Root cause |
|---|---|
| `No module named 'app.a2a_app'` — container dies | Only the pickle shipped; source not bundled. Fix: `extra_packages: ["app"]`. |
| `Please provide a staging_bucket` | Mandatory parameter, no default. |
| Card advertises `.../reasoningEngines/test-agent-engine/a2a` | `set_up()` rewrites the card URL from `GOOGLE_CLOUD_AGENT_ENGINE_ID`, absent at build time. |
| `Permission 'aiplatform.reasoningEngines.get' denied` | Caller's SA cannot see the engine. |

Note the theme: **every one of these is an artefact of shipping a serialised
Python object**, and none of them would exist if we shipped a container.

---

## 4. Approach B — app-served container

### 4.1 What we write

We write the server. In both of our repos that used to be a FastAPI app with A2A
routes mounted onto it — removed on 2026-09-18:

```python
# akapal-geap-agent/app/app_utils/a2a.py  (and the planner's twin) — both removed
agent_card = await AgentCardBuilder(
    agent=agent,
    capabilities=...,
    rpc_url=f"{resolved_app_url}{rpc_path}",
).build()

request_handler = DefaultRequestHandler(
    agent_executor=A2aAgentExecutor(runner=runner),
    task_store=task_store,
    agent_card=agent_card,
)

add_a2a_routes_to_fastapi(
    app,
    agent_card_routes=create_agent_card_routes(
        agent_card, card_url=f"{rpc_path}{AGENT_CARD_WELL_KNOWN_PATH}"
    ),
    jsonrpc_routes=create_jsonrpc_routes(request_handler, rpc_url=rpc_path),
)
```

Note what happened here: **we still use `A2aAgentExecutor`.** The executor is
the same in both approaches — it is the A2A↔ADK adapter. What changed is *who
wires it into an HTTP server*. In Approach A the platform does; here we do, with
`attach_a2a_routes()`.

### 4.2 What the platform does

The platform runs our container and enforces a **runtime contract**, which is
short and mechanical:

- The container **must listen on `0.0.0.0`, port `8080`**.
- Custom endpoints are explicitly allowed: *"Your container can expose any
  custom HTTP endpoints."*
- Optionally implement `/api/reasoning_engine` and
  `/api/stream_reasoning_engine` to get Python SDK and Console-playground
  support.
- For custom containers, declare supported methods in `classMethods`.

That third bullet is the important one. Because custom endpoints are permitted,
mounting `/a2a/<agent_name>/.well-known/agent-card.json` and a JSON-RPC surface
is **documented-legal**, not a workaround.

The platform also serves the engine's own A2A surface and an authenticated card,
but it does not need to: we have our own.

### 4.3 How it is deployed

Two options, both common-tooling:

```bash
# Container image, built by us and pushed to Artifact Registry
client.agent_engines.create(config={"container_spec": {"image_uri": ...}})

# Or Dockerfile, built by the platform from our source
client.agent_engines.create(config={"source_packages": [...], "image_spec": {}})
```

Or, wrapping both, the CLI path our supervisor uses:

```bash
# akapal-geap-agent/deploy.personal.sh
agents-cli deploy \
  --deployment-target agent_runtime \
  --project "$PROJECT_ID" --region "$REGION" \
  --update-env-vars "..." \
  --min-instances 1 --max-instances 1
```

with the manifest declaring `deployment_target: agent_runtime` and
`is_a2a: true`.

**The artefact is files, not objects.** There is nothing to pickle, so no
serialization constraints reach into our code.

Note: `agents-cli`'s Agent Runtime target always builds from the Dockerfile —
a prebuilt `--image` is not supported on that path.

### 4.4 Consequences, derived

- **Public card → discovery is possible.** We serve the card ourselves at a
  known public path. A caller can fetch it and learn both the address and the
  capabilities (P3 + P5 satisfied from one artefact).
- **We own the routes.** Extra endpoints are free.
- **No serialization constraints.** Module-level functions, lambdas, closures,
  import-time work — all fine. The async-MCP problem still exists as a *runtime
  ordering* problem, but it is solved in a lifespan hook rather than dictated by
  a pickler.
- **No staging bucket, no `extra_packages`.** Our source is the source.
- **Non-Python is possible.** The runtime contract is language-agnostic.
- **One toolchain.** `agents-cli` handles infra, deploy, and CI/CD; we do not
  maintain a bespoke deploy script per agent.
- **Trade-off: we own the server.** We are responsible for binding
  `0.0.0.0:8080`, for keeping the card accurate, and for any protocol
  maintenance that the platform would otherwise absorb. The docs say so
  directly: if you want Google to *"automatically handle updates when you update
  your version of ADK, you should use the tooling provided by ADK for deploying
  agents instead of writing your own API server."*

---

## 5. Consequence table

For each first-principle invariant, what each approach actually gives:

| Invariant | A — platform-native | B — app-served container |
|---|---|---|
| **P1** Reachability | Platform generates the server | We write the server |
| **P2** Hosting contract | Pickled object + requirements + extra_packages + GCS staging | Dockerfile or container image |
| **P3** Addressing | Must be **told**: hardcoded `FINANCIAL_PLANNER_ENGINE` | **Discoverable**: public card names the URL |
| **P4** Protocol | A2A over HTTP+JSON (REST) | A2A over JSON-RPC (as we mount it) |
| **P5** Description | Card exists but is **not publicly served** | Card served at `.well-known/agent-card.json` |
| **P6** Registration | Platform-owned, auto-detected via `agent_framework="a2a"` | Ours: we declare methods and mount routes |
| Extensible routes | No | Yes |
| Serialization constraints | Yes (module-level, no lambdas, async builders) | No |
| Discovery possible | No | Yes |
| Deploy tooling | Bespoke Python script | `agents-cli`, any CLI, Terraform, CI/CD |
| Language freedom | Python | Any |
| Release status | Preview | Depends on components used |
| Who maintains the protocol glue | Platform | Us |

---

## 6. How to choose

The decision rule, stated as a rule rather than a vibe:

**Choose B when** the agent needs to be *discoverable*, needs routes beyond the
fixed set, is written in a language other than Python, or when you want one
deployment toolchain across agents. This is the common case, and it is the
documented "control over the API server" path.

**Choose A when** you are prototyping interactively (the docs present the SDK
object deploy as *"ideal for interactive development in environments like
Colab"*), your agent's structure is genuinely serialisable, and you actively
want the platform to own the A2A surface.

The asymmetry that matters most in this codebase: **B can always express what A
can** — you can mount `A2aAgentExecutor` yourself, as we do — but A cannot
express what B can, because A's operation set is closed and its card is not
public.

---

## 7. This system, specifically

### 7.1 Current state

We are running exactly one deployment of each agent, and both are Approach A:

| Deployment | Approach | Repo | Card | Used by |
|---|---|---|---|---|
| Supervisor on Agent Runtime | **A** (`AdkApp`, no server) | `akapal-geap-agent` | Not public | Inbound REST clients (`:query` / `:streamQuery`) |
| Planner on Agent Runtime | **A** (`A2aAgent`) | `akapal-geap-financial-planner` | Not public | Supervisor |

No Approach B deployment remains: the planner's Cloud Run twin was removed on
2026-09-18, the same day the supervisor's app-served surface went.

### 7.2 The observation that follows

*(Historical — the artefacts described here were removed on 2026-09-18. Kept
because this is the reasoning that led to unifying on A.)*

The planner repo used to carry an Approach B deployment whose container was
built to run on Agent Runtime. Its Dockerfile satisfied the runtime contract
(`EXPOSE 8080`, binds via `--port "${PORT:-8080}"`), and its
`attach_a2a_routes(rpc_path=f"/a2a/{agent.name}")` produced a public card at:

```
/a2a/financial_planner/.well-known/agent-card.json
```

That was the same pattern as the supervisor's. Nothing about "both agents on
GEAP" prevented deploying *that* to Agent Runtime instead of object-deploying
the `A2aAgent` — but the opposite was chosen: both B paths were deleted.

### 7.3 What unification on B would remove

- The hardcoded `FINANCIAL_PLANNER_ENGINE` — replaced by card discovery
  *(caveat: wrong as written. The planner is already discoverable in Agent
  Registry today; what is hardcoded is our client, not the capability. And
  unifying on B would drop the planner's existing `A2A_AGENT` registry entry with
  its indexed skills, because the registry classifies by `agent_framework` and
  app-served deploys come through as `google-adk`. Net effect: you would trade a
  public card for an A2A registry entry — see §10.)*
- `deploy_a2a.py` and the object-deploy machinery
- The GCS staging bucket
- `extra_packages` and the `No module named 'app.a2a_app'` failure class
- The pickling constraints on `build_runner` / `build_agent_executor`
- The `test-agent-engine` placeholder card URL from `set_up()`
- The second, bespoke deploy toolchain

It would also make `call_financial_planner` simpler: with a public card,
`RemoteA2aAgent` becomes available again, instead of the manual
`agent_engines.get()` + `on_message_send()` call.

### 7.4 What it costs

- **We own the server.** Correctness of the card, the bind, and the routes is
  ours.
- **We stop getting automatic adaptation** when ADK changes its A2A internals.
  The docs warn about exactly this.
- **A2A itself is Preview on this platform**, so neither approach is on
  GA ground.

### 7.5 Open questions worth verifying before acting

These are genuinely unresolved and should be tested, not assumed:

1. Does `agents-cli deploy --deployment-target agent_runtime` preserve a custom
   `lifespan` and custom route mounts? *Answered yes* — the supervisor was
   deployed this way and served `attach_a2a_routes()`. (That surface was later
   removed deliberately, not because it failed.)
2. What does `is_a2a: true` in `agents-cli-manifest.yaml` actually generate?
   *Partially answered (2026-09-18):* in Agent Registry it produced **nothing
   A2A** — the supervisor came through as `Framework: google-adk` / `CUSTOM`
   with no card and no skills, and the engine's `spec.agentFramework` was
   `google-adk`, not `a2a`. Whether agents-cli does anything else with the flag
   remains unverified.
3. Are the *app-served* A2A routes GA, or Preview? Only the `A2aAgent`
   template's Pre-GA status is explicitly documented. Unknown for the
   `attach_a2a_routes` path.
4. Is `handle_authenticated_agent_card()` available in our pinned
   `google-cloud-aiplatform==1.163.0`? The current docs list it as a supported
   operation, which contradicts §9 of `AGENT_RUNTIME_A2A.md` ("does not exist").
   If it works, Approach A's discovery gap narrows to "authenticated only"
   rather than "impossible".

---

## 8. Corrections to `AGENT_RUNTIME_A2A.md`

The earlier document is accurate on mechanics but wrong or stale in places.
Specifically:

| Claim in that doc | Status |
|---|---|
| "there are two kinds of A2A" | True, but framed as a forced dichotomy. It is one design fork, and B expresses A. |
| "The card is the *only* discovery mechanism" | True as a statement about A2A; misleading as a description of this system, where neither side reads the other's card. |
| §9: "`handle_authenticated_agent_card` does not exist" | Resolved: the card **is** retrievable via Agent Registry (`card.content`), not via `{base}/v1/card`. The method's absence in our pin is still real. |
| §9: "the planner's card is not retrievable by any route we found" | Now resolved: the card **is** retrievable — stored inline in the Agent Registry `Agent` resource as `card.content` (`A2A_AGENT_CARD`), with 3 skills indexed. It is simply not served at a public `.well-known` path. |
| "the supervisor never imports planner code" | Correct and important. |
| §3 / §7.2: the supervisor as a live Approach B example | Superseded — its A2A surface was removed on 2026-09-18, and the planner's B code path (`app/fast_api_app.py` + `Dockerfile`) was removed the same day. No Approach B deployment remains. |

Read that document for *what happens on the wire*; read this one for *why the
shapes differ*.

---

## 9. Verification notes

Everything above was checked against the live documentation on 2026-09-17, plus
the code in both repos and the `agents-cli` manifest.

- [Deploy an agent](https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/runtime/deploy-an-agent) — the five deploy methods, `extra_packages` and `gcs_dir_name` scoped to object deploy, `agent_framework` auto-detection
- [Create an A2A agent](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/runtime/create-an-a2a-agent) — `AgentCard` + `AgentExecutor` + `LlmAgent`, `A2aAgent`, Preview banner
- [Use an A2A agent](https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/runtime/use-an-a2a-agent) — operation set, `handle_authenticated_agent_card`, "does not serve the public agent card"
- [Agent Platform runtime contract](https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/runtime/runtime-contract) — `0.0.0.0:8080`, custom endpoints permitted, `classMethods`, the "use ADK tooling instead of writing your own server" warning
- [Agents CLI deployment](https://google.github.io/agents-cli/guide/deployment/) — `deployment_target` values, Agent Runtime always builds from Dockerfile
- [Agent Runtime overview](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/runtime) — ADK full-integration tier, Agents CLI

Not verified: whether the planner's `A2aAgentExecutor` + custom-routes
combination behaves identically when containerised rather than object-deployed.

---

## 10. Registering a non-A2A agent in Agent Registry (future work)

Not done yet. Recorded so the next attempt starts from the docs rather than from
guesswork.

**The supervisor is already registered — just not as an A2A agent.** Verified live
in `adk-tut-508714/us-central1`: it appears as an `Agent` resource with
`Framework: google-adk`, protocol type `CUSTOM`, interfaces `:query` and
`:streamQuery`, and **no card and no skills**. Automatic ingestion covers Agent
Runtime resources; the SDK is not required.

**Automatic registration could not enrich it.** Per the docs, auto-registration
indexes A2A skills by querying the card at `/.well-known/agent-card.json`. The
supervisor never served a card there — its old card lived at
`/api/a2a/supervisor/.well-known/agent-card.json` and has since been removed — so
there was nothing to index.

**The documented path for a REST-only agent is `no-spec`:**

```
gcloud agent-registry services create AGENT_NAME \
  --project=PROJECT_ID --location=REGION \
  --display-name="DISPLAY_NAME" \
  --agent-spec-type=no-spec \
  --interfaces=url=ENDPOINT_URL,protocolBinding=http-json
```

**`--agent-spec-type=a2a-agent-card` is only correct if the agent actually serves
A2A.** Registering a card while serving no A2A endpoint would advertise a surface
that does not exist. That option reopens only if the supervisor regains an A2A
surface — e.g. by moving to the platform-native `A2aAgent` template.

Other constraints worth knowing:

- Requires `roles/agentregistry.editor` on the project.
- The `us` and `eu` multi-region locations are **not supported**; use a region or
  `global`. Our entries live in `us-central1`.
- Manual entries are **not** automatically updated or deleted when the underlying
  resource changes — lifecycle is ours to manage.
- Registering a `Service` for an engine the platform has already auto-registered
  may produce a second, parallel entry. Test on a throwaway agent first.

Sources: [Register agents](https://docs.cloud.google.com/agent-registry/register-agents) ·
[Use manual registration](https://docs.cloud.google.com/agent-registry/manual-registration)
That is the one experiment standing between §7.3 and action.
