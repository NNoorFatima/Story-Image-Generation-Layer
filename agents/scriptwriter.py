"""
agents/scriptwriter.py — Scriptwriter Agent
Reasoning loop: interpret prompt → decompose into scenes → generate dialogue → attach visual cues
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state import WritersRoomState
import tool_registry as mcp


def scriptwriter_node(state: WritersRoomState) -> WritersRoomState:
    print("\n[Scriptwriter Agent] Starting script generation...")

    available_tools = mcp.discover_tools()
    print(f"[Scriptwriter Agent] MCP tools available: {available_tools}")

    if "generate_script_segment" not in available_tools:
        return {**state, "status": "failed", "error": "MCP tool 'generate_script_segment' unavailable"}

    prompt = state["raw_input"]
    num_scenes = 5 if len(prompt.split()) > 30 else 3
    print(f"[Scriptwriter Agent] Generating {num_scenes} scenes...")

    try:
        scene_manifest = mcp.invoke("generate_script_segment", {
            "prompt": prompt,
            "num_scenes": num_scenes,
        })
        print(f"[Scriptwriter Agent] ✓ Generated {len(scene_manifest.get('scenes', []))} scenes.")
    except Exception as e:
        return {**state, "status": "failed", "error": f"Script generation failed: {str(e)}"}

    try:
        mcp.invoke("commit_memory", {
            "collection": "script_history",
            "documents": [str(scene_manifest)],
            "metadatas": [{"prompt": prompt[:100], "num_scenes": num_scenes}],
            "ids": [f"script_{abs(hash(prompt)) % 100000}"],
        })
    except Exception as e:
        print(f"[Scriptwriter Agent] Warning: memory commit failed: {e}")

    return {
        **state,
        "scene_manifest": scene_manifest,
        "script_valid": True,
        "status": "awaiting_hitl",
    }