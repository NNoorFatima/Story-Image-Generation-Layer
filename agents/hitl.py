"""
agents/hitl.py — Human-in-the-Loop Agent
Provides a review checkpoint BEFORE character extraction and image generation.
Prevents hallucinated scripts from propagating downstream.
"""

import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state import WritersRoomState


def hitl_node(state: WritersRoomState) -> WritersRoomState:
    """
    LangGraph node: Human-in-the-Loop checkpoint.
    Prints the generated script to the terminal and asks for user approval.
    In a web UI, this would be replaced by an interrupt + resume pattern.
    """
    print("\n" + "="*70)
    print("  HUMAN-IN-THE-LOOP REVIEW  ")
    print("="*70)
    print("The following script has been generated. Please review:\n")

    manifest = state.get("scene_manifest", {})
    scenes = manifest.get("scenes", [])

    for scene in scenes:
        print(f"\n── SCENE {scene.get('scene_id', '?')} | {scene.get('location', '?')} ──")
        print(f"   Characters: {', '.join(scene.get('characters', []))}")
        print(f"   Action: {scene.get('action_description', '')}")
        for line in scene.get("dialogue", []):
            print(f"   {line.get('speaker', '?')}: \"{line.get('line', '')}\"")
            print(f"     [Visual cue: {line.get('visual_cue', '')}]")

    print("\n" + "="*70)
    print("Options: [y] Approve  [n] Reject  [e] Edit feedback")
    choice = input("Your choice: ").strip().lower()

    if choice == "y":
        print("[HITL] Script approved. Continuing pipeline...\n")
        return {
            **state,
            "hitl_approved": True,
            "hitl_feedback": None,
            "status": "processing",
        }
    elif choice == "e":
        feedback = input("Enter your feedback for the scriptwriter: ").strip()
        print(f"[HITL] Feedback recorded: '{feedback}'")
        # In a full system this would loop back to scriptwriter with the feedback.
        # For Phase 1, we store feedback and still proceed.
        return {
            **state,
            "hitl_approved": True,
            "hitl_feedback": feedback,
            "status": "processing",
        }
    else:
        print("[HITL] Script rejected by user.")
        return {
            **state,
            "hitl_approved": False,
            "hitl_feedback": "User rejected the script.",
            "status": "failed",
            "error": "Script rejected at HITL checkpoint.",
        }