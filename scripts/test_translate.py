"""
Test Typhoon 2 translation quality with D4 sample strings + post-process.

Usage:
    python scripts/test_translate.py
    python scripts/test_translate.py --model scb10x/typhoon-translate1.5-4b
    python scripts/test_translate.py --model scb10x/llama3.1-typhoon2-8b-instruct
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from babelmeow.translators import Glossary, OllamaTranslator, PostProcessor

SAMPLES_FILE = PROJECT_ROOT / "games" / "diablo4" / "sample_strings.json"
GLOSSARY_FILE = PROJECT_ROOT / "games" / "diablo4" / "glossary.yaml"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--model",
        default="scb10x/llama3.1-typhoon2-8b-instruct",
        help="Ollama model name",
    )
    args = ap.parse_args()

    glossary = Glossary.from_yaml(GLOSSARY_FILE)
    translator = OllamaTranslator(model=args.model)
    processor = PostProcessor(glossary=glossary)

    print(f"[Model]    {args.model}")
    print(f"[Glossary] {len(glossary)} terms loaded")
    print(f"[Ollama]   {translator.url}\n")
    print("=" * 80)

    with open(SAMPLES_FILE, encoding="utf-8") as f:
        samples = json.load(f)["samples"]

    system = translator.build_system(glossary.to_prompt_block())

    total_time = 0.0
    fixed_count = 0
    review_count = 0

    for i, sample in enumerate(samples, 1):
        en = sample["en"]
        category = sample["category"]

        try:
            result = translator.translate(en, system)
            total_time += result.elapsed_sec
        except Exception as e:
            print(f"[{i:2d}] ERROR: {e}")
            continue

        # Post-process
        pp = processor.process(en, result.th)
        if pp.fixes:
            fixed_count += 1
        if pp.needs_review:
            review_count += 1

        print(f"\n[{i:2d}] ({category}) {result.elapsed_sec:.1f}s")
        print(f"     EN:  {en}")
        if pp.fixes:
            print(f"     Raw: {pp.original}")
            print(f"     Fix: {pp.corrected}  ← {', '.join(pp.fixes)}")
        else:
            print(f"     TH:  {pp.corrected}")
        if pp.warnings:
            for w in pp.warnings:
                print(f"     ⚠️  {w}")

    print("\n" + "=" * 80)
    print(
        f"[Summary] {len(samples)} samples in {total_time:.1f}s "
        f"(avg {total_time/len(samples):.2f}s/string)"
    )
    print(f"[Auto-fixed] {fixed_count} strings")
    print(f"[Needs review] {review_count} strings")


if __name__ == "__main__":
    main()
