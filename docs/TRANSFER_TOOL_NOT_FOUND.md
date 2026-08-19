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

1. **Add the transfer tool to every sub-agent** so the model can hand back to
   the supervisor:

   ```python
   from google.adk.tools.transfer_to_agent_tool import TransferToAgentTool

   LlmAgent(
       ...,
       tools=[
           ...,
           TransferToAgentTool(agent_names=["supervisor"]),
       ],
   )
   ```

   `agent_names` enum-constrains the `agent_name` parameter so the model
   cannot hallucinate a target.

2. **Update the prompts** to reference the real tool:

   ```
   - If the user's question is outside your expertise, call transfer_to_agent
     with agent_name="supervisor".
   ```

   (replacing `call transfer_to_supervisor`).

## Verification

Each sub-agent's tool list now includes `transfer_to_agent`:

```
trade_assistant    ['ResilientMcpToolset', 'google_search_agent', 'load_web_page', 'transfer_to_agent']
portfolio_analyst  ['ResilientMcpToolset', 'transfer_to_agent']
market_research    ['ResilientMcpToolset', 'google_search_agent', 'load_web_page', 'transfer_to_agent']
customer_support   ['ResilientMcpToolset', 'google_search_agent', 'transfer_to_agent']
mortgage_agent     ['ResilientMcpToolset', 'google_search_agent', 'transfer_to_agent']
```

## Key takeaway

Never reference a transfer tool name in a prompt that ADK does not generate.
ADK 2.6.2 exposes only `transfer_to_agent(agent_name=...)`; anything else must
be added explicitly with `TransferToAgentTool`.
