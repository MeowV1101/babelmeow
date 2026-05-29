# 🎮 GPU Acceleration Fix — AMD RX 9070 XT (RDNA4)

> ⚠️ สำคัญมาก: ถ้าไม่ทำ Ollama จะรันบน **CPU** ช้ากว่า GPU ~5 เท่า

## 🔴 อาการ

`ollama ps` แสดง:
```
NAME                          SIZE     PROCESSOR
typhoon2-8b                   5.7 GB   100% CPU     ← ผิด! ควรเป็น GPU
```

Batch translate rate แค่ ~0.30/s (ควรได้เร็วกว่ามาก)

## 🔍 สาเหตุ

**RX 9070 XT = RDNA4 (gfx1201)** ใหม่เกินไป — Ollama 0.24.0:
- ROCm 6.4 ที่ติดมายังไม่ support gfx1201 เต็มที่
- GPU auto-detect เลย fall back ไป CPU เงียบๆ

แต่ Ollama **มี Vulkan backend ติดมาแล้ว** (`lib\ollama\vulkan\ggml-vulkan.dll`)
แค่ต้องเปิดด้วย env var

## ✅ วิธีแก้

### ตั้ง environment variable (ครั้งเดียว ถาวร)

```powershell
[Environment]::SetEnvironmentVariable("OLLAMA_VULKAN", "1", "User")
[Environment]::SetEnvironmentVariable("OLLAMA_NUM_PARALLEL", "4", "User")
[Environment]::SetEnvironmentVariable("OLLAMA_KEEP_ALIVE", "30m", "User")
```

### Restart Ollama ให้สะอาด (สำคัญ — ต้อง free port ก่อน)

```powershell
# Kill ทุก ollama process
Get-Process -Name ollama -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 4

# Start ใหม่ (env vars จะถูก inherit)
$env:OLLAMA_VULKAN="1"; $env:OLLAMA_NUM_PARALLEL="4"; $env:OLLAMA_KEEP_ALIVE="30m"
Start-Process "C:\Users\lnwza\AppData\Local\Programs\Ollama\ollama.exe" -ArgumentList "serve" -WindowStyle Hidden
```

หรือ double-click: **`scripts\start_ollama_gpu.bat`**

### ยืนยันว่าใช้ GPU

```powershell
ollama ps
```
ต้องเห็น **`100% GPU`** ใน PROCESSOR column

ตรวจ debug log:
```
library=Vulkan  name="AMD Radeon RX 9070 XT"  total="15.9 GiB"  ← GPU detected!
PROCESSOR: 100% GPU
```

## 🧮 VRAM Management (RX 9070 XT = 16 GB)

| Component | VRAM |
|---|---|
| Desktop / Chrome / อื่นๆ | ~3.4 GB |
| Model (Typhoon 8B Q4) | ~5-6 GB |
| KV cache (num_ctx=3072 × 4 slots) | ~2 GB |
| Compute buffers | ~1 GB |
| **รวม** | **~11-12 GB** |
| **เหลือ** | **~4-5 GB** ✅ |

### คุม VRAM ไม่ให้เกิน

1. **`num_ctx=3072`** ใน translator (ตั้งแล้วใน `ollama.py`)
   - พอสำหรับ system prompt 1500 + input + output
   - ยิ่งเล็ก ยิ่งประหยัด KV cache
2. **`NUM_PARALLEL=4`** — ถ้า VRAM เกิน ลดเป็น 2-3
3. เช็ค spill: ถ้า `Shared Usage` (RAM spill) สูง = VRAM เต็ม → ลด parallel/ctx

### เช็ค VRAM realtime
```powershell
(Get-Counter "\GPU Adapter Memory(*)\Dedicated Usage").CounterSamples |
  Where-Object { $_.CookedValue -gt 200MB } |
  ForEach-Object { "{0:N0} MB" -f ($_.CookedValue/1MB) }
```

## ⚖️ Tuning Trade-offs

| NUM_PARALLEL | Throughput | VRAM | เสี่ยงเกิน? |
|---|---|---|---|
| 2 | ปานกลาง | ~9 GB | ปลอดภัยมาก |
| **4 (ปัจจุบัน)** | **ดี** | **~12 GB** | ปลอดภัย |
| 6 | ดีสุด | ~15 GB | เสี่ยง — ระวัง spill |
| 8 | อาจช้าลง | >16 GB | เกิน! spill to RAM |

> Sweet spot = 4. ถ้าอยากดันเป็น 6 ต้องลด num_ctx เป็น 2048

## 🔄 หลัง Reboot

User-scope env var `OLLAMA_VULKAN=1` จะติดถาวร — Ollama ที่ auto-start (tray app) ควรใช้ Vulkan เอง

แต่ถ้า `ollama ps` กลับไปเป็น CPU → รัน `scripts\start_ollama_gpu.bat` อีกครั้ง
