"""
Test Typhoon 2 translation quality with D4 sample strings.

Usage:
    python scripts/test_translate.py
    python scripts/test_translate.py --model scb10x/typhoon-translate1.5-4b
    python scripts/test_translate.py --model scb10x/llama3.1-typhoon2-8b-instruct
"""

import argparse
import json
import time
from pathlib import Path

import requests
import yaml

OLLAMA_URL = "http://localhost:11434/api/generate"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLES_FILE = PROJECT_ROOT / "games" / "diablo4" / "sample_strings.json"
GLOSSARY_FILE = PROJECT_ROOT / "games" / "diablo4" / "glossary.yaml"


def build_glossary_prompt(glossary: dict) -> str:
    lines = ["You are a professional game translator. Translate EN to TH for Diablo IV."]
    lines.append("\nUse these EXACT translations for proper nouns (case-sensitive):")
    for section, mapping in glossary.items():
        if section.startswith("_") or not isinstance(mapping, dict):
            continue
        for en, th in mapping.items():
            lines.append(f"  - {en} → {th}")
    lines.append("\nRules:")
    lines.append("- Preserve placeholders like {0}, %1$s, {playerName} EXACTLY")
    lines.append("- Numbers and damage values stay the same format")
    lines.append("- Output ONLY the Thai translation, no quotes, no English, no explanation")
    return "\n".join(lines)


def translate_one(model: str, system: str, en_text: str) -> tuple[str, float]:
    payload = {
        "model": model,
        "prompt": f"Translate to Thai:\n{en_text}",
        "system": system,
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 200},
    }
    start = time.time()
    r = requests.post(OLLAMA_URL, json=payload, timeout=120)
    r.raise_for_status()
    elapsed = time.time() - start
    return r.json()["response"].strip(), elapsed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--model",
        default="scb10x/typhoon-translate1.5-4b",
        help="Ollama model name",
    )
    args = ap.parse_args()

    print(f"[Model] {args.model}")
    print(f"[Ollama] {OLLAMA_URL}\n")

    with open(SAMPLES_FILE, encoding="utf-8") as f:
        samples = json.load(f)["samples"]

    with open(GLOSSARY_FILE, encoding="utf-8") as f:
        glossary = yaml.safe_load(f)

    system = build_glossary_prompt(glossary)
    print(f"[Glossary] {len([k for s in glossary.values() if isinstance(s, dict) for k in s])} terms loaded\n")
    print("=" * 80)

    total_time = 0.0
    for i, sample in enumerate(samples, 1):
        en = sample["en"]
        category = sample["category"]
        expected = sample.get("expected_th_style", "—")

        try:
            th, elapsed = translate_one(args.model, system, en)
            total_time += elapsed
        except Exception as e:
            print(f"[{i:2d}] ERROR: {e}")
            continue

        print(f"\n[{i:2d}] ({category}) {elapsed:.1f}s")
        print(f"     EN: {en}")
        print(f"     TH: {th}")
        print(f"     ~?: {expected}")

    print("\n" + "=" * 80)
    print(f"[Done] {len(samples)} samples in {total_time:.1f}s "
          f"(avg {total_time/len(samples):.2f}s/string)")


if __name__ == "__main__":
    main()
