"""
BabelMeow control panel (Tkinter) — full app: Play (overlay), Build (extract→
import→filter→translate→upgrade), and Export, all without touching the CLI.

Tabs:
  Play   : pick game/lang, Start/Stop the overlay bridge (+Ollama), live status
  Build  : import an engine export → filter → translate (with progress) → upgrade
  Export : dump cache to JSON/CSV/PO/keyvalue (for moddable games)
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from babelmeow.config import GAMES_DIR, GameConfig  # noqa: E402

BRIDGE_PORT = 11434
OLLAMA_PORT = 11435
PYTHON = sys.executable
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_PROGRESS_RE = re.compile(r"\[\s*([\d,]+)\s*/\s*([\d,]+)\]")


def find_ollama() -> str:
    for c in (Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Ollama/ollama.exe",
              Path("C:/Program Files/Ollama/ollama.exe")):
        if c.exists():
            return str(c)
    return "ollama"


def list_games() -> list[str]:
    if not GAMES_DIR.exists():
        return ["diablo4"]
    return sorted(d.name for d in GAMES_DIR.iterdir()
                  if d.is_dir() and (d / "config.yaml").exists())


def list_langs(game: str) -> list[str]:
    langs = set()
    root = GAMES_DIR / game
    if root.exists():
        for p in root.glob("cache.*.db"):
            parts = p.name.split(".")
            if len(parts) == 3:
                langs.add(parts[1])
    lp = PROJECT_ROOT / "babelmeow" / "langpacks"
    if lp.exists():
        langs.update(p.stem for p in lp.glob("*.yaml"))
    try:
        langs.add(GameConfig.load(game).target_lang)
    except Exception:
        pass
    return sorted(langs) or ["th"]


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.ollama_proc: subprocess.Popen | None = None
        self.bridge_proc: subprocess.Popen | None = None
        self.task_proc: subprocess.Popen | None = None   # build pipeline task
        self.busy = False
        root.title("BabelMeow")
        root.geometry("560x640")
        root.minsize(540, 600)

        tk.Label(root, text="🐱 BabelMeow", font=("Segoe UI", 16, "bold"),
                 fg="#1F4E79").pack(pady=(8, 0))

        # shared game/lang selectors (top, above tabs)
        top = ttk.Frame(root); top.pack(fill="x", padx=10, pady=6)
        ttk.Label(top, text="Game:").grid(row=0, column=0, sticky="w")
        self.game_var = tk.StringVar()
        self.game_cb = ttk.Combobox(top, textvariable=self.game_var, state="readonly", width=18)
        self.game_cb.grid(row=0, column=1, padx=6)
        self.game_cb.bind("<<ComboboxSelected>>", lambda e: self._on_game_change())
        tk.Button(top, text="➕", width=2, command=self._add_game).grid(row=0, column=2)
        tk.Button(top, text="⟳", width=2, command=self._refresh_games).grid(row=0, column=3, padx=(2, 12))
        ttk.Label(top, text="Language:").grid(row=0, column=4, sticky="w")
        self.lang_var = tk.StringVar()
        self.lang_cb = ttk.Combobox(top, textvariable=self.lang_var, state="readonly", width=8)
        self.lang_cb.grid(row=0, column=5, padx=6)

        nb = ttk.Notebook(root); nb.pack(fill="both", expand=True, padx=10, pady=4)
        self._build_play_tab(nb)
        self._build_build_tab(nb)
        self._build_export_tab(nb)

        # shared log
        logf = ttk.LabelFrame(root, text="Log"); logf.pack(fill="both", expand=True, padx=10, pady=6)
        self.log = tk.Text(logf, height=7, wrap="word", font=("Consolas", 8))
        self.log.pack(fill="both", expand=True, padx=4, pady=4)

        root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._refresh_games()
        self._log("Ready.")
        self._poll()

    # ───────── tabs ─────────
    def _build_play_tab(self, nb):
        t = ttk.Frame(nb); nb.add(t, text="▶ Play (Overlay)")
        self.live_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(t, text="Live fallback (translate new text on the fly via Ollama)",
                        variable=self.live_var).pack(anchor="w", padx=8, pady=6)
        tk.Label(t, text="RST reads the screen → bridge translates → draws over the game. "
                         "Works with any game incl. D4.", fg="#555", wraplength=500,
                 justify="left", font=("Segoe UI", 8)).pack(anchor="w", padx=8)

        # Custom dictionary file (bring a translation file from elsewhere)
        df = ttk.LabelFrame(t, text="Dictionary file (optional)")
        df.pack(fill="x", padx=8, pady=6)
        self.dict_path = tk.StringVar()
        ttk.Entry(df, textvariable=self.dict_path, width=40).grid(row=0, column=0, padx=6, pady=6)
        tk.Button(df, text="Browse", command=self._browse_dict).grid(row=0, column=1)
        tk.Button(df, text="Clear", command=lambda: self.dict_path.set("")).grid(row=0, column=2, padx=4)
        tk.Label(df, text="Blank = built-in for this game/language. "
                          ".db used directly; .json/.csv/.po imported first.",
                 fg="#777", wraplength=480, justify="left", font=("Segoe UI", 8)).grid(
            row=1, column=0, columnspan=3, sticky="w", padx=6, pady=(0, 4))

        st = ttk.LabelFrame(t, text="Status"); st.pack(fill="x", padx=8, pady=8)
        self.lbl_ollama = tk.Label(st, text="Ollama:  ○", anchor="w"); self.lbl_ollama.pack(fill="x", padx=8)
        self.lbl_bridge = tk.Label(st, text="Bridge:  ○", anchor="w"); self.lbl_bridge.pack(fill="x", padx=8)
        self.lbl_cache = tk.Label(st, text="Cache:   —", anchor="w"); self.lbl_cache.pack(fill="x", padx=8)
        self.lbl_stats = tk.Label(st, text="Stats:   —", anchor="w"); self.lbl_stats.pack(fill="x", padx=8, pady=(0, 4))

        b = tk.Frame(t); b.pack(pady=8)
        self.btn_start = tk.Button(b, text="▶  Start", width=14, bg="#2E7D32", fg="white",
                                   font=("Segoe UI", 10, "bold"), command=self.start)
        self.btn_start.pack(side="left", padx=6)
        self.btn_stop = tk.Button(b, text="⏹  Stop", width=14, bg="#B71C1C", fg="white",
                                  font=("Segoe UI", 10, "bold"), command=self.stop, state="disabled")
        self.btn_stop.pack(side="left", padx=6)
        bl = tk.Frame(t); bl.pack()
        tk.Button(bl, text="Open stats", command=self._open_stats).pack(side="left", padx=4)
        tk.Button(bl, text="Project folder", command=lambda: os.startfile(str(PROJECT_ROOT))).pack(side="left", padx=4)

    def _build_build_tab(self, nb):
        t = ttk.Frame(nb); nb.add(t, text="🔧 Build")
        tk.Label(t, text="Prepare a game's translations (offline). Run top→bottom.",
                 fg="#555", font=("Segoe UI", 8)).pack(anchor="w", padx=8, pady=(6, 2))

        # 1. Import
        f1 = ttk.LabelFrame(t, text="1 · Import (engine export → translations.json)")
        f1.pack(fill="x", padx=8, pady=4)
        self.import_path = tk.StringVar()
        ttk.Entry(f1, textvariable=self.import_path, width=42).grid(row=0, column=0, padx=6, pady=6)
        tk.Button(f1, text="Browse", command=self._browse_import).grid(row=0, column=1)
        tk.Button(f1, text="Import", width=8, command=self._do_import).grid(row=0, column=2, padx=6)

        # 2. Filter
        f2 = ttk.LabelFrame(t, text="2 · Filter (dedup + drop junk)")
        f2.pack(fill="x", padx=8, pady=4)
        tk.Button(f2, text="Filter", width=10, command=self._do_filter).pack(side="left", padx=6, pady=6)

        # 3. Translate
        f3 = ttk.LabelFrame(t, text="3 · Translate (batch, local Ollama)")
        f3.pack(fill="x", padx=8, pady=4)
        ttk.Label(f3, text="Model:").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.model_var = tk.StringVar()
        ttk.Entry(f3, textvariable=self.model_var, width=34).grid(row=0, column=1, columnspan=2, sticky="w")
        ttk.Label(f3, text="Workers:").grid(row=1, column=0, sticky="w", padx=6)
        self.workers_var = tk.StringVar(value="5")
        ttk.Spinbox(f3, from_=1, to=8, textvariable=self.workers_var, width=4).grid(row=1, column=1, sticky="w")
        ttk.Label(f3, text="Limit (blank=all):").grid(row=2, column=0, sticky="w", padx=6)
        self.limit_var = tk.StringVar()
        ttk.Entry(f3, textvariable=self.limit_var, width=8).grid(row=2, column=1, sticky="w")
        self.btn_translate = tk.Button(f3, text="Translate", width=10, command=self._do_translate)
        self.btn_translate.grid(row=0, column=3, rowspan=2, padx=8)
        self.prog = ttk.Progressbar(f3, length=420, mode="determinate")
        self.prog.grid(row=3, column=0, columnspan=4, padx=6, pady=6)

        # 4. Upgrade
        f4 = ttk.LabelFrame(t, text="4 · Upgrade live (re-translate live-discovered with batch model)")
        f4.pack(fill="x", padx=8, pady=4)
        tk.Button(f4, text="Upgrade", width=10, command=self._do_upgrade).pack(side="left", padx=6, pady=6)

    def _build_export_tab(self, nb):
        t = ttk.Frame(nb); nb.add(t, text="📤 Export")
        tk.Label(t, text="Dump cache to a portable file, then inject with the engine's tool "
                         "(moddable Unity/Unreal). Not for D4 — use overlay.",
                 fg="#555", wraplength=500, justify="left", font=("Segoe UI", 8)).pack(anchor="w", padx=8, pady=6)
        f = ttk.Frame(t); f.pack(anchor="w", padx=8, pady=4)
        ttk.Label(f, text="Format:").grid(row=0, column=0, sticky="w")
        self.fmt_var = tk.StringVar(value="po")
        ttk.Combobox(f, textvariable=self.fmt_var, state="readonly", width=12,
                     values=["json", "csv", "po", "keyvalue"]).grid(row=0, column=1, padx=6)
        self.excl_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text="exclude needs-review", variable=self.excl_var).grid(row=0, column=2, padx=6)
        tk.Button(f, text="Export", width=10, command=self._do_export).grid(row=0, column=3, padx=6)

    # ───────── helpers ─────────
    def _log(self, msg):
        self.log.insert("end", msg + "\n"); self.log.see("end")

    def _on_game_change(self):
        self._refresh_langs()
        self._sync_model()

    def _refresh_games(self):
        games = list_games(); self.game_cb["values"] = games
        if self.game_var.get() not in games:
            self.game_var.set("diablo4" if "diablo4" in games else
                              next((g for g in games if not g.startswith("_")), games[0] if games else ""))
        self._refresh_langs(); self._sync_model()

    def _refresh_langs(self):
        langs = list_langs(self.game_var.get()); self.lang_cb["values"] = langs
        try:
            default = GameConfig.load(self.game_var.get()).target_lang
        except Exception:
            default = langs[0]
        if self.lang_var.get() not in langs:
            self.lang_var.set(default if default in langs else langs[0])

    def _sync_model(self):
        try:
            cfg = GameConfig.load(self.game_var.get(), lang=self.lang_var.get() or None)
            self.model_var.set(cfg.model_batch)
        except Exception:
            pass

    def _open_stats(self):
        import webbrowser; webbrowser.open(f"http://localhost:{BRIDGE_PORT}/stats")

    def _browse_import(self):
        p = filedialog.askopenfilename(title="Engine export file",
                                       filetypes=[("Data", "*.tsv *.csv *.json *.txt"), ("All", "*.*")])
        if p:
            self.import_path.set(p)

    def _browse_dict(self):
        p = filedialog.askopenfilename(title="Dictionary file",
                                       filetypes=[("Dictionary", "*.db *.json *.csv *.po *.txt"), ("All", "*.*")])
        if p:
            self.dict_path.set(p)

    def _resolve_dict(self) -> str | None:
        """Return a cache.db path to use, importing non-.db files first.
        None = use the default per-game/lang cache."""
        raw = self.dict_path.get().strip()
        if not raw:
            return None
        p = Path(raw)
        if not p.exists():
            self._log(f"[dict] not found: {p}"); return None
        if p.suffix.lower() == ".db":
            return str(p)
        # import json/csv/po/keyvalue -> a sibling .db, then use it
        out = p.with_suffix(".imported.db")
        self._log(f"[dict] importing {p.name} -> {out.name} ...")
        r = subprocess.run([PYTHON, "scripts/import_dict.py", "--input", str(p), "-o", str(out)],
                           cwd=str(PROJECT_ROOT), capture_output=True, text=True,
                           encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                           creationflags=NO_WINDOW)
        last = (r.stdout or r.stderr or "").strip().splitlines()
        self._log("  " + (last[-1] if last else "import done"))
        return str(out) if out.exists() else None

    # ───────── background task runner ─────────
    def _run_bg(self, cmd, label, on_line=None, on_done=None):
        if self.busy:
            messagebox.showinfo("Busy", "A task is already running."); return
        self.busy = True
        self._log(f"$ {label}")

        def worker():
            try:
                self.task_proc = subprocess.Popen(
                    [PYTHON, *cmd], cwd=str(PROJECT_ROOT), stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                    env={**os.environ, "PYTHONIOENCODING": "utf-8"}, creationflags=NO_WINDOW)
                for line in self.task_proc.stdout:
                    line = line.rstrip()
                    if line:
                        if on_line:
                            self.root.after(0, on_line, line)
                        else:
                            self.root.after(0, self._log, "  " + line[:160])
                self.task_proc.wait()
            except Exception as e:
                self.root.after(0, self._log, f"[error] {e}")
            finally:
                self.busy = False
                self.task_proc = None
                if on_done:
                    self.root.after(0, on_done)

        threading.Thread(target=worker, daemon=True).start()

    def _do_import(self):
        path = self.import_path.get().strip()
        if not path:
            messagebox.showerror("Import", "Pick an export file first."); return
        self._run_bg(["scripts/import_strings.py", "--game", self.game_var.get(), "--input", path],
                     "import_strings")

    def _do_filter(self):
        self._run_bg(["scripts/filter_strings.py", "--game", self.game_var.get()], "filter_strings")

    def _do_translate(self):
        cmd = ["scripts/translate_batch.py", "--game", self.game_var.get(),
               "--lang", self.lang_var.get(), "--workers", self.workers_var.get(),
               "--host", f"http://127.0.0.1:{OLLAMA_PORT}", "--report-every", "20"]
        if self.model_var.get().strip():
            cmd += ["--model", self.model_var.get().strip()]
        if self.limit_var.get().strip().isdigit():
            cmd += ["--limit", self.limit_var.get().strip()]
        self.prog["value"] = 0
        self.btn_translate["state"] = "disabled"
        # ensure Ollama up for batch
        if not self._port_up(OLLAMA_PORT):
            self._start_ollama_only()
        self._run_bg(cmd, "translate_batch", on_line=self._on_translate_line,
                     on_done=lambda: self.btn_translate.config(state="normal"))

    def _on_translate_line(self, line):
        m = _PROGRESS_RE.search(line)
        if m:
            done = int(m.group(1).replace(",", "")); total = int(m.group(2).replace(",", ""))
            if total:
                self.prog["maximum"] = total; self.prog["value"] = done
        self._log("  " + line[:160])

    def _do_upgrade(self):
        if not self._port_up(OLLAMA_PORT):
            self._start_ollama_only()
        self._run_bg(["scripts/upgrade_live.py", "--game", self.game_var.get(),
                      "--lang", self.lang_var.get(), "--host", f"http://127.0.0.1:{OLLAMA_PORT}"],
                     "upgrade_live")

    def _do_export(self):
        cmd = ["scripts/export_translations.py", "--game", self.game_var.get(),
               "--lang", self.lang_var.get(), "--format", self.fmt_var.get()]
        if self.excl_var.get():
            cmd.append("--exclude-review")
        self._run_bg(cmd, "export_translations")

    # ───────── add game ─────────
    def _add_game(self):
        dlg = tk.Toplevel(self.root); dlg.title("Add game"); dlg.geometry("340x250")
        dlg.resizable(False, False); dlg.transient(self.root)
        rows = [("Game id (folder name)", "name", ""), ("Engine (unity/unreal/casc)", "engine", "unity"),
                ("Source language", "source_lang", "en"), ("Target language", "target_lang", "th")]
        fields = {}
        for i, (label, key, dflt) in enumerate(rows):
            ttk.Label(dlg, text=label).grid(row=i, column=0, sticky="w", padx=10, pady=6)
            v = tk.StringVar(value=dflt); ttk.Entry(dlg, textvariable=v, width=20).grid(row=i, column=1, padx=10)
            fields[key] = v

        def create():
            name = fields["name"].get().strip()
            if not name:
                messagebox.showerror("Add game", "Game id is required."); return
            root = GAMES_DIR / name
            if (root / "config.yaml").exists():
                messagebox.showerror("Add game", f"'{name}' already exists."); return
            root.mkdir(parents=True, exist_ok=True)
            (root / "config.yaml").write_text(
                f"game: {name}\nengine: {fields['engine'].get().strip() or 'unknown'}\n"
                f"source_lang: {fields['source_lang'].get().strip() or 'en'}\n"
                f"target_lang: {fields['target_lang'].get().strip() or 'th'}\n"
                "model_batch: scb10x/llama3.1-typhoon2-8b-instruct\n"
                "model_live: scb10x/typhoon-translate1.5-4b\n"
                "importer:\n  format: csv\n  columns:\n    source: text\n    filename: file\n    key: id\n"
                "category_patterns:\n  - [quest, quest]\n  - [item, item]\n  - [skill, skill]\n"
                "  - [ui, ui]\n  - [dialog, npc_dialog]\n"
                "dropped_files: []\n"
                "priority_categories: [item, quest, skill, npc_dialog, ui, lore, other]\n",
                encoding="utf-8")
            self._log(f"Created game '{name}'. Go to Build tab → Import your export file.")
            self.game_var.set(name); self._refresh_games(); dlg.destroy()

        tk.Button(dlg, text="Create", width=12, command=create).grid(row=len(rows), column=0, columnspan=2, pady=12)

    # ───────── play start/stop ─────────
    def start(self):
        game, lang, live = self.game_var.get(), self.lang_var.get(), self.live_var.get()
        self._log(f"Start overlay: {game}/{lang} live={'on' if live else 'off'}")
        self.btn_start["state"] = "disabled"

        custom_db = self._resolve_dict()
        if custom_db:
            self._log(f"Using dictionary: {Path(custom_db).name}")

        def worker():
            try:
                if live and not self._port_up(OLLAMA_PORT):
                    self._start_ollama_only()
                env = {**os.environ, "PYTHONIOENCODING": "utf-8", "BABELMEOW_GAME": game,
                       "BABELMEOW_LANG": lang, "BABELMEOW_PORT": str(BRIDGE_PORT),
                       "BABELMEOW_LIVE": "1" if live else "0",
                       "BABELMEOW_REAL_OLLAMA": f"http://127.0.0.1:{OLLAMA_PORT}"}
                if custom_db:
                    env["BABELMEOW_CACHE"] = custom_db
                self.bridge_proc = subprocess.Popen(
                    [PYTHON, "-m", "babelmeow.overlay_bridge.server"], cwd=str(PROJECT_ROOT),
                    env=env, creationflags=NO_WINDOW)
                self.root.after(0, lambda: self._log(f"Bridge on :{BRIDGE_PORT} (model babelmeow-{lang})"))
                self.root.after(0, lambda: self.btn_stop.config(state="normal"))
            except Exception as e:
                self.root.after(0, lambda: self._log(f"[error] {e}"))
                self.root.after(0, lambda: self.btn_start.config(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    def _start_ollama_only(self):
        env = {**os.environ, "OLLAMA_VULKAN": "1", "OLLAMA_NUM_PARALLEL": "4",
               "OLLAMA_KEEP_ALIVE": "30m", "OLLAMA_HOST": f"127.0.0.1:{OLLAMA_PORT}"}
        self.ollama_proc = subprocess.Popen([find_ollama(), "serve"], env=env, creationflags=NO_WINDOW)
        self.root.after(0, lambda: self._log(f"Ollama serve on :{OLLAMA_PORT}"))
        import time; time.sleep(5)

    def stop(self):
        for name, proc in (("bridge", self.bridge_proc), ("ollama", self.ollama_proc)):
            if proc and proc.poll() is None:
                proc.terminate(); self._log(f"Stopped {name}.")
        self.bridge_proc = self.ollama_proc = None
        self.btn_stop["state"] = "disabled"; self.btn_start["state"] = "normal"

    # ───────── status poll ─────────
    @staticmethod
    def _port_up(port):
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2); return s.connect_ex(("127.0.0.1", port)) == 0

    def _poll(self):
        def work():
            ol, br = self._port_up(OLLAMA_PORT), self._port_up(BRIDGE_PORT)
            cache, stats = "—", "—"
            if br:
                try:
                    cache = f"{requests.get(f'http://localhost:{BRIDGE_PORT}/', timeout=0.5).json().get('cache_size',0):,} entries"
                    s = requests.get(f"http://localhost:{BRIDGE_PORT}/stats", timeout=0.5).json()
                    stats = f"hit {s.get('hit_rate_pct',0)}% · live {s.get('live',0)}"
                except Exception:
                    pass
            self.root.after(0, self._update_status, ol, br, cache, stats)
        threading.Thread(target=work, daemon=True).start()
        self.root.after(2500, self._poll)

    def _update_status(self, ol, br, cache, stats):
        self.lbl_ollama.config(text=f"Ollama:  {'● running' if ol else '○ stopped'}", fg="#2E7D32" if ol else "#888")
        self.lbl_bridge.config(text=f"Bridge:  {'● ' + str(BRIDGE_PORT) if br else '○ stopped'}", fg="#2E7D32" if br else "#888")
        self.lbl_cache.config(text=f"Cache:   {cache}")
        self.lbl_stats.config(text=f"Stats:   {stats}")

    def _on_close(self):
        if self.task_proc and self.task_proc.poll() is None:
            self.task_proc.terminate()
        self.stop(); self.root.destroy()


def main():
    root = tk.Tk(); App(root); root.mainloop()


if __name__ == "__main__":
    main()
