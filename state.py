"""
state.py — Shared LangGraph State Schema
All agents read from and write to this TypedDict.
"""

from typing import TypedDict, Optional, Literal
from pydantic import BaseModel


# ── Scene-level models ────────────────────────────────────────────────────────

class DialogueLine(BaseModel):
    speaker: str
    line: str
    visual_cue: str


class Scene(BaseModel):
    scene_id: int
    location: str
    characters: list[str]
    dialogue: list[DialogueLine]
    action_description: str = ""


class SceneManifest(BaseModel):
    scenes: list[Scene]


# ── Character models ──────────────────────────────────────────────────────────

class Character(BaseModel):
    name: str
    personality_traits: list[str]
    appearance_description: str
    reference_style: str
    image_path: Optional[str] = None


class CharacterDB(BaseModel):
    characters: list[Character]


# ── LangGraph Shared State ────────────────────────────────────────────────────

class WritersRoomState(TypedDict):
    # Input
    input_mode: Literal["manual", "auto"]
    raw_input: str                          # user prompt OR raw script text

    # Script layer
    scene_manifest: Optional[dict]          # serialised SceneManifest
    script_valid: Optional[bool]
    validation_errors: Optional[list[str]]

    # HITL
    hitl_approved: Optional[bool]
    hitl_feedback: Optional[str]

    # Character layer
    character_db: Optional[dict]            # serialised CharacterDB

    # Image layer
    image_paths: Optional[list[str]]

    # Memory
    memory_committed: Optional[bool]

    # Pipeline control
    status: Literal["processing", "awaiting_hitl", "complete", "failed"]
    error: Optional[str]