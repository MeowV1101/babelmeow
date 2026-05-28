# 🔄 Batch Operations Guide

> วิธีจัดการ full batch translate (รัน 1-5 วัน)

## ✅ สถานะ batch ปัจจุบัน

Started: 2026-05-28 ~23:09 (timezone +07)
Target: 96,061 unique D4 strings → SQLite cache
Workers: 6 parallel
Model: scb10x/llama3.1-typhoon2-8b-instruct

## 📊 Monitor Progress

### วิธีง่ายสุด: Double-click `monitor.bat`

หรือใน terminal:
```powershell
cd D:\claude\BabelMeow
python scripts\monitor_progress.py
```

จะแสดง:
- Progress bar (X / 96,061)
- ETA
- Rate (strings/sec ปัจจุบัน)
- Latest 5 translations
- Per-category breakdown

## 🛑 หยุด batch ชั่วคราว

Batch รันเป็น Python process — หยุดได้แบบไหน:

### Method 1: หา process แล้ว kill
```powershell
Get-Process -Name python | Where-Object { $_.CommandLine -like "*translate_batch*" } | Stop-Process
```

### Method 2: ผ่าน Task Manager
- เปิด Task Manager (Ctrl+Shift+Esc)
- หา `python.exe` ที่ใช้ ~315 MB RAM
- End task

> ⚠️ **ไม่ต้องกลัวข้อมูลหาย** — cache.db save ทุก string ทันทีที่แปลเสร็จ
> **Resume** ได้ทันทีโดยรัน batch ซ้ำ — มันจะ skip ของที่แปลแล้ว

## ▶️ Resume หลังหยุด/restart

```powershell
cd D:\claude\BabelMeow
python scripts\translate_batch.py --workers 6 --report-every 50
```

หรือ background:
```powershell
Start-Job -ScriptBlock {
    cd D:\claude\BabelMeow
    python scripts\translate_batch.py --workers 6 --report-every 50
}
```

## ⚡ Adjust Performance

### เพิ่ม workers (เร็วขึ้น แต่ contention มากขึ้น)
```powershell
python scripts\translate_batch.py --workers 8
```

### ลด workers (สำหรับเล่นเกม/ใช้ GPU พร้อมกัน)
```powershell
python scripts\translate_batch.py --workers 2
```

### เปลี่ยน model (เร็วกว่า แต่ quality ต่ำลง)
```powershell
python scripts\translate_batch.py --model scb10x/typhoon-translate1.5-4b
```

## 🔍 Query Cache โดยตรง

```powershell
# จำนวน entries
python -c "import sqlite3; print(sqlite3.connect('games/diablo4/cache.db').execute('SELECT COUNT(*) FROM translations').fetchone()[0])"

# Top categories
python -c "import sqlite3; [print(r) for r in sqlite3.connect('games/diablo4/cache.db').execute('SELECT category, COUNT(*) FROM translations GROUP BY category ORDER BY 2 DESC')]"

# Strings ที่ต้อง review
python -c "import sqlite3,sys; sys.stdout.reconfigure(encoding='utf-8'); [print(r[0]) for r in sqlite3.connect('games/diablo4/cache.db').execute('SELECT en_text FROM translations WHERE needs_review=1 LIMIT 20')]"
```

## 💾 Backup Cache

```powershell
Copy-Item games\diablo4\cache.db games\diablo4\cache.db.backup
```

แนะนำ backup ทุก 12 ชั่วโมง ระหว่างที่รัน

## ⚠️ ข้อควรระวัง

| สถานการณ์ | สิ่งที่ต้องรู้ |
|---|---|
| PC sleep | Batch หยุด — เปิดเครื่องแล้ว resume ได้ |
| PC restart | ต้อง start Ollama + start batch ใหม่ |
| Ollama crash | Python จะ error — restart Ollama + batch |
| Disk full | cache.db ปกติแค่ ~30 MB ตอนเต็ม — ไม่น่ามีปัญหา |
| GPU เกินร้อน | ลด workers หรือพักให้เย็น |

## 🛌 Tip: ป้องกัน Sleep ระหว่างรัน

```powershell
# ป้องกัน sleep แต่ปิดจอได้
powercfg /change standby-timeout-ac 0

# กลับเป็นปกติทีหลัง (30 นาที)
powercfg /change standby-timeout-ac 30
```

## 📈 Expected Timeline

| Workers | ETA |
|---|---|
| 2 | ~10 วัน |
| 4 | ~5 วัน |
| **6 (ปัจจุบัน)** | **~3-4 วัน** |
| 8 | ~2-3 วัน |

> หมายเหตุ: ETA ขึ้นกับ GPU load, อุณหภูมิ, อย่าใช้เล่นเกมหนักพร้อมกัน
