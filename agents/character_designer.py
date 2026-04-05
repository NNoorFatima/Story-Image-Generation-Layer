"""
agents/character_designer.py — Character Designer Agent
Extracts character profiles from scene_manifest.
Maintains identity consistency across all scenes.
Outputs: character_db.json
"""

import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state import WritersRoomState
import tool_registry as mcp

def character_designer_node(state: WritersRoomState) -> WritersRoomState:
    """
    LangGraph node: Character Designer Agent.
    Extracts character profiles and persists to ChromaDB + character_db.json.
    """
    print("\n[Character Designer Agent] Extracting character identities...")

    # ── Step 1: Discover tools ────────────────────────────────────────────────
    available_tools = mcp.discover_tools()
    required = {"extract_characters", "commit_memory"}
    missing = required - set(available_tools)
    if missing:
        return {**state, "status": "failed", "error": f"Missing MCP tools: {missing}"}

    # ── Step 2: Extract characters via MCP ───────────────────────────────────
    try:
        character_db = mcp.invoke("extract_characters", {
            "scene_manifest": state["scene_manifest"]
        })
    except Exception as e:
        return {**state, "status": "failed", "error": f"Character extraction failed: {str(e)}"}

    characters = character_db.get("characters", [])
    print(f"[Character Designer Agent] Extracted {len(characters)} characters: "
          f"{[c['name'] for c in characters]}")

    # ── Step 3: Persist each character to vector memory ───────────────────────
    if characters:
        try:
            mcp.invoke("commit_memory", {
                "collection": "character_metadata",
                "documents": [
                    f"{c['name']}: {c['appearance_description']}" for c in characters
                ],
                "metadatas": [
                    {
                        "name": c["name"],
                        "style": c.get("reference_style", "cinematic"),
                        "traits": ", ".join(c.get("personality_traits", [])),
                    }
                    for c in characters
                ],
                "ids": [f"char_{c['name'].lower().replace(' ', '_')}" for c in characters],
            })
            print("[Character Designer Agent] Characters committed to memory.")
        except Exception as e:
            print(f"[Character Designer Agent] Warning: memory commit failed: {e}")

    # ── Step 4: Save character_db.json ────────────────────────────────────────
    os.makedirs("outputs", exist_ok=True)
    output_path = "outputs/character_db.json"
    with open(output_path, "w") as f:
        json.dump(character_db, f, indent=2)
    print(f"[Character Designer Agent] Saved → {output_path}")

    return {
        **state,
        "character_db": character_db,
        "status": "processing",
    }