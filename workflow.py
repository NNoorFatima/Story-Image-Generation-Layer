"""
workflow.py — LangGraph StateGraph (The Writer's Room)
Nodes: mode_selector → validator|scriptwriter → hitl → character → image → memory_commit
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from langgraph.graph import StateGraph, END

from state import WritersRoomState
from agents import (
    scriptwriter_node,
    validator_node,
    hitl_node,
    character_designer_node,
    image_synthesizer_node,
    memory_commit_node,
)


# ── Mode Selector Node ────────────────────────────────────────────────────────

def mode_selector_node(state: WritersRoomState) -> WritersRoomState:
    mode = state.get("input_mode", "auto")
    print(f"\n[Mode Selector] Input mode: '{mode}'")
    return {**state, "status": "processing"}


# ── Conditional routing functions ─────────────────────────────────────────────

def route_after_mode_selector(state: WritersRoomState) -> str:
    return "validator_node" if state["input_mode"] == "manual" else "scriptwriter_node"


def route_after_script_stage(state: WritersRoomState) -> str:
    return END if state.get("status") == "failed" else "hitl_node"


def route_after_hitl(state: WritersRoomState) -> str:
    return END if not state.get("hitl_approved") else "character_node"


def route_after_character(state: WritersRoomState) -> str:
    return END if state.get("status") == "failed" else "image_node"


def route_after_image(state: WritersRoomState) -> str:
    return END if state.get("status") == "failed" else "memory_commit_node"


# ── Build the graph ───────────────────────────────────────────────────────────

def build_workflow():
    graph = StateGraph(WritersRoomState)

    graph.add_node("mode_selector_node",  mode_selector_node)
    graph.add_node("validator_node",      validator_node)
    graph.add_node("scriptwriter_node",   scriptwriter_node)
    graph.add_node("hitl_node",           hitl_node)
    graph.add_node("character_node",      character_designer_node)
    graph.add_node("image_node",          image_synthesizer_node)
    graph.add_node("memory_commit_node",  memory_commit_node)

    graph.set_entry_point("mode_selector_node")

    graph.add_conditional_edges(
        "mode_selector_node", route_after_mode_selector,
        {"validator_node": "validator_node", "scriptwriter_node": "scriptwriter_node"}
    )
    graph.add_conditional_edges(
        "validator_node", route_after_script_stage,
        {"hitl_node": "hitl_node", END: END}
    )
    graph.add_conditional_edges(
        "scriptwriter_node", route_after_script_stage,
        {"hitl_node": "hitl_node", END: END}
    )
    graph.add_conditional_edges(
        "hitl_node", route_after_hitl,
        {"character_node": "character_node", END: END}
    )
    graph.add_conditional_edges(
        "character_node", route_after_character,
        {"image_node": "image_node", END: END}
    )
    graph.add_conditional_edges(
        "image_node", route_after_image,
        {"memory_commit_node": "memory_commit_node", END: END}
    )
    graph.add_edge("memory_commit_node", END)

    return graph.compile()


def run_pipeline(input_mode: str, raw_input: str) -> WritersRoomState:
    app = build_workflow()
    initial_state: WritersRoomState = {
        "input_mode":        input_mode,
        "raw_input":         raw_input,
        "scene_manifest":    None,
        "script_valid":      None,
        "validation_errors": None,
        "hitl_approved":     None,
        "hitl_feedback":     None,
        "character_db":      None,
        "image_paths":       None,
        "memory_committed":  None,
        "status":            "processing",
        "error":             None,
    }
    return app.invoke(initial_state)