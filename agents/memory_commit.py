"""
agents/memory_commit.py — Memory Commit Node
Final node: persists all outputs and writes the deliverable JSON files.
Outputs: scene_manifest.json, character_db.json (updated with images)
"""

import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state import WritersRoomState
import tool_registry as mcp

def memory_commit_node(state: WritersRoomState) -> WritersRoomState:
    """
    LangGraph node: Memory Commit.
    Saves all final outputs and marks pipeline as complete.
    """
    print("\n[Memory Commit] Persisting final outputs...")

    os.makedirs("outputs", exist_ok=True)

    # ── Save scene_manifest.json ──────────────────────────────────────────────
    if state.get("scene_manifest"):
        path = "outputs/scene_manifest.json"
        with open(path, "w") as f:
            json.dump(state["scene_manifest"], f, indent=2)
        print(f"[Memory Commit] ✓ Saved → {path}")

    # ── Save character_db.json (with image paths) ─────────────────────────────
    if state.get("character_db"):
        path = "outputs/character_db.json"
        with open(path, "w") as f:
            json.dump(state["character_db"], f, indent=2)
        print(f"[Memory Commit] ✓ Saved → {path}")

    # ── Commit image refs to vector memory ───────────────────────────────────
    image_paths = state.get("image_paths", [])
    if image_paths:
        try:
            mcp.invoke("commit_memory", {
                "collection": "image_references",
                "documents": image_paths,
                "metadatas": [{"type": "character_image"} for _ in image_paths],
                "ids": [f"img_{i}" for i, _ in enumerate(image_paths)],
            })
            print(f"[Memory Commit] ✓ {len(image_paths)} image references committed to ChromaDB.")
        except Exception as e:
            print(f"[Memory Commit] Warning: image ref commit failed: {e}")

    # ── Print summary ─────────────────────────────────────────────────────────
    scenes = state.get("scene_manifest", {}).get("scenes", [])
    characters = state.get("character_db", {}).get("characters", [])

    print("\n" + "="*60)
    print("  PIPELINE COMPLETE — PROJECT MONTAGE PHASE 1")
    print("="*60)
    print(f"  Scenes generated  : {len(scenes)}")
    print(f"  Characters created: {len(characters)}")
    print(f"  Images generated  : {len(image_paths)}")
    print(f"  Output directory  : ./outputs/")
    print("="*60)

    return {
        **state,
        "memory_committed": True,
        "status": "complete",
    }