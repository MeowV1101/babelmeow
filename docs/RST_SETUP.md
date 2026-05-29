# 🎮 RSTGameTranslation + BabelMeow Bridge — Setup

> เชื่อม RST → bridge ของเรา → cache.db (174k คำแปลไทย)

## ⚠️ RST ต้องรันแบบ Administrator

RST ทำ overlay + screen capture → ต้องการสิทธิ์ admin
ถ้าเปิดธรรมดาจะ **ปิดเงียบทันที**

**วิธีเปิด:**
- Double-click `start_rst_admin.bat` (จะเด้ง UAC → กด Yes)
- หรือ right-click `D:\claude\Tools\RST\RSTGameTranslation\rst.exe` → **Run as administrator**

## 📋 ก่อนเริ่ม — เปิด 3 อย่าง

| | คำสั่ง/ไฟล์ | สถานะ |
|---|---|---|
| 1. Ollama (GPU) | `scripts\start_ollama_gpu.bat` | ควรรันอยู่แล้ว |
| 2. **Bridge** | `scripts\start_bridge.bat` | **ต้องเปิด** (port 11435) |
| 3. RST (admin) | `start_rst_admin.bat` | เปิดแบบ admin |

> ตรวจ bridge: เปิด browser ไป `http://localhost:11435/` ควรเห็น `{"status":"ok",...}`

## ⚙️ ตั้งค่า RST (ทำครั้งเดียว)

### 1. OCR
**Settings → OCR → เลือก `OneOCR`** (built-in ไม่ต้องติดตั้ง)

### 2. Language
**Settings → Language:**
- Source: **English**
- Target: **Thai**

### 3. Translation → Ollama ⭐ (จุดสำคัญ)
**Settings → Translation → เลือก `Ollama`**

ตั้งค่า:
| ช่อง | ค่า |
|---|---|
| Ollama URL / Endpoint | `http://localhost:11435` |
| Model | `babelmeow-th` |

> ⚠️ ใส่ **11435** (bridge) ไม่ใช่ 11434 (Ollama จริง)
> ถ้า model dropdown ว่าง → กด refresh, bridge จะส่งชื่อ `babelmeow-th` ให้

## 🚀 เริ่มแปล

1. เปิด **Diablo IV** (Borderless Windowed)
2. ใน RST กด **Select Window** → เลือก Diablo IV
3. **Alt+Q** → ลากเลือกพื้นที่ที่จะแปล (เช่น quest text มุมขวาบน)
4. **Alt+F** → เปิด overlay
5. **Alt+G** → เริ่ม/หยุดแปล

## 🔍 ดูว่า bridge ทำงานไหม

ขณะเล่น เปิด browser ไป `http://localhost:11435/stats`
```json
{"exact":120,"normalized":15,"fuzzy":8,"live":0,"miss":3,
 "requests":146,"hit_rate_pct":98.0}
```
- hit_rate สูง = cache ครอบคลุมดี
- miss เยอะ = ข้อความยังไม่อยู่ใน cache (เปิด live fallback ช่วยได้)

## 🐛 ดู log เพื่อจูน

`bridge_requests.log` บันทึกทุก request ที่ RST ส่งมา:
```json
{"endpoint":"generate","raw":"...","extracted":"Slay the Butcher",
 "method":"exact","th":"สังหารบุชเชอร์"}
```
ใช้ดูว่า:
- RST ส่ง format อะไรมา (เผื่อต้องปรับ `extract_source_text`)
- คำไหน miss บ่อย → เพิ่มเข้า glossary/cache

## 🔧 เปิด Live Fallback (หลัง batch เสร็จ)

ตอน batch แปลยังรันอยู่ เราปิด live fallback ไว้ (กันแย่ง Ollama)
พอ batch เสร็จ เปิดได้:

```powershell
# หยุด bridge เดิม แล้วเปิดใหม่โดยไม่ตั้ง BABELMEOW_LIVE=0
Get-Process python | Where-Object { $_.CommandLine -like '*overlay_bridge*' } | Stop-Process -Force
cd D:\claude\BabelMeow
& "C:\Users\lnwza\AppData\Local\Programs\Python\Python312\python.exe" -m babelmeow.overlay_bridge.server
```

หรือ double-click `scripts\start_bridge.bat` (live fallback ON by default)

## 🩹 Troubleshooting

| ปัญหา | แก้ |
|---|---|
| RST เปิดแล้วปิดเลย | ต้องรัน admin (`start_rst_admin.bat`) |
| Model dropdown ว่าง | bridge ไม่ได้เปิด — เช็ค `localhost:11435` |
| แปลออกมาเป็น EN | cache miss + live off — เปิด live หรือรอ batch เสร็จ |
| overlay ไม่ขึ้น | D4 ต้อง Borderless, RST ต้อง admin |
| ตัวอักษรไทยเป็น □□□ | RST font ไม่รองรับไทย → เปลี่ยน overlay font เป็น Noto Sans Thai ใน Settings |
