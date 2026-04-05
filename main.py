"""
main.py — PROJECT MONTAGE: The Writer's Room
Entry point for Phase 1 pipeline.

Usage:
    python main.py                         # interactive
    python main.py --mode auto             # prompts for story idea
    python main.py --mode manual           # prompts for script text
"""

import argparse
import sys
from dotenv import load_dotenv

load_dotenv()


# AUTO_EXAMPLE = (
#     "A young hacker discovers that the city's AI traffic system has become sentient "
#     "and is manipulating accidents to teach humans lessons about patience. "
#     "She must team up with a traffic cop who has been unknowingly helping the AI "
#     "to shut it down before the next 'lesson' kills someone."
# )
AUTO_EXAMPLE = (
    "In a remote mountain village where winter lasts nearly the entire year, "
    "a quiet mapmaker discovers that the mountains around the town keep changing "
    "their paths overnight. When travelers begin disappearing along routes that "
    "used to be safe, she realizes the shifting landscape is trying to hide "
    "something buried deep beneath the snow. With the help of a stubborn historian "
    "and a child who claims to hear the mountains whisper, she must uncover the "
    "truth before the village itself vanishes from every map in the world."
)

MANUAL_EXAMPLE = """
SCENE 1 - INT. POLICE STATION - NIGHT

DETECTIVE SARA reviews files at her desk.

DETECTIVE SARA
We've been looking at this all wrong.

OFFICER JAMES
(confused)
What do you mean?

DETECTIVE SARA
The killer isn't hiding from us. They're hiding in plain sight.

SCENE 2 - EXT. CITY ROOFTOP - DAWN

DETECTIVE SARA and OFFICER JAMES look out over the city.

DETECTIVE SARA
Every crime scene was within two blocks of a subway entrance.

OFFICER JAMES
(realizing)
They're using the tunnels.
"""


def get_input_interactively() -> tuple[str, str]:
    print("\n" + "="*60)
    print("  PROJECT MONTAGE — THE WRITER'S ROOM (Phase 1)")
    print("="*60)
    print("\nSelect input mode:")
    print("  [1] Auto   — Give a story prompt, AI writes the script")
    print("  [2] Manual — Paste your own script for validation")
    choice = input("\nChoice (1/2): ").strip()

    if choice == "2":
        print("\nPaste your script. Enter '---END---' on a new line when done.")
        print("(Press Enter immediately to use the built-in example)\n")
        lines = []
        while True:
            line = input()
            if line.strip() == "---END---":
                break
            lines.append(line)
        raw = "\n".join(lines).strip() or MANUAL_EXAMPLE
        return "manual", raw
    else:
        print(f"\nEnter your story prompt (or press Enter for the built-in example):\n")
        prompt = input("> ").strip() or AUTO_EXAMPLE
        return "auto", prompt


def main():
    parser = argparse.ArgumentParser(description="Project Montage — Writers Room")
    parser.add_argument("--mode", choices=["auto", "manual"])
    parser.add_argument("--input", type=str)
    args = parser.parse_args()

    if args.mode and args.input:
        input_mode, raw_input = args.mode, args.input
    else:
        input_mode, raw_input = get_input_interactively()

    print(f"\n[Main] Starting pipeline in '{input_mode}' mode...")

    from workflow import run_pipeline
    final_state = run_pipeline(input_mode, raw_input)

    status = final_state.get("status")
    if status == "complete":
        print("\n✅ Pipeline completed successfully!")
        print("   └─ outputs/scene_manifest.json")
        print("   └─ outputs/character_db.json")
        print("   └─ outputs/images/<character>.png")
    elif status == "failed":
        print(f"\n❌ Pipeline failed: {final_state.get('error', 'Unknown error')}")
        sys.exit(1)
    else:
        print(f"\n⚠️  Pipeline ended with status: {status}")


if __name__ == "__main__":
    main()