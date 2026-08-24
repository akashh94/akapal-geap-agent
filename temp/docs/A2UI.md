# A2UI in geap-agent — Backend Implementation

Backend half of GEAP's [A2UI](https://developers.googleblog.com/a2ui-v0-9-generative-ui/)
(Agent-to-UI) implementation. For the full end-to-end picture — the server relay, the
`<a2ui-view>` web component, the shared catalog, and the sequence diagram — see
[`geap-poc/docs/A2UI.md`](https://github.com/../geap-poc/docs/A2UI.md) (sibling repo). This
doc covers only what lives here: how an agent builds, validates, and returns an envelope.

## Why not the reference A2UI SDK's free-text approach

The reference SDKs (`A2uiSchemaManager` + friends) teach a model to hand-author the
envelope JSON in free text and then parse/heal/validate whatever comes back. GEAP agents
never let the model touch the JSON at all: a `FunctionTool` builds it deterministically in
Python and returns it through ADK's normal function-calling path — the same mechanism
`trade_assistant`'s `show_rebalance_widget` already used. The model's only decision is
*whether and when* to call the tool. This trades some of the reference SDK's improvisational
flexibility for envelopes that are always well-formed and catalog-valid — worth it for a
fiduciary-adjacent surface where a malformed UI payload reaching the browser is a worse
failure mode than a slightly less flexible agent.

## Module map

```
app/a2ui/
  catalog.py            CATALOG_ID, CATALOG_VERSION, COMPONENT_TYPES — the component vocabulary
  envelope.py            SurfaceBuilder — deterministic envelope assembly (createSurface / updateComponents / updateDataModel)
  validate.py            validate_envelope() — jsonschema structural pass + semantic checks
  planning_envelope.py   Strict retirement health-check chart contract (build_planning_envelope /
                         default_planning_envelope / validate_planning_envelope)

app/tools/planning/
  intent.py              is_retirement_health_check_intent() — normalized retirement intent matching
  retirement_tools.py    Mock retirement data + render_retirement_dashboard() (builds, validates, returns the envelope)

app/prompts/planning_prompt.py   planning_agent's instruction text
app/agents/planning_agent.py     The LlmAgent: model + tools
app/agents/supervisor.py         Routing entry: "retirement planning ... -> planning_agent"
```

## The strict retirement health-check chart contract

The chat UI mounts A2UI with `<a2ui-view data-root="charts" ...>`, which expects a
smaller, nested-tree envelope shape rather than `SurfaceBuilder`'s flat message list.
`app/a2ui/planning_envelope.py` builds exactly this shape for retirement health-check
responses:

```json
{
  "version": "1.0",
  "root": {
    "type": "surface",
    "props": { "title": "Planning & Retirement" },
    "children": {
      "charts": {
        "type": "chart_tabs",
        "props": { "defaultTab": "glide_path" },
        "children": {
          "glide_path": { "type": "glide_path_chart", "props": { "series": [] } },
          "monte_carlo": {
            "type": "monte_carlo_chart",
            "props": { "series": { "p10": [], "p50": [], "p90": [] }, "target": 0 }
          },
          "allocation": { "type": "allocation_chart", "props": { "segments": [] } }
        }
      }
    }
  },
  "updateDataModel": {
    "planning": {
      "successRate": "",
      "targetAge": 0,
      "currentSavings": "",
      "targetPortfolio": ""
    }
  }
}
```

Rules `render_retirement_dashboard()` follows:

- **Never omit or null `a2ui` for a matched retirement intent.** If composing real
  chart data raises for any reason, it falls back to `default_planning_envelope()` — a
  deep copy of the canonical, always-valid `DEFAULT_PLANNING_A2UI` template above.
- **Charts hold only numeric/structured data** (series/segments/percentiles); narrative
  explanation stays in the agent's prose reply, never inside chart props.
- **No chat-irrelevant full-dashboard sections** (hero cards, tool grids, safeguard
  panels) are included in this envelope — those only ever belonged to a separate,
  standalone dashboard-page use case.
- `validate_planning_envelope()` enforces the shape (version, `root.type`,
  `root.children.charts.type`, the three required chart children, and
  `updateDataModel.planning`'s summary keys) before the tool returns.

Retirement-intent matching (`app/tools/planning/intent.py`) normalizes text (lowercase,
collapse whitespace, trim) before matching phrases like "retirement health check" or
"retirement planning health check diagnostic", so this contract is applied only to
retirement-planning intents and never forced onto unrelated planning questions.

## Writing a new A2UI-emitting tool

Pattern for a new flat, `SurfaceBuilder`-style dashboard-page surface (the retirement
health-check chat charts use the different, stricter `planning_envelope` contract
described above instead — see that section for the pattern to copy for chart-style
chat surfaces):

```python
from app.a2ui.envelope import SurfaceBuilder
from app.a2ui.validate import validate_envelope

def render_my_surface() -> dict:
    """Docstring is the tool description the model sees — explain *when* to call this."""
    data = get_my_underlying_data()  # a separate, plain tool the agent also calls directly

    builder = SurfaceBuilder("my-surface-id", title="My Surface")
    builder.add("tile", "stat_tile", {"label": "...", "value": str(data["x"])})
    builder.set_data(agent="my_agent")

    envelope = builder.build()
    validate_envelope(envelope)  # raises A2uiValidationError -- let it propagate as a tool error
    return {"a2ui": envelope}
```

Two things worth keeping when copying this pattern:

- **Take zero (or minimal) arguments.** Re-derive figures by calling the same tools the
  agent already called for its prose, instead of taking those figures as function
  arguments. That way the model can never make the surface show different numbers than
  its own text does by mistyping an argument — it's not a risk that needs to exist.
- **Always validate before returning.** `validate_envelope()` failing raises `A2uiValidationError`
  (a `ValueError` subclass) inside the tool call — ADK surfaces that as a tool error the
  agent can see and react to, rather than a malformed payload silently reaching the browser.

If the new surface needs a component type the existing set (`surface`, `hero_cta`,
`stat_grid`, `stat_tile`, `tool_grid`, `tool_card`, `safeguard_panel`, `safeguard_row`,
`chart_tabs`, `glide_path_chart`, `monte_carlo_chart`, `allocation_chart`) doesn't cover,
add it to `COMPONENT_TYPES` in `catalog.py` first — `SurfaceBuilder.add()` and
`validate_envelope()` both reject unknown types by construction. Remember the client-side
`RENDERERS` map in `geap-poc/public/js/a2ui/a2ui-view.js` needs the matching case too; the
two catalogs aren't shared by a build step (see Limitations in the sibling doc).

## Model choice for planning_agent

`app/config/models.py::build_model()` resolves a model name with this priority (most
specific wins): the function's own `default_model` argument < the global `AGENT_MODEL` env
var < a per-agent env var passed as `model_env_var`. `planning_agent` calls it as:

```python
build_model(model_env_var="PLANNING_AGENT_MODEL")
```

Like every other GEAP agent, `planning_agent` defaults to the flash-tier `DEFAULT_MODEL`.
Set `PLANNING_AGENT_MODEL` in `.env` (see `.env.example`) to pin it to a different model —
e.g. if the eval harness (`tests/eval/`) shows flash-tier slipping on this agent's longer
tool-call chains (it chains 3-4 tool calls, including the dashboard tool, for a
compliance-flagged "retirement health check").

## Tests

- `tests/unit/test_a2ui.py` — `SurfaceBuilder` and `validate_envelope`, including every
  rejection path (unknown type, duplicate id, dangling child reference, missing root,
  multiple surface ids in one envelope).
- `tests/unit/test_planning_envelope.py` — the strict retirement chart contract:
  `build_planning_envelope`, `default_planning_envelope`, and every
  `validate_planning_envelope` rejection path (wrong version, wrong root/charts type,
  missing chart children, missing `updateDataModel.planning` keys).
- `tests/unit/test_retirement_intent.py` — `normalize_intent_text` and
  `is_retirement_health_check_intent`, including the documented example phrases and
  case/whitespace variants.
- `tests/unit/test_planning_tools.py` — the mock retirement data functions, and that
  `render_retirement_dashboard()`'s figures always match what `get_retirement_summary()`
  independently returns (guards the "never re-type the numbers" property above), plus that
  its `a2ui` payload always satisfies the strict chart contract.
- `tests/unit/test_agent.py` — `planning_agent` is registered on `supervisor.root_agent`,
  has the `render_retirement_dashboard` tool, and resolves to `DEFAULT_MODEL`
  absent env overrides.

Run with `pytest tests/unit` (requires real Application Default Credentials — importing
`app` triggers `app/agent.py`'s `setup_telemetry()`, which calls `google.auth.default()` at
import time).
