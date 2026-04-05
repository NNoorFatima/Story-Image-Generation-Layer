# PROJECT MONTAGE — Phase 1: The Writer's Room
### Agentic AI (CS-4015) | FAST-NUCES

---

## What Was Expected vs What Was Built

### What the Assignment Asked For

The assignment required building **"The Writer's Room"** — the first phase of a larger AI-powered video generation pipeline called PROJECT MONTAGE. The core idea is simple: a human gives a raw story idea (or an existing script), and the system autonomously transforms it into a complete, structured, machine-readable screenplay with character visuals — ready to be consumed by future video/audio generation agents.

Specifically the assignment required:

- A **multi-agent system** where specialized AI agents collaborate, each with a defined role
- A **LangGraph stateful workflow** to orchestrate these agents with proper routing logic
- A **Supervisor-Worker architecture** where agents are coordinated through graph routing
- A **shared memory layer** using ChromaDB/FAISS so agents can persist and retrieve context
- **MCP-based tool discovery** — a strict constraint where agents NEVER call APIs directly, but instead discover and invoke tools through a central registry at runtime
- Support for **two input modes**: manually uploading a script, or giving a prompt and letting the AI write one
- A **Human-in-the-Loop checkpoint** where the user reviews the generated script before the pipeline continues
- Final deliverables: `scene_manifest.json`, `character_db.json`, and AI-generated character images

### What Was Actually Built

Every requirement above was implemented and verified to work end-to-end:

| Requirement | Implementation |
|---|---|
| Multi-agent system | 5 specialized agents: Scriptwriter, Validator, HITL, Character Designer, Image Synthesizer |
| LangGraph stateful workflow | `StateGraph` with 7 nodes and conditional routing edges |
| Supervisor-Worker model | LangGraph routing acts as the implicit supervisor; each agent is a worker node |
| Shared memory (ChromaDB) | All agents read/write a persistent `WritersRoomState` TypedDict; scripts, characters, and image refs are committed to ChromaDB |
| MCP-based tool discovery | `tool_registry/` module with `invoke()` and `discover_tools()` — agents call `mcp.discover_tools()` at runtime and never hardcode API URLs |
| Dual input modes | Mode 1 (manual): user pastes script → Validator Agent checks structure. Mode 2 (auto): user gives prompt → Scriptwriter Agent generates screenplay |
| Human-in-the-Loop | Pipeline pauses after script generation, prints the full script, and waits for user approval before continuing |
| scene_manifest.json | Generated with scene IDs, locations, characters, dialogue, and visual cues |
| character_db.json | Generated with name, personality traits, appearance description, reference style, and image path per character |
| Character images | Generated via HuggingFace SDXL (Stable Diffusion XL) and saved as PNG files |

---

## Project Structure

```
project_montage/
│
├── main.py                     # Entry point — CLI runner
├── workflow.py                 # LangGraph StateGraph definition
├── state.py                    # Shared state schema (WritersRoomState TypedDict)
├── requirements.txt            # Python dependencies
├── .env.example                # API key template
│
├── tool_registry/              # MCP Tool Layer
│   ├── __init__.py             # Exports invoke() and discover_tools()
│   └── registry.py            # All tool implementations + registry map
│
├── agents/                     # All agent nodes
│   ├── __init__.py
│   ├── scriptwriter.py         # Auto-generates screenplay from prompt
│   ├── validator.py            # Validates manually provided scripts
│   ├── hitl.py                 # Human review checkpoint
│   ├── character_designer.py   # Extracts character profiles
│   ├── image_synthesizer.py    # Generates character images
│   └── memory_commit.py        # Final persistence node
│
└── outputs/                    # Generated at runtime
    ├── scene_manifest.json     # Structured screenplay
    ├── character_db.json       # Character identity store
    ├── images/                 # AI-generated character PNGs
    └── chroma_db/              # ChromaDB persistent vector store
```

---

## File-by-File Explanation

### `state.py`
Defines `WritersRoomState` — a `TypedDict` that acts as the single shared memory object passed between every node in the LangGraph graph. Think of it as the "baton" in a relay race. Every agent reads what it needs from this state and writes its output back into it. Fields include `input_mode`, `raw_input`, `scene_manifest`, `character_db`, `image_paths`, `hitl_approved`, `status`, and more.

Also defines Pydantic models (`Scene`, `DialogueLine`, `Character`) for structured validation of the data shapes.

### `tool_registry/registry.py`
This is the MCP (Model Context Protocol) layer. It contains a dictionary called `TOOL_REGISTRY` mapping tool names to their handler functions. The two public functions are:

- `discover_tools()` — returns all available tool names (simulates querying an MCP registry at runtime)
- `invoke(tool_name, input)` — looks up and calls a tool by name

The six tools registered are:
- `generate_script_segment` — calls Groq LLaMA to write a screenplay
- `validate_script` — calls Groq LLaMA to check a manual script's structure
- `extract_characters` — calls Groq LLaMA to pull character profiles from a screenplay
- `generate_character_image` — calls HuggingFace SDXL to generate a character portrait
- `commit_memory` — saves documents to ChromaDB
- `query_memory` — retrieves similar documents from ChromaDB

**Why this matters:** The assignment strictly required that no agent hardcodes API calls. Every agent in this project calls `mcp.invoke("tool_name", {...})` exclusively. The actual API logic lives only here.

### `workflow.py`
Builds the LangGraph `StateGraph` and defines all routing logic. Contains:
- All 7 node registrations
- A conditional routing function after each node that decides the next step based on the current state
- The `run_pipeline()` convenience function that initializes state and invokes the compiled graph

### `agents/scriptwriter.py`
Triggered in `auto` mode. Queries the MCP registry for available tools, then calls `generate_script_segment` with the user's prompt. Adjusts the number of scenes based on prompt length (more detail = more scenes). Commits the script to ChromaDB memory and writes the scene manifest to state.

### `agents/validator.py`
Triggered in `manual` mode. Takes the raw script text the user pasted, calls `validate_script` via MCP, which uses an LLM to check for scene headings, dialogue labels, and action descriptions. If validation fails, the pipeline terminates with a list of errors. If it passes, the script is converted to the standardized JSON format.

### `agents/hitl.py`
Human-in-the-Loop checkpoint. After the script is ready (from either the Scriptwriter or Validator), the pipeline pauses and prints the full script to the terminal in a readable format. The user types `y` (approve), `n` (reject), or `e` (approve with feedback). If rejected, the graph terminates. If approved, the pipeline continues to character extraction.

### `agents/character_designer.py`
Calls `extract_characters` via MCP, which sends the full scene manifest to an LLM and gets back structured profiles for each character: name, personality traits, appearance description, and reference style. Each character is also committed to ChromaDB under the `character_metadata` collection. Saves `character_db.json` to disk.

### `agents/image_synthesizer.py`
Iterates over every character in `character_db` and calls `generate_character_image` via MCP for each one. This hits the HuggingFace SDXL model with a crafted prompt built from the character's appearance description and style. Saves each image as a PNG in `outputs/images/`. Image failures are non-fatal — the pipeline continues with other characters.

### `agents/memory_commit.py`
The final node. Writes the definitive `scene_manifest.json` and `character_db.json` (now updated with image paths) to disk. Commits image references to ChromaDB. Prints the final pipeline summary and marks `status` as `"complete"`.

### `main.py`
The CLI entry point. Handles interactive mode (shows a menu, collects user input) and argument mode (`--mode auto --input "..."`). Imports and calls `run_pipeline()` from `workflow.py` and reports the final result.

---

## Dependencies

```
langgraph          # Stateful multi-agent graph orchestration
langchain          # LLM abstraction layer
langchain-groq     # Groq API integration for LangChain
langchain-core     # Core LangChain primitives
chromadb           # Local vector database for persistent memory
requests           # HTTP calls to HuggingFace API
pillow             # Image file handling
python-dotenv      # .env file loading
pydantic           # Data validation and schema models
```

Install all dependencies:
```bash
pip install -r requirements.txt
```

---

## Setup Instructions

**Step 1 — Get API Keys (both free)**

- **Groq API Key:** Sign up at [console.groq.com](https://console.groq.com) → API Keys → Create Key
- **HuggingFace API Key:** Sign up at [huggingface.co](https://huggingface.co) → Settings → Access Tokens → New Token (read access is enough)

**Step 2 — Create your `.env` file**

```bash
cp .env.example .env
```

Open `.env` and fill in:
```
GROQ_API_KEY=gsk_your_key_here
HF_API_KEY=hf_your_key_here
```

**Step 3 — Create and activate virtual environment**

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

**Step 4 — Install dependencies**

```bash
pip install -r requirements.txt
```

**Step 5 — Run the pipeline**

```bash
python main.py
```

You will be prompted to choose between Auto mode (give a story prompt) or Manual mode (paste your own script).

---

## LangGraph — What It Is, How It's Used, and Why

### What is LangGraph?

LangGraph is a framework for building stateful, multi-step AI applications as directed graphs. Instead of running a linear chain of LLM calls, LangGraph lets you define a **graph** where:

- **Nodes** are functions (agents) that do work
- **Edges** are connections that define what runs next
- **Conditional edges** allow the graph to branch based on the current state — for example, routing to a different agent depending on whether a validation passed or failed
- **State** is a shared object that every node can read from and write to, persisted across the entire graph execution

### How LangGraph is Used in This Project

The graph is defined in `workflow.py` using `StateGraph(WritersRoomState)`.

**The 7 nodes registered:**

```
mode_selector_node      → Reads input_mode, decides the route
validator_node          → Validates manually provided scripts
scriptwriter_node       → Autonomously generates a screenplay
hitl_node               → Human review checkpoint
character_node          → Extracts character profiles
image_node              → Generates character images
memory_commit_node      → Final persistence and output
```

**The flow:**

```
START
  └─► mode_selector_node
        ├─► [if manual] validator_node
        └─► [if auto]   scriptwriter_node
                              │
                    [if failed] END
                    [if ok]   hitl_node
                                  │
                        [if rejected] END
                        [if approved] character_node
                                            │
                                      image_node
                                            │
                                    memory_commit_node
                                            │
                                           END
```

**Conditional routing example** from `workflow.py`:

```python
def route_after_hitl(state: WritersRoomState) -> str:
    return END if not state.get("hitl_approved") else "character_node"

graph.add_conditional_edges(
    "hitl_node",
    route_after_hitl,
    {"character_node": "character_node", END: END}
)
```

The routing function reads `hitl_approved` from the shared state and returns the name of the next node. LangGraph handles the actual branching.

### Why LangGraph Instead of a Simple Loop?

A simple Python `if/else` chain would technically work for a linear script, but LangGraph provides several critical advantages for this project:

**1. Stateful persistence across agents.** Every agent automatically receives the full accumulated state from all previous agents. There is no manual passing of variables between functions.

**2. Failure isolation.** If any agent sets `status = "failed"`, the conditional routing catches it and terminates the graph cleanly — no need for try/except chains spanning multiple files.

**3. Human-in-the-Loop support.** LangGraph is specifically designed for workflows that need to pause and wait for human input before resuming. The HITL node is a natural fit for this pattern.

**4. Scalability for future phases.** As PROJECT MONTAGE grows into Phase 2 (audio) and Phase 3 (video), new nodes can be added to this same graph without restructuring existing code. The graph is the architecture.

**5. Matches the assignment's architectural requirement.** The assignment specifically required a "LangGraph stateful workflow" with a Supervisor-Worker model. LangGraph's routing logic acts as the implicit supervisor, and each agent node is a worker.

---

## Outputs

After a successful run, the following files are created in the `outputs/` directory:

| File | Description |
|---|---|
| `scene_manifest.json` | Full structured screenplay: scene IDs, locations, characters, dialogue lines, visual cues |
| `character_db.json` | Character profiles: name, traits, appearance, style, image path |
| `images/<name>.png` | AI-generated portrait image for each character |
| `chroma_db/` | ChromaDB vector store containing script history, character metadata, and image references |

---

## Evaluation Rubric Mapping

| Criteria | Marks | How It's Satisfied |
|---|---|---|
| Agent Definition — clear roles, reasoning loops | 20 | 5 agents each with scoped responsibilities, reasoning logic, and MCP tool usage documented in code |
| Script Generation Quality — structured + coherent scenes | 15 | Groq LLaMA generates multi-scene screenplays with dialogue, visual cues, and character consistency |
| MCP Integration — proper tool usage, no hardcoding | 15 | All 6 tools discovered via `discover_tools()` and invoked via `invoke()` — zero hardcoded API calls in agents |
| LangGraph Workflow — StateGraph correctness | 10 | 7-node StateGraph with conditional edges, proper entry point, and END routing |
| Human-in-the-Loop — proper checkpoint design | 10 | `hitl_node` pauses pipeline, displays full script, handles approve/reject/feedback |
| Output Completeness — JSON + images generated | 5 | `scene_manifest.json`, `character_db.json`, and character PNGs all generated |
| **Total** | **75** | |

# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up your API keys
cp .env.example .env
# Edit .env → add your GROQ_API_KEY and HF_API_KEY

# 3. Run interactively
python main.py

# Or directly
python main.py --mode auto --input "Your story idea here"
