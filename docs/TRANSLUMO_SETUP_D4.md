# 🎮 Translumo + Diablo IV — Setup Guide

> ทดสอบ Phase 1 จริง: overlay capture + OCR กับ D4

## 📋 ก่อนเริ่ม

ต้องเปิดทั้ง 2 โปรแกรมไว้:

| App | สถานะ |
|---|---|
| Battle.net Launcher | login พร้อม |
| Diablo IV | พร้อมเล่น |
| Translumo | อยู่ที่ `D:\claude\Tools\Translumo\Translumo.exe` |
| Ollama server | ✅ รันอยู่แล้ว (background) |

---

## Step 1️⃣ — ตั้ง D4 เป็น Borderless Windowed

**สำคัญมาก!** Translumo capture fullscreen exclusive ไม่ได้

1. เปิด Diablo IV
2. ไปที่ **Settings → Video → Display Mode**
3. เลือก **`Fullscreen Windowed`** หรือ **`Borderless Windowed`**
4. Resolution คงที่ (เลือกตัวที่ใช้ปกติ)
5. **กด Apply**

💡 **Tip:** หลังจากนี้ resolution ห้ามเปลี่ยน เพราะ region preset จะผูกกับ resolution

---

## Step 2️⃣ — เปิด Translumo

ดับเบิลคลิก: **`D:\claude\Tools\Translumo\Translumo.exe`**

> ครั้งแรกที่เปิด Windows อาจถาม SmartScreen → กด **More info → Run anyway** (เป็นเรื่องปกติของแอป unsigned)

---

## Step 3️⃣ — ตั้งค่า Translumo

### A. Language Settings

หน้า **Settings** (รูปฟันเฟือง):

| ตัวเลือก | ค่า |
|---|---|
| Source language | English |
| Target language | Thai (or whatever Thai is shown) |
| OCR engine | **EasyOCR** (แม่นสุดสำหรับเกม) |
| Translator | **Google Translate** (เริ่มต้นด้วยตัวฟรีก่อน) |

> เรายังไม่ใช้ Ollama ของเรา — Phase 4 ค่อยทำ bridge ทีหลัง

### B. Capture Area

หน้า **Capture Areas**:

1. คลิก **+ Add Area** หรือ "New Area"
2. ตั้งชื่อเช่น `Quest Tracker`
3. คลิก **Set bounds** → ลากกรอบที่หน้าจอ D4
   - แนะนำเริ่มจาก **มุมขวาบน** ที่เป็น quest tracker
4. **OCR engine:** EasyOCR
5. **Source language:** English
6. กด **Save**

### C. Hotkey

ตั้ง hotkey toggle on/off เช่น **F8** หรือ **Ctrl+Shift+T**

---

## Step 4️⃣ — เริ่มทดสอบ

1. กลับไปที่ D4 (เกมต้องอยู่หน้าจอ)
2. กด hotkey ที่ตั้งไว้
3. Translumo จะ:
   - Capture region ที่ตั้งไว้
   - OCR ข้อความ EN
   - แปลผ่าน Google Translate
   - แสดง overlay ภาษาไทย

---

## 🐛 Troubleshooting

### "ไม่เห็น overlay"
- ตรวจสอบ D4 เป็น Borderless จริง (ไม่ใช่ Fullscreen Exclusive)
- เช็คว่า Translumo รันด้วยสิทธิ์ Administrator (ลอง right-click → Run as administrator)
- เช็คว่า region overlap กับเกม

### "OCR อ่านได้แต่ไม่แม่น"
- เพิ่ม contrast/brightness ใน D4
- ขยาย region ให้ครอบข้อความเต็มๆ
- ลองเปลี่ยน OCR engine: Windows OCR หรือ Tesseract
- D4 ใช้ font stylized — บาง EasyOCR model อ่านยาก ลอง upscale capture

### "OCR อ่านไม่ได้เลย"
- เช็คว่า OCR engine ติดตั้ง model EN แล้ว
- ลอง screenshot region แล้วเปิดดู ว่ามีตัวอักษรชัดไหม

### "แปลผิดความหมาย"
- ปกติเลย เพราะใช้ Google Translate ฟรี
- **Phase 3** จะใช้ Typhoon 2 + glossary ของเรา ผลจะดีกว่า

---

## ✅ Phase 1 Success Criteria

หลังตั้งค่าเสร็จ ทดสอบให้ครบ:

- [ ] Translumo capture หน้าจอ D4 ได้ (ไม่ดำ ไม่ crash)
- [ ] OCR อ่าน text EN จาก D4 ได้ (อ่านถูก >80%)
- [ ] Overlay แสดงผลขณะเล่น (ไม่บัง gameplay)
- [ ] FPS ของเกมไม่ตกผิดปกติ
- [ ] Hotkey toggle on/off ทำงาน

ถ้าผ่านครบ → พร้อมไป **Phase 2 (Extract strings จาก CASC)**

---

## 📝 Notes for Phase 4

ตอน Phase 4 เราจะ:
1. เขียน FastAPI server impersonate Ollama
2. ตั้ง Translumo translator = "Ollama" หรือ custom HTTP
3. ข้อมูลแปลทั้งหมดมาจาก SQLite ของเรา (pre-translated)
4. VRAM runtime = 0 (ไม่ใช้ LLM ตอนเล่น)

ตอนนี้แค่พิสูจน์ว่า Translumo + D4 ทำงานก่อน
