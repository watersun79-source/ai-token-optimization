"""Offline adapter wiring checks only; not an MCP protocol conformance test."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

class DummyFastMCP:
    def __init__(self,name,**kwargs):
        self.name=name
        self.opts=kwargs
        self.calls=[]
    def tool(self):
        def deco(fn):
            self.calls.append(fn)
            return fn
        return deco
    def run(self,**kwargs):
        raise RuntimeError('must not run as part of adapter tests')

class MCPAdapterTests(unittest.TestCase):
    def test_register_and_call_actual_worker(self):
        fake_mcp=types.ModuleType('mcp')
        fake_server=types.ModuleType('mcp.server')
        fake_fast=types.ModuleType('mcp.server.fastmcp')
        fake_fast.FastMCP=DummyFastMCP
        modules={'mcp':fake_mcp,'mcp.server':fake_server,'mcp.server.fastmcp':fake_fast}
        with patch.dict(sys.modules,modules):
            spec=importlib.util.spec_from_file_location('offline_mcp_test',ROOT/'mcp_server.py')
            mod=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self.assertEqual(mod.mcp.name,'AI Real Bot Gateway')
            self.assertEqual(len(mod.mcp.calls),1)
            result=mod.delegate_message('에러 고쳐',python_code='print(')
            self.assertEqual(result['workers'][0]['status'],'DONE')
            self.assertFalse(result['workers'][0]['evidence']['syntax_valid'])
            self.assertFalse(result['chatgpt_composer_hook'])
            self.assertEqual(result['external_llm_calls'],0)

if __name__=='__main__':unittest.main()
