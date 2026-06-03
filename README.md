# 🐱 BabelMeow

[![CI](https://github.com/MeowV1101/babelmeow/actions/workflows/ci.yml/badge.svg)](https://github.com/MeowV1101/babelmeow/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

> Universal game translation overlay — Thai-first, open to all languages

BabelMeow แปลเกมที่ไม่รองรับภาษาไทย ให้คุณเล่นได้สบาย โดย **ไม่แตะไฟล์เกม** = ไม่เสี่ยงโดน ban

## ✨ Features (planned)

- 🎮 รองรับหลายเกม (เริ่มจาก **Diablo IV**)
- 🇹🇭 แปล EN → TH คุณภาพสูง ด้วย local LLM
- 🔒 ปลอดภัย — overlay only, ไม่แตะไฟล์เกม
- 💸 ฟรี 100% — ใช้ local AI ไม่มี API cost
- 🔌 ใช้ Translumo / RSTGameTranslation เป็น overlay engine
- 📦 Pre-translated dictionary — runtime ใช้ VRAM = 0

## 🏗 How it works

```
Offline (one-time per game):
  Game files → Extract strings → Translate (Typhoon 2) → SQLite

Runtime (while playing):
  Screen → OCR → Dictionary lookup → Overlay
```

## 🚀 Quick Start

> 🚧 **Work in progress** — ดู [PLAN.md](docs/PLAN.md) สำหรับสถานะปัจจุบัน

## 🎯 Supported Games

| Game | Engine | Status |
|---|---|---|
| Diablo IV | Blizzard CASC | 🚧 In progress |
| _Coming soon..._ | | |

## 📚 Documentation

- 📖 **[Journey / Learning Guide](docs/JOURNEY.md)** — เล่าทุกขั้นตอน + สิ่งที่ลองแล้วไม่เวิร์ก (สำหรับมือใหม่) ⭐
- [Play Guide](docs/PLAY_GUIDE.md) — วิธีเริ่มเล่น + จูน + แก้ปัญหา
- [Export Guide](docs/EXPORT.md) — ส่งออกคำแปลเป็น JSON/CSV/PO (multi-game/multi-language)
- [Project Plan](docs/PLAN.md) — สถาปัตยกรรม, phases, timeline
- [GPU Vulkan Fix](docs/GPU_VULKAN_FIX.md) — แก้ AMD RDNA4 รันบน CPU
- [RST Setup](docs/RST_SETUP.md) — ตั้งค่า RSTGameTranslation
- [Batch Operations](docs/BATCH_OPERATIONS.md) — จัดการ batch translate
- [GitHub Setup Guide](docs/GITHUB_SETUP.md) — สอนสร้าง repo

## 🤝 Contributing

ยินดีต้อนรับ contributor! ดู [PLAN.md](docs/PLAN.md) ก่อนเพื่อเข้าใจ architecture

## 📜 License

MIT (planned)

---

*Made with 🐾 by กรอบ (Thai-first, world-friendly)*
