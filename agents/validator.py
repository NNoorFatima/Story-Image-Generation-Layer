"""
agents/validator.py — Script Validator Agent
Checks: scene headings, dialogue labels, action descriptions.
Rejects malformed scripts and suggests corrections.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state import WritersRoomState
import tool_registry as mcp

def validator_node(state: WritersRoomState) -> WritersRoomState:
    """
    LangGraph node: Script Validator Agent.
    Triggered when input_mode == 'manual'.
    Validates raw script text and converts it to standardized JSON.
    """
    print("\n[Validator Agent] Validating manually provided script...")

    # ── Step 1: Discover tools ────────────────────────────────────────────────
    available_tools = mcp.discover_tools()
    if "validate_script" not in available_tools:
        return {**state, "status": "failed", "error": "MCP tool 'validate_script' unavailable"}

    # ── Step 2: Run validation via MCP ────────────────────────────────────────
    try:
        result = mcp.invoke("validate_script", {
            "script_text": state["raw_input"]
        })
    except Exception as e:
        return {**state, "status": "failed", "error": f"Validation tool error: {str(e)}"}

    valid = result.get("valid", False)
    errors = result.get("errors", [])
    parsed = result.get("parsed")

    if not valid:
        print(f"[Validator Agent] Script REJECTED. Issues found: {errors}")
        return {
            **state,
            "script_valid": False,
            "validation_errors": errors,
            "status": "failed",
            "error": f"Script validation failed: {'; '.join(errors)}",
        }

    print(f"[Validator Agent] Script PASSED validation. Parsed {len(parsed.get('scenes', []))} scenes.")

    # ── Step 3: Commit validated script to memory ─────────────────────────────
    try:
        mcp.invoke("commit_memory", {
            "collection": "script_history",
            "documents": [str(parsed)],
            "metadatas": [{"mode": "manual", "source": "user_upload"}],
            "ids": [f"manual_script_{hash(state['raw_input']) % 100000}"],
        })
    except Exception as e:
        print(f"[Validator Agent] Warning: memory commit failed: {e}")

    return {
        **state,
        "scene_manifest": parsed,
        "script_valid": True,
        "validation_errors": [],
        "status": "awaiting_hitl",
    }