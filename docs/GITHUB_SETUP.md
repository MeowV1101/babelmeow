# 🐙 GitHub Setup Guide — สอนสร้าง repo ทีละขั้น

> สำหรับมือใหม่ ทำตามได้เลย

## 📋 สิ่งที่ต้องเตรียม

1. **บัญชี GitHub** — ถ้ายังไม่มี ไปสมัครที่ [github.com/signup](https://github.com/signup) (ฟรี)
2. **Git** — โปรแกรมจัดการ version
3. **GitHub CLI (gh)** — เครื่องมือ command line ที่ทำให้ทุกอย่างง่ายขึ้น (optional แต่แนะนำ)

---

## Step 1️⃣ — ติดตั้ง Git

### Windows
ดาวน์โหลด installer: https://git-scm.com/download/win

ระหว่างติดตั้ง:
- ✅ "Git from the command line and also from 3rd-party software"
- ✅ "Use Visual Studio Code as Git's default editor" (ถ้ามี VS Code)
- ✅ "Override the default branch name for new repositories" → ใส่ `main`
- ✅ "Use Windows' default console window"
- ✅ ตัวเลือกอื่นๆ ใช้ค่า default ได้

ทดสอบ:
```powershell
git --version
# ควรขึ้น: git version 2.xx.x
```

---

## Step 2️⃣ — ตั้งค่า Git (ทำครั้งเดียวต่อเครื่อง)

เปิด PowerShell หรือ Terminal:

```powershell
# ใส่ชื่อ-อีเมลให้ตรงกับบัญชี GitHub
git config --global user.name "ชื่อของคุณ"
git config --global user.email "lnwzapetch@gmail.com"

# ตั้ง default branch เป็น main
git config --global init.defaultBranch main

# (Windows) แก้ปัญหา line endings
git config --global core.autocrlf true
```

---

## Step 3️⃣ — ติดตั้ง GitHub CLI (แนะนำ)

ทำให้สร้าง repo + push ได้ใน command เดียว

### Windows
ดาวน์โหลด: https://cli.github.com/

หรือผ่าน winget:
```powershell
winget install --id GitHub.cli
```

ทดสอบ:
```powershell
gh --version
```

### Login เข้า GitHub
```powershell
gh auth login
```

จะถาม:
1. **Where do you use GitHub?** → `GitHub.com`
2. **What is your preferred protocol?** → `HTTPS`
3. **Authenticate Git with your GitHub credentials?** → `Yes`
4. **How would you like to authenticate?** → `Login with a web browser`

จะมีโค้ด one-time code ขึ้น เช่น `XXXX-XXXX` แล้วเปิดเบราว์เซอร์ให้เอาไปใส่

---

## Step 4️⃣ — สร้าง Repository (วิธีที่ 1: ใช้ gh CLI)

### A. Init git ใน folder ของเรา

```powershell
cd D:\claude\BabelMeow
git init
git add .
git commit -m "Initial commit: project plan and structure"
```

### B. สร้าง repo บน GitHub + push ในคำสั่งเดียว

```powershell
gh repo create babelmeow --public --source=. --remote=origin --push
```

อธิบาย:
- `babelmeow` — ชื่อ repo
- `--public` — เปิดสาธารณะ (ใช้ `--private` ถ้าอยากเก็บส่วนตัวก่อน)
- `--source=.` — ใช้ folder ปัจจุบัน
- `--remote=origin` — ตั้งชื่อ remote เป็น origin
- `--push` — push code ขึ้นทันทีหลังสร้าง repo

เสร็จแล้ว! เปิด browser: https://github.com/YOUR_USERNAME/babelmeow

---

## Step 4️⃣ (ทางเลือก) — สร้าง Repository (วิธีที่ 2: ผ่านเว็บ)

ถ้าไม่อยากใช้ gh CLI:

### A. สร้าง repo ผ่านเว็บ

1. ไปที่ https://github.com/new
2. **Repository name:** `babelmeow`
3. **Description:** `Universal game translation overlay — Thai-first`
4. **Public** หรือ **Private** เลือกได้
5. ❌ **อย่าติ๊ก** "Initialize this repository with README" (เพราะเรามีไฟล์อยู่แล้ว)
6. กด **Create repository**

### B. Push code จากเครื่องขึ้น

GitHub จะแสดงคำสั่ง copy-paste:

```powershell
cd D:\claude\BabelMeow
git init
git add .
git commit -m "Initial commit: project plan and structure"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/babelmeow.git
git push -u origin main
```

ครั้งแรก push จะถาม login → เปิด browser ให้ authorize

---

## Step 5️⃣ — Workflow ปกติ (อัพเดทโค้ดต่อ)

ทุกครั้งที่แก้ไฟล์เสร็จแล้วอยาก save ขึ้น GitHub:

```powershell
cd D:\claude\BabelMeow

# ดูว่าแก้อะไรบ้าง
git status

# เพิ่มไฟล์ที่แก้
git add .                          # ทั้งหมด
git add path/to/file.py            # เฉพาะไฟล์

# Commit (message ควรบอกว่าทำอะไร)
git commit -m "Add extractor for Diablo IV"

# Push ขึ้น GitHub
git push
```

---

## 🌿 Branch Workflow (เมื่อโปรเจกต์โตขึ้น)

แทนที่จะ commit ลง `main` ตรงๆ → สร้าง branch แยกสำหรับแต่ละ feature

```powershell
# สร้าง branch ใหม่
git checkout -b feature/diablo4-extractor

# ทำงาน, commit ปกติ
git add .
git commit -m "Implement CASC extraction"

# Push branch ขึ้น GitHub
git push -u origin feature/diablo4-extractor

# กลับมา branch main
git checkout main

# Merge branch กลับเข้า main (หลัง review)
git merge feature/diablo4-extractor
git push
```

หรือใน GitHub web UI สร้าง **Pull Request** จาก branch → main เพื่อ review ก่อน merge

---

## 🔐 Best Practices

### ✅ Do
- Commit บ่อยๆ ทุกครั้งที่เสร็จ feature ย่อย
- เขียน commit message ที่บอกว่าทำอะไร
- ใช้ branch สำหรับ feature ใหญ่ๆ
- เขียน README ให้ดี
- ใส่ .gitignore ก่อน commit ครั้งแรก (เราทำแล้ว ✅)

### ❌ Don't
- Commit secrets (API keys, passwords) — ใส่ `.env` ใน .gitignore
- Commit ไฟล์ใหญ่ (>50MB) — ใส่ Git LFS หรือ exclude
- Commit data/cache.db ที่เปลี่ยนบ่อย
- `git push --force` ไป main (อันตรายมาก)

---

## 🆘 ปัญหาที่เจอบ่อย

### Q: "fatal: not a git repository"
A: ยังไม่ได้ `git init` ใน folder นั้น

### Q: "Permission denied (publickey)"
A: ใช้ HTTPS แทน SSH หรือ login ใหม่ด้วย `gh auth login`

### Q: Push แล้วขึ้น "rejected"
A: มีคน push ก่อนเรา → `git pull --rebase` แล้ว push ใหม่

### Q: เผลอ commit ไฟล์ใหญ่/secret ไปแล้ว
A: ใช้ [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/) หรือถามผม

### Q: อยากย้อน commit
A: `git reset --soft HEAD~1` (keep changes) หรือ `git reset --hard HEAD~1` (ลบ changes — อันตราย)

---

## 🎓 เรียนเพิ่มเติม

- [Pro Git Book](https://git-scm.com/book/en/v2) (ฟรี)
- [GitHub Skills](https://skills.github.com/) — interactive tutorials
- [Oh My Git!](https://ohmygit.org/) — เกมสอน git

---

## 📌 Cheatsheet สั้นๆ

```powershell
git status                  # ดูว่ามีอะไรแก้
git add .                   # stage ทุกไฟล์ที่แก้
git commit -m "message"     # commit ที่เครื่อง
git push                    # push ขึ้น GitHub
git pull                    # ดึงของใหม่จาก GitHub
git log --oneline           # ดูประวัติ commit
git diff                    # ดู diff ที่ยังไม่ commit
```

---

🐱 **เสร็จแล้ว!** ตอนนี้ BabelMeow ของคุณอยู่บน GitHub แล้ว
