# 🎮 BabelMeow — Play Guide (final setup)

## 🚀 เริ่มเล่น (ทุกครั้ง)

1. **Double-click `PLAY.bat`** → เปิด Ollama (11435) + Bridge (11434) ให้อัตโนมัติ
2. เปิด **Diablo IV** → Settings → Display → **Borderless Windowed**
3. **Double-click `start_rst_admin.bat`** → เปิด RST แบบ admin (กด UAC: Yes)
4. ใน RST:
   - **Translation tab** → Ollama, URL `http://127.0.0.1:11434`, model `babelmeow-th`
   - **OCR** → OneOCR
   - **Language** → English → Thai
   - **Context/Overlay** → Font = ฟอนต์ไทย (Tahoma / Leelawadee UI)
5. กลับไป D4 → RST: **Select Window** → Diablo IV
6. **Alt+Q** เลือกพื้นที่ → **Alt+F** overlay → **Alt+G** เริ่มแปล

## 🧠 ระบบทำงานยังไง (3 ชั้น)

```
RST OCR ข้อความ
   ↓
Bridge (11434):
   1. cache lookup (96k คำ)   <50ms  ← ชื่อ/ปุ่ม/menu/affix
   2. template (dynamic)       <50ms  ← "Defeat the X", "+12 Strength"
   3. fuzzy (OCR error)        ~30ms  ← "Necromaneer"->เนโครแมนเซอร์
   4. live fallback (4B LLM)   ~1s    ← description ยาว/OCR มั่ว -> แปลสด + cache
   ↓
overlay ไทย
```

- ชั้น 1-3 = ใช้ cache ที่แปลไว้ (เร็ว, คุณภาพสูง, VRAM 0)
- ชั้น 4 = แปลสดด้วย LLM เฉพาะที่ cache ไม่มี → **เก็บเข้า cache** (ครั้งหน้าเร็ว)
- เล่นไปเรื่อยๆ cache จะครบขึ้น live fallback จะถูกเรียกน้อยลง

## 💾 VRAM (RX 9070 XT 16GB)

| | VRAM |
|---|---|
| D4 | ~8 GB |
| Ollama 4B (live) | ~3.5 GB |
| desktop/อื่นๆ | ~2-3 GB |
| **รวม** | **~14 GB** (พอดี) |

> ⚠️ ปิด Chrome/โปรแกรมหนัก + หยุดอัดวิดีโอ ตอนเล่น เพื่อกัน VRAM เกิน
> ถ้า overlay ช้าผิดปกติ = VRAM เกิน → ปิด live (ดูล่าง)

## ⚙️ ปรับ OCR (RST → OCR Settings) ให้แม่นขึ้น

| Setting | แนะนำ | ผล |
|---|---|---|
| Min letter confidence | 0.1 → **0.4** | ตัดตัวอ่านมั่ว |
| Min line confidence | 0.1 → **0.4** | ตัดบรรทัดมั่ว |
| Multi Selection Area | เปิด | เลือกหลายจุด (quest+dialog) |

> region เล็ก = OCR แม่น + เร็ว + แตกคำน้อย → เลือกกรอบเฉพาะ tooltip/dialog ดีกว่ากรอบใหญ่ทั้งจอ

## 🔧 ปิด Live Fallback (โหมด VRAM 0)

ถ้าอยากให้ game ได้ VRAM เต็มที่ (description ที่ cache ไม่มีจะเป็น EN):

แก้ `PLAY.bat` → เปลี่ยน `set BABELMEOW_LIVE=1` เป็น `set BABELMEOW_LIVE=0`
(ไม่ต้องเปิด Ollama เลย → ประหยัด 3.5GB)

## 📊 ดูสถานะ

- Bridge stats: เปิด browser → `http://localhost:11434/stats`
  - `hit_rate_pct` สูง = cache ครอบคลุมดี
  - `live` = จำนวนที่แปลสด (จะค่อยๆ เพิ่มแล้วนิ่ง)

## 🩹 ปัญหาที่เจอ + วิธีแก้

| อาการ | สาเหตุ | แก้ |
|---|---|---|
| ช้า 2 วิทุกครั้ง | localhost IPv6 | ✅ แก้แล้ว (dual-stack) — ถ้ายังช้า ใช้ 127.0.0.1 ใน RST |
| description เป็น EN | cache miss + live off | เปิด live (PLAY.bat) |
| ตัวอักษร □□□ | font ไม่ใช่ไทย | RST → Overlay → Font ไทย |
| overlay ช้า/กระตุก | VRAM เกิน | ปิด Chrome/recording หรือปิด live |
| คำแปลแปลกๆ | 4B LLM พลาด (เช่น skeleton) | คำพวกนี้ส่วนน้อย — แก้ทีหลังได้ |

## 🔮 อนาคต (ทำให้ดีขึ้นอีก)

- **Pre-translate gaps offline**: re-extract description ที่ขาด (D4Analyzer Powers module) → batch แปล 8B → เพิ่ม cache → runtime VRAM 0 + คุณภาพสูง (แทน live)
- เก็บ live translations ที่สะสมไว้ กลับเข้า cache ถาวร
- แชร์ cache.db ให้คนไทยคนอื่นใช้ (ไม่ต้องแปลใหม่)
