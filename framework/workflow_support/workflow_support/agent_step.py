"""Agent-as-step adapter — wrap agents as workflow steps."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from workflow_support.step import Step, StepContext


def agent_as_step(
    agent: Any,
    input_schema: type[BaseModel],
    output_schema: type[BaseModel],
    name: str | None = None,
) -> Step:
    """Wrap an agent as a workflow Step.

    Supports two agent protocols:
    1. AgentRunner protocol: agent.run(definition, input, tools, context) -> AgentRunResult
       Pass definition/tools/context via ctx.state keys.
    2. Simple protocol: agent.run(input_data) -> output
    """
    step_name = name or getattr(agent, "name", "agent-step")

    async def _run_agent(ctx: StepContext) -> BaseModel:
        # If state contains agent_definition, use AgentRunner protocol
        if ctx.state.get("agent_definition") is not None:
            definition = ctx.state["agent_definition"]
            tools = ctx.state.get("agent_tools", [])
            agent_ctx = ctx.state.get("agent_context", {})
            input_str = (
                ctx.input_data.model_dump_json()
                if isinstance(ctx.input_data, BaseModel)
                else str(ctx.input_data)
            )
            result = await agent.run(definition, input_str, tools, agent_ctx)
            if hasattr(result, "output"):
                return output_schema.model_validate({"response": result.output})
            return result
        else:
            # Simple protocol: run(input_data) -> output
            return await agent.run(ctx.input_data)

    return Step(
        fn=_run_agent,
        name=step_name,
        input_schema=input_schema,
        output_schema=output_schema,
    )
