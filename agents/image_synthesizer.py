"""
agents/image_synthesizer.py — Image Synthesizer Agent
Generates visual representations of each character.
Uses Hugging Face SDXL via MCP (no direct API calls).
Output: outputs/images/<character_name>.png
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state import WritersRoomState
import tool_registry as mcp

def image_synthesizer_node(state: WritersRoomState) -> WritersRoomState:
    """
    LangGraph node: Image Synthesizer Agent.
    Iterates over character_db and generates one reference image per character.
    """
    print("\n[Image Synthesizer Agent] Starting character image generation...")

    character_db = state.get("character_db", {})
    characters = character_db.get("characters", [])

    if not characters:
        print("[Image Synthesizer Agent] No characters found, skipping image generation.")
        return {**state, "image_paths": [], "status": "processing"}

    # ── Step 1: Discover tools ────────────────────────────────────────────────
    available_tools = mcp.discover_tools()
    if "generate_character_image" not in available_tools:
        return {**state, "status": "failed", "error": "MCP tool 'generate_character_image' unavailable"}

    # ── Step 2: Generate image per character ──────────────────────────────────
    os.makedirs("outputs/images", exist_ok=True)
    image_paths = []

    for character in characters:
        name = character["name"]
        safe_name = name.lower().replace(" ", "_")
        output_path = f"outputs/images/{safe_name}.png"

        print(f"[Image Synthesizer Agent] Generating image for: {name}...")

        try:
            result = mcp.invoke("generate_character_image", {
                "character_name": name,
                "appearance_description": character.get("appearance_description", ""),
                "style": character.get("reference_style", "cinematic"),
                "output_path": output_path,
            })
            image_paths.append(result["path"])
            print(f"[Image Synthesizer Agent] ✓ Saved → {result['path']}")

            # Update character record with image path
            character["image_path"] = result["path"]

        except Exception as e:
            print(f"[Image Synthesizer Agent] ✗ Failed for {name}: {e}")
            # Non-fatal — continue with other characters
            image_paths.append(None)

    # ── Step 3: Update character_db with image paths ──────────────────────────
    updated_db = {**character_db, "characters": characters}

    return {
        **state,
        "character_db": updated_db,
        "image_paths": [p for p in image_paths if p],
        "status": "processing",
    }