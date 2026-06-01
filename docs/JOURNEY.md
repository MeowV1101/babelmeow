# 📖 BabelMeow — บันทึกการเดินทาง (เอกสารเรียนรู้สำหรับมือใหม่)

> เอกสารนี้เล่าทุกขั้นตอนของการสร้างระบบแปล Diablo IV เป็นภาษาไทย
> รวมถึง **สิ่งที่ลองแล้วไม่เวิร์ก** เพราะ "ทางตัน" คือบทเรียนที่ดีที่สุด
>
> เป้าหมาย: ให้คนที่ไม่เคยทำ เข้าใจได้ว่า "ทำไม" ไม่ใช่แค่ "ทำอะไร"

---

## 🎯 โจทย์เริ่มต้น

> "อยากทำ mod ภาษาไทย Diablo IV"

ฟังดูง่าย แต่พอเจาะจริง มีกำแพงเต็มไปหมด เอกสารนี้เล่าว่าเราชนกำแพงอะไรบ้าง และข้ามมายังไง

---

## 🗺 ภาพรวมสุดท้าย (ระบบที่ได้)

```
═══════ ทำครั้งเดียว (OFFLINE) ═══════
  D4 game files → [Extract] → 174k ข้อความ EN
       → [Batch แปลด้วย AI ในเครื่อง] → SQLite "พจนานุกรม" 96k คำ

═══════ ตอนเล่น (RUNTIME) ═══════
  จอเกม → [จับภาพ+OCR] → [ค้นพจนานุกรม] → [overlay ไทยทับจอ]
                              ↓ ถ้าไม่มีในพจนานุกรม
                          [AI แปลสด + จำไว้]
```

**หัวใจ:** แปลล่วงหน้าเก็บใส่พจนานุกรม → ตอนเล่นแค่ "เปิดพจนานุกรม" (เร็ว, ไม่กิน VRAM)
ไม่ใช่ "คิดแปลใหม่ทุกครั้ง" (ช้า, กิน VRAM, แย่งเกม)

---

## 🧱 ทำไมไม่ "mod ตรงๆ" — ทางตันแรก

ความคิดแรกของคนทั่วไป: "ก็แก้ไฟล์ภาษาในเกมเลยสิ"

**ลองคิดแล้วพบว่าทำไม่ได้:**

| กำแพง | เหตุผล |
|---|---|
| ไฟล์ถูก pack | D4 ใช้ระบบ CASC ของ Blizzard — ทุกอย่างอยู่ในไฟล์ `data.000`-`data.156` |
| เกม online + anti-cheat | แก้ไฟล์ client = เสี่ยง **โดน ban** |
| launcher verify ไฟล์ | เปิดเกมทีก็ download ไฟล์เดิมกลับ — แก้ไปก็สูญ |
| ฟอนต์ไม่มีไทย | ต่อให้แปลได้ ตัวอักษรไทยจะเป็น □□□ (font atlas ไม่มี glyph ไทย) |

**บทเรียน #1:** ก่อนลงมือ ต้องเข้าใจ "ข้อจำกัดของแพลตฟอร์ม" — บางทีวิธีที่ตรงที่สุดคือวิธีที่ทำไม่ได้

**ทางออก:** ไม่แตะเกมเลย → ทำ **overlay translator** (อ่านจอ → แปล → วาดทับ) เหมือน OBS/Discord ทับเกม = ปลอดภัย

---

## 🔬 สิ่งที่ลองแล้ว "ไม่เวิร์ก" (Dead-ends) — เรียนจากความผิดพลาด

### ❌ 1. DeepL แปลไทย
ตอนแรกวางแผนใช้ DeepL (ดังเรื่องคุณภาพ) — **แต่ DeepL ไม่รองรับภาษาไทย** (พ.ค. 2026)
→ บทเรียน: เช็คว่า tool รองรับภาษาเป้าหมายก่อน อย่าเพิ่งวางแผนรอบมัน

### ❌ 2. แปลสดด้วย LLM ตอนเล่น (naive approach)
ถ้าให้ AI แปลทุกข้อความขณะเล่น: D4 (8GB) + LLM (6GB) + OCR = VRAM เกิน → เกมกระตุก, แปลช้า 2-3 วิ
→ บทเรียน: นี่คือเหตุผลที่ overlay translator ทั่วไป "ไม่ค่อยเวิร์ก" → เราเลยเลือก **แปลล่วงหน้า** แทน

### ❌ 3. ใช้ผม (Claude) แปลทั้งหมดผ่าน chat
ประเมินแล้ว: 100k strings = ส่ง chat 1000+ ครั้ง = 10 sessions × 5 ชม = เปลืองมาก
→ บทเรียน: งาน volume สูง ควรใช้ API/local model แบบ batch ไม่ใช่ chat ทีละข้อความ

### ❌ 4. Ollama รันบน CPU (ไม่รู้ตัว!)
RX 9070 XT ใหม่เกินไป (RDNA4) → Ollama default fallback ไป CPU เงียบๆ → ช้า 5 เท่า
→ ค้นพบเพราะ user ถาม "VRAM เหลือเอามาช่วยได้ไหม" → เช็คแล้วเจอ `ollama ps` ขึ้น "100% CPU"
→ **บทเรียนสำคัญที่สุด:** อย่าเชื่อว่ามันใช้ GPU — **วัดเสมอ** (`ollama ps`, GPU utilization)
→ แก้ด้วย `OLLAMA_VULKAN=1`

### ❌ 5. d4-asset-extractor (tool แรกที่หา)
เป็น tool ดึง texture เท่านั้น ไม่ดึงข้อความ → เปลี่ยนไปใช้ **D4Analyzer** (ดึง StringList ได้)
→ บทเรียน: หา tool ให้ตรงงาน อย่าฝืนใช้ของผิดประเภท

### ❌ 6. localhost ช้า 2 วินาที
RST ต่อ `localhost` → Windows ลอง IPv6 (`::1`) ก่อน → bridge ฟังแค่ IPv4 → timeout 2 วิ
→ ค้นพบโดยจับเวลา: connection ใหม่ช้า 2055ms แต่ reuse 2ms
→ แก้ด้วย dual-stack socket (ฟังทั้ง IPv6+IPv4)
→ **บทเรียน:** ปัญหา "ช้า" บางทีไม่ใช่ที่ logic แต่ที่ networking layer — ต้องวัดแยกชั้น

### ❌ 7. live fallback ช้า 34 วินาที
ครั้งแรกที่เปิด live: 34 วิ! เพราะ glossary system prompt ยาว (~1500 tokens) prefill บน 4B ช้า
→ แก้ด้วย "light prompt" (สั้นๆ) → เหลือ ~1 วิ (เร็วขึ้น 30 เท่า)
→ บทเรียน: prompt ยาว = prefill ช้า โดยเฉพาะ model เล็ก

### ❌ 8. Settle Time ไม่ใช่ตัวการ
user รู้สึก "ต้องค้างแปปนึงถึงแปล" → คิดว่า OCR ช้า → วัดแล้ว OCR แค่ 76ms, bridge 3ms
→ ตัวจริงคือ live translation คำใหม่ (~1s) + RST settle time
→ บทเรียน: **วัดก่อนแก้** อย่าเดาว่าอะไรช้า

---

## 🪜 การเดินทางทีละ Phase

### Phase 0 — สำรวจ & ตัดสินใจสถาปัตยกรรม
- สำรวจโฟลเดอร์เกม → พบ CASC
- ตัดสินใจ: overlay (ปลอดภัย) ไม่ใช่ mod ไฟล์ (เสี่ยง ban)
- ตัดสินใจ: pre-translate (เร็ว) ไม่ใช่ live ตอนเล่น (กิน VRAM)
- ตัดสินใจ: local AI (ฟรี, privacy) ไม่ใช่ cloud API
- **เครื่องมือ:** Translumo/RST (overlay) + Ollama + Typhoon (Thai LLM) + Python

### Phase 1 — Pipeline แปล + เครื่องมือ
- ติดตั้ง Ollama, Python, ดาวน์โหลด Translumo
- โหลด Typhoon 2 8B + Typhoon Translate 4B (เทียบกัน)
- เขียน: glossary (คำศัพท์เฉพาะ) + post-process (บังคับ glossary + กู้ placeholder)
- **ค้นพบ:** glossary วางบนสุดของ prompt → คุณภาพ 10/10

### Phase 2 — ดึงข้อความจากเกม
- ลอง d4-asset-extractor (ไม่ได้) → เจอ **D4Analyzer** (ได้!)
- กด "Copy Selected" → clipboard → save TSV → parse เป็น JSON
- **ผล:** 174,817 ข้อความ (dedup เหลือ ~96k unique = ประหยัด 41%)

### Phase 3 — แปลทั้งหมด (batch)
- SQLite cache (resume ได้ ถ้าหยุดกลางคัน)
- รัน parallel หลาย worker
- **ค้นพบ CPU bug → แก้เป็น GPU → เร็วขึ้น 7 เท่า** (80ชม → 12ชม)
- ปรับ workers 5→7 (ใช้ GPU headroom) → เสร็จ 96k คำ

### Phase 4 — Bridge (กาวเชื่อม)
- เขียน FastAPI server ปลอมเป็น Ollama → RST คุยด้วยได้
- 3 ชั้นค้นหา: exact → normalized → fuzzy (กู้ OCR ที่อ่านพลาด)
- **ค้นพบ:** RST v5 ส่ง prompt แบบซับซ้อน (JSON + ##|||## separator) → ต้องแกะ format

### Phase 5 — ข้อความ dynamic
- "Defeat the {MONSTER}" → จับ template → ดึงค่า → แปลค่านั้นต่อ
- "+12 Strength" → "+12 พลังกาย" (เลขคงเดิม)
- **ค้นพบ:** markup ซับซ้อน ({if:}/{c_label}/{SF_1}) → ขยายตัวจับให้ครอบคลุม

### Phase 6 — เล่นจริง + แก้ปัญหารัว
- ❌ ต่อไม่ติด → ย้าย port
- ❌ ออกอังกฤษ → แกะ RST format
- ❌ ช้า 2วิ → dual-stack
- ❌ description มั่ว → live fallback + concurrent + light prompt
- ✅ **เล่นได้จริง!**

---

## 💎 บทเรียนสำคัญ (สรุป)

1. **เข้าใจข้อจำกัดแพลตฟอร์มก่อน** — บางวิธีตรงสุดแต่ทำไม่ได้ (mod = ban)
2. **วัดก่อนแก้** — CPU/GPU, localhost/IPv6, OCR/bridge/live — เดาผิดเสียเวลา
3. **แยกชั้นเวลา debug** — ปัญหา "ช้า" อาจอยู่ที่ network ไม่ใช่ logic
4. **pre-compute > compute-on-demand** — แปลล่วงหน้าเก็บ cache ดีกว่าแปลสด
5. **fallback เป็นชั้นๆ** — exact → fuzzy → template → live → echo (เร็วก่อน แม่นทีหลัง)
6. **memoize ทุกอย่างที่ซ้ำ** — RST ส่งซ้ำตลอด, จำไว้ = เร็วขึ้นมหาศาล
7. **tool ที่ใช่ > ฝืน tool ที่ผิด** — d4-asset-extractor → D4Analyzer
8. **commit บ่อยๆ** — แต่ละ phase push GitHub, ย้อนได้, มี CI ตรวจ

---

## 📂 ไฟล์ในโปรเจกต์ (แต่ละอันทำอะไร)

```
BabelMeow/
├── PLAY.bat                    ← กดเดียวเปิดทุกอย่างเพื่อเล่น
├── start_rst_admin.bat         ← เปิด RST แบบ admin
├── babelmeow/
│   ├── translators/
│   │   ├── glossary.py         ← โหลดคำศัพท์เฉพาะ (Lilith→ลิลิธ)
│   │   ├── ollama.py           ← คุยกับ AI แปล + system prompt
│   │   └── postprocess.py      ← บังคับ glossary + กู้ placeholder + จับ error
│   ├── runtime/
│   │   └── cache.py            ← SQLite พจนานุกรม (resume-able)
│   └── overlay_bridge/
│       ├── matcher.py          ← 5 ชั้นค้นหา (exact/norm/template/fuzzy/miss)
│       ├── template.py         ← จับ dynamic text ({MONSTER}, +12)
│       └── server.py           ← FastAPI ปลอม Ollama + live fallback
├── scripts/
│   ├── parse_d4_strings.py     ← TSV → JSON
│   ├── filter_strings.py       ← กรอง + dedup (174k→96k)
│   ├── translate_batch.py      ← แปลทั้งหมด (parallel, resume)
│   ├── upgrade_live.py         ← ยกคุณภาพคำที่ live เจอ (4B→8B)
│   └── monitor_progress.py     ← ดู progress batch
├── games/diablo4/
│   ├── glossary.yaml           ← 68 คำศัพท์เฉพาะ D4
│   └── cache.db                ← 96k+ คำแปล (หัวใจระบบ)
├── tests/                      ← 46 unit tests
└── docs/                       ← เอกสารทั้งหมด
```

---

## 📚 คำศัพท์เทคนิค (สำหรับมือใหม่)

| คำ | ความหมายง่ายๆ |
|---|---|
| **CASC** | ระบบ pack ไฟล์ของ Blizzard (เหมือน zip ยักษ์) |
| **OCR** | อ่านตัวอักษรจากภาพ (Optical Character Recognition) |
| **overlay** | หน้าต่างโปร่งใสวาดทับจอ |
| **LLM** | AI ภาษา (Large Language Model) เช่น Typhoon |
| **VRAM** | RAM ของการ์ดจอ — เกม+AI แย่งกันใช้ |
| **cache** | ที่เก็บผลลัพธ์ไว้ใช้ซ้ำ (พจนานุกรมของเรา) |
| **fuzzy match** | จับคู่แบบ "ใกล้เคียงพอ" (กู้ OCR ที่อ่านพลาด) |
| **template** | แม่แบบที่มีช่องว่าง ("Defeat the ___") |
| **fallback** | แผนสำรองเมื่อวิธีหลักไม่ได้ |
| **memoize** | จำผลลัพธ์ไว้ ไม่คำนวณซ้ำ |
| **dual-stack** | socket ที่รับทั้ง IPv4 และ IPv6 |
| **placeholder** | ช่องตัวแปร เช่น {MONSTER}, {SF_1} |

---

## 🌍 ถ้าจะทำเกมอื่น / ภาษาอื่น

ระบบนี้ใช้ซ้ำได้ ~70%:

**ใช้ซ้ำได้:** bridge, matcher, template, cache, batch translator, overlay (RST)

**ต้องทำใหม่ต่อเกม:**
- Extractor (ขึ้นกับ engine — Unity/Unreal ง่ายกว่า CASC มาก)
- Glossary (ชื่อตัวละคร/ของ/สถานที่)
- Translation dictionary

**เปลี่ยนภาษา:** แค่เปลี่ยน target language ตอน batch translate + ฟอนต์ overlay

> เกม **Unity/Unreal** (single-player) มักแก้ไฟล์ตรงได้เลย (ไม่มี anti-cheat) — ง่ายกว่า D4

---

## ✅ สถานะสุดท้าย

- 96,000+ คำแปลไทยใน cache
- เล่น D4 เห็นไทย real-time (UI/menu/skill/quest/item)
- live fallback เติมส่วนที่ขาด (~1วิ แล้วจำ)
- ปลอดภัย ไม่แตะไฟล์เกม ไม่เสี่ยง ban
- 46 unit tests + CI เขียว
- repo: https://github.com/MeowV1101/babelmeow

**จาก idea เล่นๆ → ระบบที่ใช้งานได้จริง** 🐱
