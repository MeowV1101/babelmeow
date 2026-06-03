# 📤 Export Translations

ดึงคำแปลออกจาก cache เป็นไฟล์ทั่วไป — เอาไปใช้ต่อ/แก้/แชร์/ทำ mod เกม moddable

## การใช้งาน

```powershell
python scripts/export_translations.py --game diablo4 --lang th --format po
python scripts/export_translations.py --game diablo4 --lang zh --format csv -o out.csv
python scripts/export_translations.py --game diablo4 --lang th --format json --exclude-review
```

| flag | ความหมาย |
|---|---|
| `--game` | เกม (โฟลเดอร์ใน games/) |
| `--lang` | ภาษาเป้าหมาย (default: game config) → อ่าน `cache.<lang>.db` |
| `--format` | `json` / `csv` / `po` / `keyvalue` |
| `-o` | path output (default: `games/<game>/export_<lang>.<ext>`) |
| `--exclude-review` | ข้ามคำที่ flag `needs_review` (เอาเฉพาะที่มั่นใจ) |

## รูปแบบไฟล์

### json
```json
[ { "source": "Lilith", "target": "ลิลิธ", "category": "characters", "needs_review": false } ]
```
เหมาะ: เขียนโปรแกรมต่อ, แปลงเป็น format อื่น

### csv (UTF-8 BOM — เปิด Excel ได้เลย)
```
source,target,category,needs_review
Lilith,ลิลิธ,characters,0
```
เหมาะ: review/แก้ใน Excel/Google Sheets

### po (gettext — มาตรฐานแปลแอป/เกม)
```
#. category: characters
msgid "Lilith"
msgstr "ลิลิธ"
```
เหมาะ: เครื่องมือแปลมืออาชีพ (Poedit, Weblate, Crowdin), เกมที่ใช้ gettext

### keyvalue
```
Lilith = ลิลิธ
```
เหมาะ: อ่านง่าย, import เข้าระบบ key-value ง่ายๆ

## เอาไปทำ mod เกมอื่นยังไง

> ⚠️ **ไม่ใช่สำหรับ Diablo IV** (CASC + anti-cheat + ฟอนต์ → ใช้ overlay เท่านั้น)
> ใช้กับเกม **moddable** (Unity/Unreal single-player) ที่แก้ไฟล์ได้

ขั้นตอนทั่วไป:
1. export เป็น format ที่ engine นั้นรับ (มักเป็น `po` หรือ `json`)
2. ใช้ tool ของ engine ใส่กลับ:
   - **Unity**: แก้ผ่าน AssetStudio/UABEA → repack TextAsset/locale
   - **Unreal**: import `.po` → `.locres` ผ่าน UnrealLocres / editor
   - **เกมที่อ่าน json/csv ภายนอก**: วางไฟล์แทนของเดิมตรงๆ
3. ใส่ฟอนต์ที่รองรับภาษาเป้าหมายถ้าเกมไม่มี

> BabelMeow ไม่ bundle tool ของ engine — export ให้ไฟล์ คุณใช้ tool ของเกมนั้น insert เอง

## ⚖️ หมายเหตุลิขสิทธิ์

คำแปล derive จากข้อความในเกม (IP ของผู้พัฒนา/ผู้จัดจำหน่าย)
- ใช้ส่วนตัว/community เล็กๆ มักไม่มีปัญหา
- **อย่าแจกไฟล์ export สาธารณะแบบขาย/ดังๆ** อาจโดน DMCA
- ไฟล์ export ถูก gitignore ไว้ (ไม่ขึ้น repo) ด้วยเหตุนี้

## หมายเหตุเทคนิค
- คอลัมน์ `source`/`target` = ภาษาต้นทาง/ปลายทาง (ในฐานข้อมูลเก็บชื่อ `en_text`/`th_text` ตามเดิม แต่หมายถึง source/target ทั่วไป)
- จำนวน entries = `cache stats` (เช็คด้วย `monitor_progress.py --game <g> --lang <l>`)
