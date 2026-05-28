# Phase 1 — Recon & Setup Progress

> Status: 🚧 In progress
> Started: 2026-05-28

## ✅ Completed

- [x] ติดตั้ง gh CLI (GitHub.cli 2.93.0)
- [x] Login GitHub (user: MeowV1101)
- [x] git init + initial commit
- [x] สร้าง repo `babelmeow` (public) บน GitHub
- [x] Push code ขึ้น GitHub
- [x] ดาวน์โหลด Translumo 1.0.2 (478 MB) → `D:\claude\Tools\Translumo`
- [x] ติดตั้ง Ollama 0.24.0
- [x] Start Ollama server
- [x] เตรียม sample D4 strings (10 entries, 8 categories)
- [x] เตรียม glossary D4 (80+ terms)
- [x] เขียน test script Python

## 🔄 In Progress

- [ ] Pull `scb10x/typhoon-translate1.5-4b` (~2.5 GB) — dedicated translator
- [ ] Pull `scb10x/llama3.1-typhoon2-8b-instruct` (~5 GB) — general LLM
- [ ] ทดสอบคุณภาพแปล D4 sample strings

## 📋 Next (after Phase 1 test)

- [ ] เทียบคุณภาพ 4B translator vs 8B general — เลือกตัวที่ดีกว่า
- [ ] ทดสอบ Translumo จับหน้าจอ D4 (user ต้องเปิด D4)
- [ ] ทดสอบ Translumo OCR ภาษาอังกฤษ
- [ ] **Decision point:** Translumo OK หรือ switch RST?

## 🛠 Tools Installed

| Tool | Version | Path |
|---|---|---|
| Git | 2.54.0 | system PATH |
| GitHub CLI | 2.93.0 | `C:\Program Files\GitHub CLI\gh.exe` |
| Ollama | 0.24.0 | `%LOCALAPPDATA%\Programs\Ollama\ollama.exe` |
| Translumo | 1.0.2 | `D:\claude\Tools\Translumo\Translumo.exe` |

## 📁 Files Created This Phase

- `README.md`
- `.gitignore`
- `pyproject.toml`
- `docs/PLAN.md`
- `docs/GITHUB_SETUP.md`
- `docs/PHASE1_PROGRESS.md` (this file)
- `games/diablo4/sample_strings.json`
- `games/diablo4/glossary.yaml`
- `scripts/test_translate.py`

## 🔗 Links

- GitHub repo: https://github.com/MeowV1101/babelmeow
- Translumo: https://github.com/Danily07/Translumo
- Typhoon Translate: https://ollama.com/scb10x/typhoon-translate1.5-4b
- Typhoon 2 8B: https://ollama.com/scb10x/llama3.1-typhoon2-8b-instruct
