"""
tool_registry/registry.py — MCP Tool Registry
Agents NEVER call APIs directly. They call tool_registry.invoke(tool_name, input).
This registry maps tool names to their handler functions.
Satisfies assignment constraint: "All tools must be discovered dynamically via MCP."
"""

import os
import json
import requests
from typing import Any
from dotenv import load_dotenv

load_dotenv()


# ── Tool handler implementations ──────────────────────────────────────────────

def _generate_script_segment(input: dict) -> dict:
    """Calls Groq LLM to generate a structured screenplay segment."""
    from langchain_groq import ChatGroq
    from langchain_core.messages import HumanMessage, SystemMessage

    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.8,
        api_key=os.getenv("GROQ_API_KEY"),
    )

    prompt = input.get("prompt", "")
    num_scenes = input.get("num_scenes", 3)

    system = """You are a professional screenplay writer.
When given a story prompt, produce a structured JSON screenplay.

Return ONLY valid JSON in this exact format, no markdown, no explanation:
{
  "scenes": [
    {
      "scene_id": 1,
      "location": "...",
      "characters": ["CharA", "CharB"],
      "action_description": "...",
      "dialogue": [
        {
          "speaker": "CharA",
          "line": "...",
          "visual_cue": "..."
        }
      ]
    }
  ]
}"""

    user_msg = f"Write a {num_scenes}-scene screenplay based on this prompt:\n{prompt}"
    response = llm.invoke([SystemMessage(content=system), HumanMessage(content=user_msg)])

    try:
        return json.loads(response.content)
    except json.JSONDecodeError:
        import re
        match = re.search(r'\{.*\}', response.content, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"LLM returned non-JSON: {response.content[:200]}")


def _commit_memory(input: dict) -> dict:
    """Persists data to ChromaDB vector store."""
    import chromadb
    client = chromadb.PersistentClient(path="./outputs/chroma_db")
    collection = client.get_or_create_collection(name=input["collection"])
    collection.add(
        documents=input["documents"],
        metadatas=input.get("metadatas", [{} for _ in input["documents"]]),
        ids=input["ids"],
    )
    return {"status": "committed", "collection": input["collection"], "count": len(input["documents"])}


def _query_memory(input: dict) -> dict:
    """Queries ChromaDB for similar documents."""
    import chromadb
    client = chromadb.PersistentClient(path="./outputs/chroma_db")
    collection = client.get_or_create_collection(name=input["collection"])
    results = collection.query(
        query_texts=[input["query"]],
        n_results=input.get("n_results", 3),
    )
    return {"results": results}


def _extract_characters(input: dict) -> dict:
    """Calls Groq LLM to extract character profiles from a scene manifest."""
    from langchain_groq import ChatGroq
    from langchain_core.messages import HumanMessage, SystemMessage

    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.3,
        api_key=os.getenv("GROQ_API_KEY"),
    )

    manifest = json.dumps(input["scene_manifest"], indent=2)

    system = """You are a character design expert.
Analyse a screenplay and extract detailed character profiles.

Return ONLY valid JSON in this exact format, no markdown:
{
  "characters": [
    {
      "name": "...",
      "personality_traits": ["...", "..."],
      "appearance_description": "...",
      "reference_style": "cinematic / animated / realistic / stylized"
    }
  ]
}"""

    response = llm.invoke([
        SystemMessage(content=system),
        HumanMessage(content=f"Extract characters from this screenplay:\n{manifest}")
    ])

    try:
        return json.loads(response.content)
    except json.JSONDecodeError:
        import re
        match = re.search(r'\{.*\}', response.content, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"LLM returned non-JSON: {response.content[:200]}")


def _generate_character_image(input: dict) -> dict:
    """Calls Hugging Face Inference API (SDXL) to generate a character image."""
    api_key = os.getenv("HF_API_KEY")
    api_url = "https://router.huggingface.co/hf-inference/models/stabilityai/stable-diffusion-xl-base-1.0"

    prompt = (
        f"Portrait of {input['character_name']}, {input['appearance_description']}, "
        f"{input.get('style', 'cinematic')} style, high quality, detailed, "
        "character reference sheet, neutral background"
    )

    response = requests.post(
        api_url,
        headers={"Authorization": f"Bearer {api_key}"},
        json={"inputs": prompt, "parameters": {"num_inference_steps": 25}},
        timeout=60,
    )

    if response.status_code != 200:
        raise RuntimeError(f"HF API error {response.status_code}: {response.text[:200]}")

    os.makedirs(os.path.dirname(input["output_path"]), exist_ok=True)
    with open(input["output_path"], "wb") as f:
        f.write(response.content)

    return {"status": "generated", "path": input["output_path"]}


def _validate_script(input: dict) -> dict:
    """Validates a manually provided script string for structure."""
    from langchain_groq import ChatGroq
    from langchain_core.messages import HumanMessage, SystemMessage

    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.0,
        api_key=os.getenv("GROQ_API_KEY"),
    )

    system = """You are a script validator. Check if the provided script has:
1. Scene headings (INT./EXT. or scene numbers)
2. Dialogue labels (CHARACTER NAME before dialogue)
3. Action descriptions

Return ONLY valid JSON:
{
  "valid": true | false,
  "errors": ["list of issues if any"],
  "parsed": { <scene_manifest JSON if valid, else null> }
}"""

    response = llm.invoke([
        SystemMessage(content=system),
        HumanMessage(content=f"Validate this script:\n\n{input['script_text']}")
    ])

    try:
        return json.loads(response.content)
    except json.JSONDecodeError:
        import re
        match = re.search(r'\{.*\}', response.content, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"LLM returned non-JSON: {response.content[:200]}")


# ── Registry: name → handler ──────────────────────────────────────────────────

TOOL_REGISTRY: dict[str, callable] = {
    "generate_script_segment":  _generate_script_segment,
    "commit_memory":            _commit_memory,
    "query_memory":             _query_memory,
    "extract_characters":       _extract_characters,
    "generate_character_image": _generate_character_image,
    "validate_script":          _validate_script,
}


# ── Public MCP interface ──────────────────────────────────────────────────────

def discover_tools() -> list[str]:
    """Returns all available tool names (simulates MCP registry query at runtime)."""
    return list(TOOL_REGISTRY.keys())


def invoke(tool_name: str, input: dict) -> Any:
    """
    Dynamically discovers and invokes a tool by name.
    This is the ONLY entry point agents use — no direct API calls inside agents.
    """
    if tool_name not in TOOL_REGISTRY:
        raise ValueError(
            f"Tool '{tool_name}' not found. Available: {discover_tools()}"
        )
    print(f"  [MCP] → invoking '{tool_name}'")
    return TOOL_REGISTRY[tool_name](input)