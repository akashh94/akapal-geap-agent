# Troubleshooting: Tool 'transfer_to_supervisor' not found

## Symptom

On the office supervisor (ReasoningEngine), agent execution fails with:

```
ValueError: Tool 'transfer_to_supervisor' not found.
```

Traceback: `llm_agent.run_impl` → `functions._execute_single_function_call_async`
→ `functions._get_tool`. The model followed the sub-agent prompt and tried to
call `transfer_to_supervisor`, but no such tool was registered.

## Root cause

The sub-agent prompts (trade, market research, portfolio, support, mortgage)
told the model to call `transfer_to_supervisor` when out of scope. But ADK
2.6.2 does **not** auto-generate a `transfer_to_<parent>` tool for chat-mode
sub-agents:

- `LlmAgent._resolve_sub_agents` (in `model_post_init`) adds an agent tool to
  the **parent** (supervisor) for `single_turn`/`task` sub-agents only.
- Chat-mode sub-agents get **no** transfer tool injected.
- The only transfer mechanism ADK provides is the generic
  `transfer_to_agent(agent_name=...)` tool (`TransferToAgentTool`).

So the model was instructed to call a tool that did not exist, and the runner
raised `Tool not found` when it tried to execute the call.

This is latent in the personal environment too (the retirement path
supervisor→planner never needed a sub-agent→supervisor transfer), which is
why it only surfaced on the office deployment.

## Fix

1. **Do NOT add `TransferToAgentTool` explicitly to sub-agents.** ADK 2.6.2's
   default `AutoFlow` already injects the generic `transfer_to_agent` tool at
   LLM request time for chat-mode agents. Adding it explicitly as well causes
   a duplicate declaration, which Gemini rejects with:

   ```
   WARNING:root:Duplicate tool name 'transfer_to_agent': the previously
     registered tool is shadowed and can no longer be called
   400 INVALID_ARGUMENT: Duplicate function declaration found: transfer_to_agent
   ```

   The tool appears once, automatically, with the correct `agent_name` enum
   (parent + peers of the agent).

2. **Reference the real tool in the prompts**:

   ```
   - If the user's question is outside your expertise, call transfer_to_agent
     with agent_name="supervisor".
   ```

   (replacing `call transfer_to_supervisor`).

## Verification

The explicit sub-agent tool lists contain **no** `transfer_to_agent` — ADK's
AutoFlow injects it once per agent at LLM request time:

```
trade_assistant    ['ResilientMcpToolset', 'google_search_agent', 'load_web_page']
portfolio_analyst  ['ResilientMcpToolset']
market_research    ['ResilientMcpToolset', 'google_search_agent', 'load_web_page']
customer_support   ['ResilientMcpToolset', 'google_search_agent']
mortgage_agent     ['ResilientMcpToolset', 'google_search_agent']
```

## Key takeaway

Never add `TransferToAgentTool` to a chat-mode agent's `tools` list. ADK 2.6.2
exposes exactly one `transfer_to_agent(agent_name=...)` declaration, injected
automatically by AutoFlow; a second one is a duplicate declaration that Gemini
rejects.
