"""Provider-free sandbox SDK functions. No external accounts or models."""
from __future__ import annotations
import argparse
import asyncio
import importlib.metadata
import json
import os
import socket

PACKAGES = {
 "openhands": ("openhands-sdk", "SDK_TOOL_DESCRIPTOR_ROUND_TRIP"),
 "mem0": ("mem0ai", "SDK_MEMORY_ITEM_VALIDATION_ROUND_TRIP"),
 "langfuse": ("langfuse", "SDK_DISABLED_LOCAL_SPAN"),
 "agent-framework": ("agent-framework-core", "SDK_TWO_EXECUTOR_WORKFLOW_EXECUTION"),
 "crewai": ("crewai", "SDK_LOCAL_TOOL_EXECUTION")
}

def deny_network(*_args, **_kwargs):
 raise RuntimeError("OFFLINE_GUARD_NETWORK_BLOCKED")

def execute(project: str) -> dict:
 if project not in PACKAGES:
  raise ValueError("Unsupported SDK or EOL target")
 os.environ.update({"LITELLM_LOCAL_MODEL_COST_MAP":"true","LANGCHAIN_TRACING_V2":"false",
  "LANGFUSE_TRACING_ENABLED":"false","OTEL_SDK_DISABLED":"true",
  "CREWAI_TELEMETRY_OPT_OUT":"true","DO_NOT_TRACK":"1"})
 socket.socket.connect=deny_network
 socket.socket.connect_ex=deny_network
 socket.create_connection=deny_network
 if project=="openhands":
  from openhands.sdk import Tool
  a=Tool(name="offline-test-tool")
  b=Tool.model_validate(a.model_dump(mode="json"))
  assert b.name=="offline-test-tool"
 elif project=="mem0":
  from mem0.configs.base import MemoryItem
  a=MemoryItem(id="sandbox-memory",memory="safe reproducible note",metadata={"source":"offline-test"})
  b=MemoryItem.model_validate(a.model_dump(mode="json"))
  assert b.id=="sandbox-memory" and b.memory=="safe reproducible note"
  assert b.metadata=={"source":"offline-test"}
 elif project=="langfuse":
  from langfuse import Langfuse
  client=Langfuse(enabled=False)
  with client.start_as_current_observation(as_type="span",name="local-no-export") as span:
   span.update(output={"verified":True})
  client.flush()
 elif project=="agent-framework":
  from typing import Never
  from agent_framework import Executor,WorkflowBuilder,WorkflowContext,handler
  class Upper(Executor):
   @handler
   async def process(self,value:str,ctx:WorkflowContext[str]):
    await ctx.send_message(value.upper())
  class Reverse(Executor):
   @handler
   async def process(self,value:str,ctx:WorkflowContext[Never,str]):
    await ctx.yield_output(value[::-1])
  upper=Upper(id="upper")
  reverse=Reverse(id="reverse")
  graph=WorkflowBuilder(start_executor=upper).add_edge(upper,reverse).build()
  events=asyncio.run(graph.run("offline"))
  assert events.get_outputs()==["ENILFFO"]
 elif project=="crewai":
  from crewai.tools import tool
  @tool("double_local")
  def double_local(value:int)->int:
   """Compute an integer multiplication without any model or provider."""
   return value*2
  assert double_local.run(value=21)==42
 package,proof=PACKAGES[project]
 return {"project":project,"installed_version":importlib.metadata.version(package),
  "proof":proof,"result":"PASS","vendor_code_executed":True,"provider_calls":0,
  "production_writes":0,"state_persisted":False}
if __name__=="__main__":
 parser=argparse.ArgumentParser()
 parser.add_argument("--project",required=True,choices=sorted(PACKAGES))
 print("SDK_FUNCTIONAL_RESULT="+json.dumps(execute(parser.parse_args().project),sort_keys=True))
