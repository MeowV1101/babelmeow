# BabelMeow — Project Plan

> Universal game translation overlay for Thai players (and beyond)
> เริ่มต้นด้วย Diablo IV เป็นเกมแรก แต่ออกแบบเป็น framework ใช้ได้ทุกเกม

---

## 🎯 เป้าหมาย

สร้างระบบแปลเกมเป็นภาษาไทย (และภาษาอื่นๆ ในอนาคต) ที่:

1. **ปลอดภัย** — ไม่แตะไฟล์เกม, ไม่เสี่ยงโดน ban
2. **ฟรี 100%** — ใช้ local AI, ไม่มี API cost
3. **คุณภาพสูง** — pre-translate ครั้งเดียวด้วย LLM แล้วตรวจสอบได้
4. **ใช้ซ้ำได้** — framework รองรับหลายเกมในอนาคต
5. **ผู้ใช้ทั่วไปใช้ได้** — install ง่าย, ใช้ง่าย

---

## 🏗 Architecture

### Pipeline ภาพรวม

```
═══════════════ Offline (one-time per game) ═══════════════

  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
  │   Extract    │ →  │  Translate   │ →  │   Dictionary │
  │ (game files) │    │ (local LLM)  │    │   (SQLite)   │
  └──────────────┘    └──────────────┘    └──────────────┘

═══════════════ Runtime (while playing) ═══════════════

  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
  │ Screen OCR   │ →  │   Lookup     │ →  │   Overlay    │
  │ (Translumo)  │    │  (SQLite)    │    │ (transparent)│
  └──────────────┘    └──────────────┘    └──────────────┘
                            ↑
                     ไม่ใช้ AI runtime
                     VRAM = 0
```

### Component Layers

| Layer | หน้าที่ | Tools/Libraries |
|---|---|---|
| **Extractor** | ดึง strings จาก game files | `d4-asset-extractor`, Unity AssetStudio, UnrealPak |
| **Translator** | แปล EN → TH (offline batch) | Ollama + **Typhoon 2 8B** |
| **Storage** | เก็บ dictionary | SQLite |
| **Bridge** | impersonate translator API | FastAPI (fake Ollama endpoint) |
| **Overlay** | capture + OCR + display | Translumo หรือ RSTGameTranslation |

---

## 🤖 Translation Model

### หลัก: **Typhoon 2 8B** (SCB10X)
- ✅ Thai-tuned LLM ทำในไทย
- ✅ เข้าใจสำนวน/บริบทไทยดี
- ✅ ขนาดเหมาะกับ VRAM 16 GB (~6 GB ใช้งาน)
- ✅ ฟรี ตลอด ไม่มี rate limit
- ✅ Run ผ่าน Ollama (CLI + HTTP API)

**Ollama command:**
```bash
ollama pull scb10x/llama3.1-typhoon2-8b-instruct
```

### สำรอง (ลองเทียบทีหลัง)
- **Qwen 2.5 14B** — multilingual general
- **NLLB-200 3.3B** — dedicated translation
- **Aya Expanse 8B** — multilingual

> **เริ่มที่ Typhoon 2 ก่อน** ถ้าคุณภาพไม่พอค่อย benchmark ตัวอื่น

---

## 🛠 Hardware (เครื่องเป้าหมาย)

```
GPU:    AMD Radeon RX 9070 XT (16 GB VRAM, RDNA 4)
RAM:    32 GB
OS:     Windows 11
```

### AMD-specific notes
- RX 9070 XT ใหม่มาก (Q1 2025) — RDNA 4 = gfx1201
- ตัวเลือก backend:
  1. **ROCm 7.1+** — เร็วสุด, ต้อง config นิดหน่อย
  2. **Vulkan** — set `OLLAMA_VULKAN=1`, ง่ายกว่า
  3. **LM Studio** — GUI ที่ auto-detect (สำหรับ test model)

---

## 📅 Development Phases

### Phase 1 — Recon & Setup (1-2 ชม) ⏳ เริ่มที่นี่
**เป้า:** พิสูจน์ว่า overlay translator ทำงานกับ D4 ได้

- [ ] ติดตั้ง Translumo (หรือ RSTGameTranslation)
- [ ] ตั้ง D4 เป็น Borderless Windowed
- [ ] ทดสอบ Translumo + Google Translate ฟรี กับ D4
- [ ] ลอง capture region: quest tracker, dialog, tooltip, item, skill
- [ ] **Decision point:** ใช้ Translumo ได้ดีไหม? ถ้าไม่ → switch RST

### Phase 2 — Extract Strings (4-8 ชม)
**เป้า:** ได้ JSON ของข้อความ EN ทั้งหมดในเกม

- [ ] Clone [d4-asset-extractor](https://github.com/game-strategy-hq/d4-asset-extractor)
- [ ] รัน extractor ชี้ไปที่ `C:\Program Files (x86)\Diablo IV\Data\`
- [ ] หา localization files (.stl หรือ format อะไรก็ตาม)
- [ ] Parse → JSON: `[{id, key, en_text, category}, ...]`
- [ ] คาดว่าจะได้ ~50k-150k strings

**Fallback:** ถ้า extract ไม่สำเร็จ → datamine จากเว็บ wiki (maxroll.gg, d4builds.gg)

### Phase 3 — Pre-translate (4-6 ชม run time)
**เป้า:** ได้ SQLite dict ขนาด EN→TH ทั้งหมด

- [ ] ติดตั้ง Ollama + Typhoon 2 8B
- [ ] สร้าง `glossary.yaml` ด้วยมือ — 100 คำสำคัญ (class, NPC, location, item type)
- [ ] เขียน script Python batch translator
- [ ] ส่ง batch 50 strings/call พร้อม glossary ใน system prompt
- [ ] จัดการ format placeholder: `{0}`, `%1$s`, `{playerName}`
- [ ] Schema: `translations(en_text, th_text, category, verified, updated_at)`

### Phase 4 — Bridge: Local Dict ↔ Overlay Tool (1-2 วัน)
**เป้า:** ทำให้ Translumo/RST ใช้ dictionary ของเราแทน API ออนไลน์

แนวทาง: **Fake Ollama Server** (FastAPI impersonator)
- เขียน FastAPI server ที่ implement Ollama's `/api/generate` endpoint
- ส่ง EN text → lookup ใน SQLite → ส่งกลับ TH text
- ตั้ง RSTGameTranslation ให้ใช้ Ollama URL = `localhost:11434`

### Phase 5 — Fuzzy Matching for Variants (1 วัน)
**เป้า:** จัดการข้อความที่มี dynamic part

- [ ] สร้าง regex templates: `r"\+(\d+) Strength"` → `"+$1 พลัง"`
- [ ] Pre-extract template patterns จาก strings ที่มี `{n}` หรือ `%d`
- [ ] Runtime: exact match → template match → fallback EN

### Phase 6 — Real-world Testing (ต่อเนื่อง)
- เล่นเกม, จด strings ที่ขาด/ผิด
- เพิ่มเข้า cache.db
- Refine glossary
- ปรับ region presets

---

## 📁 Project Structure

```
BabelMeow/
├── README.md
├── pyproject.toml
├── .gitignore
├── babelmeow/                 # core package
│   ├── __init__.py
│   ├── extractors/            # game extractors
│   │   ├── base.py
│   │   ├── diablo4.py
│   │   └── unity.py
│   ├── translators/           # batch translation backends
│   │   ├── base.py
│   │   ├── ollama.py
│   │   └── nllb.py
│   ├── overlay_bridge/        # fake-ollama server
│   │   └── server.py
│   └── runtime/               # lookup/cache logic
│       └── dict.py
├── games/                     # game-specific config
│   └── diablo4/
│       ├── config.yaml
│       ├── glossary.yaml
│       └── cache.db
├── scripts/
│   ├── extract.py
│   ├── translate_batch.py
│   └── start_bridge.bat
├── tests/
└── docs/
    ├── PLAN.md                # ไฟล์นี้
    ├── GITHUB_SETUP.md
    └── PHASE1_RECON.md
```

---

## ⚠️ ความเสี่ยง & แผนสำรอง

| ความเสี่ยง | ระดับ | แผนสำรอง |
|---|---|---|
| d4-asset-extractor extract ไม่ได้ | กลาง | datamine จากเว็บ wiki / d4builds.gg |
| String table encrypted | ต่ำ | Blizzard ไม่ค่อย encrypt localization |
| OCR อ่านผิด เช่น "O" vs "0" | สูง | ใช้ EasyOCR ดีสุด, pre-process contrast |
| Font ในเกมเป็น stylized | กลาง | ปรับ region, อาจ train OCR เพิ่ม |
| Translumo ไม่ support custom backend | กลาง | switch เป็น RSTGameTranslation |
| Typhoon 2 คุณภาพไม่พอ | ต่ำ | ลอง Qwen 14B / NLLB 3.3B |
| AMD ROCm/Vulkan compat | กลาง | LM Studio fallback |
| Patch ใหม่เพิ่ม strings | ต่ำ | re-run extract + translate batch |

---

## 🎮 รองรับเกมอื่นในอนาคต

Framework reusable ~70% — แต่ละเกมต้องเพิ่ม:
- Extractor specific (ขึ้นกับ engine)
- Glossary (NPC, locations, items)
- Translation dictionary
- Region presets

### เกมที่ extract ง่าย (เพิ่มได้เร็ว)
- **Unity** games (Hollow Knight, Stardew Valley) — AssetStudio
- **Unreal** games (Black Myth: Wukong, Lies of P) — UnrealPak, FModel
- **Source** games — VPK tools

### เกมที่ extract ยาก
- Capcom RE Engine
- กล่องดำเกมเอเชียบางตัว

---

## 🚀 Roadmap ระยะยาว (ถ้าโปรเจกต์ไปดี)

### Phase A — โอเพนซอร์ส (3-6 เดือน)
- เปิด GitHub public
- เขียน docs ให้ดี
- รับ contributor ช่วย add game support
- สร้าง community Discord

### Phase B — Web platform (6-12 เดือน)
- เว็บโหลด dictionary ของแต่ละเกม
- Community submit translations
- Mascot แมว 🐱 + branding
- Domain: babelmeow.dev / babelmeow.app

### Phase C — Pro features (ระยะไกล)
- One-click installer GUI
- Auto-update dictionaries
- Voice translation (TTS)
- Mobile companion app

---

## 📊 Success Metrics

- ✅ **Phase 1 success:** Translumo overlay ทับ D4 ทำงาน ไม่ crash
- ✅ **Phase 3 success:** 80%+ ของ strings ใน D4 มีคำแปลไทยใน SQLite
- ✅ **Phase 4 success:** เล่นเกม + overlay ทำงาน real-time ไม่มี lag
- ✅ **MVP done:** เล่น D4 จบ campaign ด้วย overlay ไทยได้

---

## 📝 หมายเหตุ

- **Privacy:** ทุก step ทำในเครื่องเอง, ไม่ส่งข้อมูลออก
- **Licensing:** จะใช้ MIT (เปิดทั้ง framework) — dictionary ของแต่ละเกมอาจแยก license
- **TOS Compliance:** ไม่แตะไฟล์เกม, ไม่ inject process, overlay-only = ปลอดภัย

---

*เริ่ม project: 2026-05-28*
*Status: Phase 1 ready to start*
