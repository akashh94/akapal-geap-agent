# GEAP E*TRADE POC — Architecture

C4 model, Container level (C4 Level 2). Rendered with [Mermaid](https://mermaid.js.org/)'s
native `C4Container` diagram type, which GitHub renders directly in Markdown — no external
tooling needed to view this file on github.com.

## GEAP Request Flow (simplified)

The primary path through the system, with the OAuth/news integrations and the legacy
Gemini bypass left out so the agent flow itself is easy to follow: **Browser → Cloud Run
query API → Reasoning Engine (Supervisor + specialist sub-agents)**.

```mermaid
C4Container
title GEAP Request Flow — Simplified

Person(user, "Brokerage Customer", "Chats with the AI assistant in the browser")

Container(spa, "Browser SPA", "HTML / JavaScript", "Sends chat queries; renders the streamed reply live")
Container(queryApi, "GEAP Query API", "Node.js, Express — Cloud Run (POST /api/geap/query)", "Relays each query to the Reasoning Engine and streams the reply back to the browser as SSE")

Container_Boundary(reasoningEngine, "Reasoning Engine — Vertex AI Agent Engine") {
  Container(supervisor, "Supervisor", "ADK LlmAgent — orchestrator", "Classifies the request and delegates via transfer_to_agent")
  Container(portfolioAnalyst, "Portfolio Analyst", "ADK LlmAgent", "Holdings, allocation, diversification")
  Container(tradeAssistant, "Trade Assistant", "ADK LlmAgent", "Orders, trade impact, rebalance widget signal")
  Container(marketResearch, "Market Research", "ADK LlmAgent", "Equity / ETF / index research")
  Container(marketResearchSuper, "Market Research Super Agent", "ADK LlmAgent", "Morgan Stanley Research, crypto, commodities")
  Container(customerSupport, "Customer Support", "ADK LlmAgent", "Account / platform / FAQ")
  Container(mortgageAgent, "Mortgage Agent", "ADK LlmAgent", "Mortgage / HELOC education")
  Container(generalAssistant, "General Assistant", "ADK LlmAgent", "Best-effort catch-all")
}

Rel(user, spa, "Uses")
Rel(spa, queryApi, "POST /api/geap/query", "fetch, JSON request / SSE response")
Rel(queryApi, supervisor, "streamQuery", "REST :streamQuery, run_config: streaming_mode=sse")
Rel(supervisor, portfolioAnalyst, "transfer_to_agent")
Rel(supervisor, tradeAssistant, "transfer_to_agent")
Rel(supervisor, marketResearch, "transfer_to_agent")
Rel(supervisor, marketResearchSuper, "transfer_to_agent")
Rel(supervisor, customerSupport, "transfer_to_agent")
Rel(supervisor, mortgageAgent, "transfer_to_agent")
Rel(supervisor, generalAssistant, "transfer_to_agent")
```

## Full Container Diagram (with auxiliary systems)

The complete picture, including the E*TRADE OAuth proxy, the public news search, and the
legacy direct-to-Gemini bypass path alongside the GEAP flow above.

```mermaid
C4Container
title GEAP E*TRADE POC — Container Diagram

Person(user, "Brokerage Customer", "Views accounts and chats with the AI assistant in a browser")

System_Boundary(geap, "GEAP E*TRADE POC") {
  Container(spa, "Browser SPA", "HTML / JavaScript (no framework)", "Renders account views and the chat panel; calls the BFF via fetch and consumes Server-Sent Events for streamed chat replies")
  Container(bff, "UI + BFF", "Node.js, Express — Cloud Run", "Serves the static SPA, proxies E*TRADE OAuth, manages session state, and relays the GEAP agent's reply to the browser as Server-Sent Events")

  Container_Boundary(geapAgent, "GEAP Agent Container — Vertex AI Agent Engine (Google ADK)") {
    Container(supervisor, "Supervisor", "ADK LlmAgent — orchestrator", "Classifies each request and delegates to a specialist via transfer_to_agent; never answers domain questions itself")
    Container(portfolioAnalyst, "Portfolio Analyst", "ADK LlmAgent", "Holdings, allocation, diversification, tax-loss harvesting")
    Container(tradeAssistant, "Trade Assistant", "ADK LlmAgent", "Order types, trade impact, position sizing; signals the rebalance widget")
    Container(marketResearch, "Market Research", "ADK LlmAgent", "Equity / ETF / index research and basic alternative assets")
    Container(marketResearchSuper, "Market Research Super Agent", "ADK LlmAgent", "Morgan Stanley Research, crypto, commodities, private equity")
    Container(customerSupport, "Customer Support", "ADK LlmAgent", "Account, fee, platform, and FAQ questions")
    Container(mortgageAgent, "Mortgage Agent", "ADK LlmAgent", "Mortgage / HELOC education")
    Container(generalAssistant, "General Assistant", "ADK LlmAgent", "Best-effort catch-all for anything outside the other specialists")
  }
}

System_Ext(gemini, "Vertex AI — Gemini 3.5 Flash", "Underlying LLM every agent calls to reason and generate responses")
System_Ext(etrade, "E*TRADE API", "Brokerage OAuth login and account data (sandbox)")
System_Ext(newsRss, "Google News RSS", "Public financial news search")

Rel(user, spa, "Uses", "HTTPS")
Rel(spa, bff, "Sends chat queries and account requests to", "fetch, JSON + SSE over HTTPS")
Rel(bff, supervisor, "Invokes the agent and streams its reply via", "REST :streamQuery / :query, SSE")
Rel(bff, etrade, "OAuth handshake and account data via", "REST, sandbox")
Rel(bff, newsRss, "Public news search via", "HTTPS")

Rel(supervisor, portfolioAnalyst, "Delegates to", "transfer_to_agent")
Rel(supervisor, tradeAssistant, "Delegates to", "transfer_to_agent")
Rel(supervisor, marketResearch, "Delegates to", "transfer_to_agent")
Rel(supervisor, marketResearchSuper, "Delegates to", "transfer_to_agent")
Rel(supervisor, customerSupport, "Delegates to", "transfer_to_agent")
Rel(supervisor, mortgageAgent, "Delegates to", "transfer_to_agent")
Rel(supervisor, generalAssistant, "Delegates to", "transfer_to_agent")

Rel(supervisor, gemini, "Every agent above calls", "Vertex AI API")

Rel(spa, gemini, "Legacy Public Gemini mode only: calls directly with a user-supplied API key, bypassing the BFF entirely", "HTTPS, browser only")
```

## Request Flow (GEAP mode — the default)

1. **Browser SPA** (`geap-poc/public/js/chat.js`) sends the user's message to `POST /api/geap/query` on the **UI + BFF**.
2. The BFF (`geap-poc/server.js`) reuses or creates a Vertex AI Agent Engine session (`getOrCreateGeapSession`, cached in `req.session.geapSessionId` for conversation memory across turns), then calls the Agent Engine's `:streamQuery` REST method with `run_config: { streaming_mode: "sse" }`.
3. The **GEAP Agent Container** — an ADK app deployed to Vertex AI Agent Engine (`geap-agent/app/agent.py` → `app/agents/supervisor.py`) — runs the **Supervisor**, which classifies the request and delegates to exactly one specialist sub-agent via ADK's `transfer_to_agent` mechanism (itself a real model call).
4. The chosen specialist calls its own tools (e.g. `get_portfolio_holdings`, `get_quote`, `preview_order_impact`) against mock brokerage data, then generates the reply. `trade_assistant` may also call `show_rebalance_widget`, a no-op signal tool with no payload of its own — the client already has everything it needs locally to render that widget.
5. Vertex AI streams events back to the BFF as they're generated (`event.partial` chunks). The BFF's incremental parser (`createIncrementalGeapEventParser`) and delta planner (`createStreamDeltaPlanner`) forward each text delta immediately as an SSE frame — not buffered lump-sum -- and append a `[[WIDGET:REBALANCE_FORM]]` sentinel at the end if the widget-signal tool was called.
6. The SPA reads that SSE stream and updates the chat bubble live as text arrives, then renders the matching widget when the sentinel appears.

## Legacy Public Gemini mode

An alternate, non-default mode (`state.aiSettings.assistantMode === 'gemini'`, toggled in AI Settings) makes the **Browser SPA** call the Gemini API directly with a user-supplied API key (`geap-poc/public/js/gemini.js`), bypassing the BFF and the GEAP Agent Container entirely. It exists for testing outside the hosted multi-agent system and is not part of the primary GEAP request flow above.

## Key facts this diagram reflects

- **Container, not microservice, granularity for the agents**: each specialist is a distinct ADK `LlmAgent` (a real model, its own tools, its own instruction), but all of them are deployed together as one Agent Engine resource — hence one `Container_Boundary`, not one box per agent, at the system level.
- **Every agent hop is a real Gemini call**, including the Supervisor's routing decision — there is no "free" classification step.
- **Session continuity** lives in the BFF (`req.session.geapSessionId`), backed by Vertex AI's own managed `VertexAiSessionService` when deployed as an Agent Engine — not an in-memory store, so it's safe under horizontal scaling.
- **Mock data only**: all account/portfolio/quote data comes from `StaticBrokerageService` in `geap-agent`, explicitly documented as a placeholder until a real E*TRADE integration exists.
