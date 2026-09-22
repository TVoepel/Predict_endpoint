"""Moderne Oberfläche im iOS-Stil (CustomTkinter).

Abgerundete Karten auf gruppiertem Hintergrund, Pill-Buttons in System-Blau,
helles und dunkles Erscheinungsbild. Die Ablauflogik (Hintergrund-Thread,
Protokoll-Queue) entspricht der klassischen Oberfläche in ``gui_classic.py``.
"""

from __future__ import annotations

import queue
import subprocess
import sys
import threading
import traceback
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from . import __version__
from .core import Project
from .paths import (APP_NAME, bundled_coefficient_dir, default_project_dir,
                    load_config, logo_file, save_config)

# --------------------------------------------------------------------------
# Farben (hell, dunkel) – angelehnt an die iOS-Systemfarben
# --------------------------------------------------------------------------
BG = ("#F2F2F7", "#000000")            # gruppierter Hintergrund
CARD = ("#FFFFFF", "#1C1C1E")          # Karten
FIELD = ("#F2F2F7", "#2C2C2E")         # Eingabefelder, Textbereiche
SEPARATOR = ("#E5E5EA", "#38383A")
SEGMENT_BG = ("#E4E4E9", "#2C2C2E")     # Hintergrund der Segment-Controls
LABEL = ("#000000", "#FFFFFF")
LABEL_2 = ("#6E6E73", "#98989D")       # sekundärer Text
ACCENT = ("#007AFF", "#0A84FF")
ACCENT_HOVER = ("#0069DB", "#3B9BFF")
TINT = ("#E4F0FF", "#0F2A48")          # getönte Buttons (Blau, transparent-Look)
TINT_HOVER = ("#D2E6FF", "#153A63")
GREEN = ("#34C759", "#30D158")
ORANGE = ("#FF9500", "#FF9F0A")
RED = ("#FF3B30", "#FF453A")
ON_ACCENT = "#FFFFFF"

RADIUS_CARD = 20
RADIUS_CONTROL = 12
PAD = 20

APPEARANCE_VALUES = ["Hell", "Dunkel", "Auto"]
APPEARANCE_MAP = {"Hell": "light", "Dunkel": "dark", "Auto": "system"}


def _font(size: int, weight: str = "normal", mono: bool = False) -> ctk.CTkFont:
    if mono:
        family = "Menlo" if sys.platform == "darwin" else "Courier"
    else:
        family = ".AppleSystemUIFont" if sys.platform == "darwin" else None
    if family:
        return ctk.CTkFont(family=family, size=size, weight=weight)
    return ctk.CTkFont(size=size, weight=weight)


def open_path(path: Path, app: str | None = None) -> None:
    """Öffnet eine Datei oder einen Ordner mit dem Finder bzw. einer App."""
    path = Path(path)
    if sys.platform == "darwin":
        cmd = ["open"]
        if app:
            cmd += ["-a", app]
        cmd.append(str(path))
        subprocess.run(cmd, check=True)
    elif sys.platform.startswith("win"):
        import os

        os.startfile(str(path))  # type: ignore[attr-defined]
    else:
        subprocess.run(["xdg-open", str(path)], check=True)


def reveal_in_finder(path: Path) -> None:
    path = Path(path)
    if sys.platform == "darwin":
        subprocess.run(["open", "-R", str(path)], check=True)
    else:
        open_path(path.parent if path.is_file() else path)


class App(ctk.CTk):
    def __init__(self) -> None:
        config = load_config()
        appearance = config.get("appearance", "Auto")
        if appearance not in APPEARANCE_MAP:
            appearance = "Auto"
        ctk.set_appearance_mode(APPEARANCE_MAP[appearance])

        super().__init__(fg_color=BG)
        self.title(APP_NAME)
        self.geometry("900x900")
        self.minsize(760, 640)

        self._log_queue: "queue.Queue[tuple[str, object]]" = queue.Queue()
        self._busy = False
        self._new_project = lambda d: Project(d, fallback_coeff_dir=bundled_coefficient_dir())

        start_dir = config.get("project_dir") or str(default_project_dir())
        self.project = self._new_project(start_dir)
        self.project_var = tk.StringVar(value=str(self.project.base_dir))
        self.appearance_var = tk.StringVar(value=appearance)
        self.open_with_var = tk.StringVar(value=config.get("open_with", "Numbers"))

        self.fonts = {
            "title": _font(28, "bold"),
            "subtitle": _font(14),
            "section": _font(12, "bold"),
            "body": _font(14),
            "body_bold": _font(14, "bold"),
            "small": _font(12),
            "badge": _font(13, "bold"),
            "button": _font(14, "bold"),
            "mono": _font(12, mono=True),
        }

        self._build_menu()
        self._build_widgets()
        self._refresh_status()
        self.after(100, self._drain_log_queue)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ Menü

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)
        mod_label = "Cmd" if sys.platform == "darwin" else "Ctrl"

        if sys.platform == "darwin":
            app_menu = tk.Menu(menubar, name="apple", tearoff=0)
            app_menu.add_command(label=f"Über {APP_NAME}", command=self._show_about)
            menubar.add_cascade(menu=app_menu)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Projektordner wählen…", command=self._choose_project_dir,
                              accelerator=f"{mod_label}+O")
        file_menu.add_command(label="Messdateien hinzufügen…", command=self._add_input_files,
                              accelerator=f"{mod_label}+I")
        file_menu.add_separator()
        file_menu.add_command(label="Projektordner im Finder zeigen", command=self._open_project_dir)
        if sys.platform != "darwin":
            file_menu.add_separator()
            file_menu.add_command(label="Beenden", command=self._on_close)
        menubar.add_cascade(label="Ablage", menu=file_menu)

        run_menu = tk.Menu(menubar, tearoff=0)
        run_menu.add_command(label="Vorhersagen berechnen", command=self._run_predictions)
        run_menu.add_command(label="Sortierte CSV erzeugen", command=self._build_sorted_csv)
        run_menu.add_command(label="Zusammenfassung erste Zeilen erzeugen",
                             command=self._build_first_lines_csv)
        run_menu.add_separator()
        run_menu.add_command(label="Auswertung starten", command=self._run_all,
                             accelerator=f"{mod_label}+R")
        run_menu.add_separator()
        run_menu.add_command(label="Input-Ordner leeren…", command=self._clear_input)
        run_menu.add_command(label="Output-Ordner leeren…", command=self._clear_output)
        menubar.add_cascade(label="Auswertung", menu=run_menu)

        self.configure(menu=menubar)

        mod = "Command" if sys.platform == "darwin" else "Control"
        self.bind_all(f"<{mod}-o>", lambda e: self._choose_project_dir())
        self.bind_all(f"<{mod}-i>", lambda e: self._add_input_files())
        self.bind_all(f"<{mod}-r>", lambda e: self._run_all())

    # --------------------------------------------------------------- Widgets

    def _card(self, parent: ctk.CTkBaseClass) -> ctk.CTkFrame:
        return ctk.CTkFrame(parent, corner_radius=RADIUS_CARD, fg_color=CARD, border_width=0)

    def _section(self, parent: ctk.CTkBaseClass, text: str) -> ctk.CTkLabel:
        return ctk.CTkLabel(parent, text=text.upper(), font=self.fonts["section"],
                            text_color=LABEL_2, anchor="w")

    def _primary_button(self, parent, text, command, **kw) -> ctk.CTkButton:
        kw.setdefault("height", 44)
        return ctk.CTkButton(parent, text=text, command=command,
                             corner_radius=RADIUS_CONTROL, fg_color=ACCENT,
                             hover_color=ACCENT_HOVER, text_color=ON_ACCENT,
                             text_color_disabled=("#FFFFFF", "#8E8E93"),
                             font=self.fonts["button"], **kw)

    def _tinted_button(self, parent, text, command, **kw) -> ctk.CTkButton:
        kw.setdefault("height", 34)
        return ctk.CTkButton(parent, text=text, command=command,
                             corner_radius=RADIUS_CONTROL, fg_color=TINT,
                             hover_color=TINT_HOVER, text_color=ACCENT,
                             text_color_disabled=LABEL_2,
                             font=self.fonts["button"], **kw)

    def _plain_button(self, parent, text, command, **kw) -> ctk.CTkButton:
        kw.setdefault("height", 30)
        return ctk.CTkButton(parent, text=text, command=command, width=60,
                             corner_radius=RADIUS_CONTROL, fg_color="transparent",
                             hover_color=FIELD, text_color=ACCENT,
                             text_color_disabled=LABEL_2,
                             font=self.fonts["body"], **kw)

    def _load_logo(self, height: int) -> ctk.CTkImage | None:
        path = logo_file()
        if path is None:
            return None
        try:
            from PIL import Image

            img = Image.open(path).convert("RGBA")
            width = round(img.width * height / img.height)
            return ctk.CTkImage(light_image=img, dark_image=img, size=(width, height))
        except Exception:  # noqa: BLE001 – Logo ist optional
            return None

    def _separator(self, parent) -> ctk.CTkFrame:
        return ctk.CTkFrame(parent, height=2, fg_color=SEPARATOR, corner_radius=0)

    def _build_widgets(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        root = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                      scrollbar_button_color=SEPARATOR)
        self.content = root
        root.grid(row=0, column=0, sticky="nsew", padx=PAD, pady=(PAD, 0))
        root.grid_columnconfigure(0, weight=1)
        row = 0

        # --- Kopfzeile ------------------------------------------------
        header = ctk.CTkFrame(root, fg_color="transparent")
        header.grid(row=row, column=0, sticky="ew", pady=(4, 16))
        header.grid_columnconfigure(1, weight=1)
        logo = self._load_logo(56)
        if logo is not None:
            ctk.CTkLabel(header, text="", image=logo).grid(
                row=0, column=0, rowspan=2, sticky="w", padx=(0, 14))
        ctk.CTkLabel(header, text=APP_NAME, font=self.fonts["title"], text_color=LABEL,
                     anchor="w").grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(header, text="Vorhersage-Auswertung von Messdateien",
                     font=self.fonts["subtitle"], text_color=LABEL_2,
                     anchor="w").grid(row=1, column=1, sticky="w")
        ctk.CTkSegmentedButton(
            header, values=APPEARANCE_VALUES, variable=self.appearance_var,
            command=self._on_appearance_change, corner_radius=RADIUS_CONTROL, height=30,
            fg_color=SEGMENT_BG, selected_color=CARD, selected_hover_color=CARD,
            unselected_color=SEGMENT_BG, unselected_hover_color=SEPARATOR,
            text_color=LABEL, font=self.fonts["small"], border_width=3,
        ).grid(row=0, column=2, rowspan=2, sticky="e")
        row += 1

        # --- Projektordner --------------------------------------------
        self._section(root, "Projektordner").grid(row=row, column=0, sticky="w",
                                                   padx=12, pady=(0, 6))
        row += 1
        proj = self._card(root)
        proj.grid(row=row, column=0, sticky="ew", pady=(0, 18))
        proj.grid_columnconfigure(0, weight=1)
        row += 1

        entry = ctk.CTkEntry(proj, textvariable=self.project_var, height=36,
                             corner_radius=RADIUS_CONTROL, fg_color=FIELD, border_width=0,
                             text_color=LABEL, font=self.fonts["body"])
        entry.grid(row=0, column=0, sticky="ew", padx=(16, 8), pady=(16, 10))
        entry.bind("<Return>", lambda e: self._set_project_dir(self.project_var.get()))
        entry.bind("<FocusOut>", lambda e: self._set_project_dir(self.project_var.get()))
        self._tinted_button(proj, "Wählen…", self._choose_project_dir, width=100).grid(
            row=0, column=1, padx=(0, 8), pady=(16, 10))
        self._tinted_button(proj, "Im Finder zeigen", self._open_project_dir, width=140).grid(
            row=0, column=2, padx=(0, 16), pady=(16, 10))

        status = ctk.CTkFrame(proj, fg_color="transparent")
        status.grid(row=1, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 14))
        status.grid_columnconfigure(1, weight=1)
        self.status_dot = ctk.CTkLabel(status, text="●", font=self.fonts["body_bold"],
                                       text_color=GREEN, width=16, anchor="w")
        self.status_dot.grid(row=0, column=0, sticky="nw", padx=(0, 6), pady=(1, 0))
        self.status_var = tk.StringVar()
        ctk.CTkLabel(status, textvariable=self.status_var, font=self.fonts["small"],
                     text_color=LABEL_2, anchor="w", justify="left").grid(
            row=0, column=1, sticky="w")

        # --- Arbeitsschritte ------------------------------------------
        self._section(root, "Arbeitsschritte").grid(row=row, column=0, sticky="w",
                                                     padx=12, pady=(0, 6))
        row += 1
        steps = self._card(root)
        steps.grid(row=row, column=0, sticky="ew", pady=(0, 18))
        steps.grid_columnconfigure(1, weight=1)
        row += 1

        self.step_buttons: list[ctk.CTkButton] = []
        step_defs = [
            ("1", "Messdateien hinzufügen",
             "CSV-Dateien auswählen; sie werden nach input_csv kopiert.",
             "Auswählen…", self._add_input_files),
            ("2", "Vorhersagen berechnen",
             "Erzeugt für jede Messdatei eine *_output.txt im Ordner output.",
             "Berechnen", self._run_predictions),
            ("3", "Sortierte CSV erzeugen",
             "Fasst alle Output-Dateien in all_predict_lines_sorted.csv zusammen.",
             "Erzeugen", self._build_sorted_csv),
        ]
        for i, (num, title, desc, btn_text, cmd) in enumerate(step_defs):
            r = i * 2
            badge = ctk.CTkLabel(steps, text=num, width=30, height=30, corner_radius=15,
                                 fg_color=ACCENT, text_color=ON_ACCENT,
                                 font=self.fonts["badge"])
            badge.grid(row=r, column=0, padx=(16, 12), pady=14, sticky="n")
            text = ctk.CTkFrame(steps, fg_color="transparent")
            text.grid(row=r, column=1, sticky="ew", pady=12)
            ctk.CTkLabel(text, text=title, font=self.fonts["body_bold"], text_color=LABEL,
                         anchor="w").pack(anchor="w")
            ctk.CTkLabel(text, text=desc, font=self.fonts["small"], text_color=LABEL_2,
                         anchor="w", justify="left").pack(anchor="w")
            btn = self._tinted_button(steps, btn_text, cmd, width=120)
            btn.grid(row=r, column=2, padx=16, pady=12)
            self.step_buttons.append(btn)
            if i < len(step_defs) - 1:
                self._separator(steps).grid(row=r + 1, column=1, columnspan=2,
                                            sticky="ew", padx=(0, 16))

        run_all = self._primary_button(steps, "Auswertung starten  (Schritte 2 + 3)",
                                       self._run_all)
        run_all.grid(row=len(step_defs) * 2, column=0, columnspan=3, sticky="ew",
                     padx=16, pady=(6, 16))
        self.step_buttons.append(run_all)

        # --- Ergebnis -------------------------------------------------
        self._section(root, "Ergebnis").grid(row=row, column=0, sticky="w",
                                              padx=12, pady=(0, 6))
        row += 1
        result = self._card(root)
        result.grid(row=row, column=0, sticky="ew", pady=(0, 18))
        result.grid_columnconfigure(1, weight=1)
        row += 1

        ctk.CTkLabel(result, text="Sortierte CSV öffnen mit", font=self.fonts["body"],
                     text_color=LABEL, anchor="w").grid(row=0, column=0, padx=(16, 12),
                                                        pady=16, sticky="w")
        ctk.CTkSegmentedButton(
            result, values=["Numbers", "Excel", "Standardprogramm"],
            variable=self.open_with_var, command=self._on_open_with_change,
            corner_radius=RADIUS_CONTROL, height=32, fg_color=SEGMENT_BG,
            selected_color=CARD, selected_hover_color=CARD, unselected_color=SEGMENT_BG,
            unselected_hover_color=SEPARATOR, text_color=LABEL, font=self.fonts["small"],
            border_width=3,
        ).grid(row=0, column=1, sticky="w", pady=16)
        self.result_buttons: list[ctk.CTkButton] = []
        b = self._tinted_button(result, "Im Finder zeigen", self._reveal_csv, width=140)
        b.grid(row=0, column=2, padx=(8, 8), pady=16)
        self.result_buttons.append(b)
        b = self._primary_button(result, "Öffnen", self._open_csv, width=110, height=34)
        b.grid(row=0, column=3, padx=(0, 16), pady=16)
        self.result_buttons.append(b)

        # --- Protokoll ------------------------------------------------
        log_head = ctk.CTkFrame(root, fg_color="transparent")
        log_head.grid(row=row, column=0, sticky="ew", padx=12, pady=(0, 6))
        log_head.grid_columnconfigure(0, weight=1)
        self._section(log_head, "Protokoll").grid(row=0, column=0, sticky="w")
        self._plain_button(log_head, "Leeren", self._clear_log).grid(row=0, column=1, sticky="e")
        row += 1
        log_card = self._card(root)
        log_card.grid(row=row, column=0, sticky="nsew", pady=(0, 12))
        log_card.grid_columnconfigure(0, weight=1)
        log_card.grid_rowconfigure(0, weight=1)
        root.grid_rowconfigure(row, weight=1)
        row += 1

        self.log_text = ctk.CTkTextbox(log_card, height=200, corner_radius=RADIUS_CONTROL,
                                       fg_color=FIELD, border_width=0, text_color=LABEL,
                                       font=self.fonts["mono"], wrap="word",
                                       scrollbar_button_color=SEPARATOR)
        self.log_text.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        self.log_text.tag_config("error", foreground=RED[0] if ctk.get_appearance_mode() == "Light" else RED[1])
        self.log_text.tag_config("ok", foreground=GREEN[0] if ctk.get_appearance_mode() == "Light" else GREEN[1])
        self.log_text.configure(state="disabled")

        # --- Fußzeile -------------------------------------------------
        footer = ctk.CTkFrame(self, fg_color="transparent", height=28)
        footer.grid(row=1, column=0, sticky="ew", padx=PAD, pady=(0, 12))
        footer.grid_columnconfigure(0, weight=1)
        self.progress = ctk.CTkProgressBar(footer, mode="indeterminate", height=4,
                                           corner_radius=2, fg_color=SEPARATOR,
                                           progress_color=ACCENT)
        self.progress.grid(row=0, column=0, sticky="ew", pady=(6, 0))
        self.progress.grid_remove()
        self.footer_var = tk.StringVar(value=f"Version {__version__}")
        ctk.CTkLabel(footer, textvariable=self.footer_var, font=self.fonts["small"],
                     text_color=LABEL_2, anchor="e").grid(row=0, column=1, padx=(12, 0))

    # ---------------------------------------------------------- Einstellungen

    def _on_appearance_change(self, value: str) -> None:
        ctk.set_appearance_mode(APPEARANCE_MAP.get(value, "system"))
        self._save_config()
        self.after(50, self._refresh_log_tags)

    def _on_open_with_change(self, value: str) -> None:
        self._save_config()

    def _save_config(self) -> None:
        save_config({
            "project_dir": str(self.project.base_dir),
            "appearance": self.appearance_var.get(),
            "open_with": self.open_with_var.get(),
        })

    def _refresh_log_tags(self) -> None:
        dark = ctk.get_appearance_mode() == "Dark"
        self.log_text.tag_config("error", foreground=RED[1] if dark else RED[0])
        self.log_text.tag_config("ok", foreground=GREEN[1] if dark else GREEN[0])

    # ------------------------------------------------------------ Projekt

    def _set_project_dir(self, path: str) -> None:
        path = path.strip()
        if not path:
            return
        new = Path(path).expanduser()
        if self.project.base_dir == new.resolve():
            self._refresh_status()
            return
        self.project = self._new_project(new)
        self.project_var.set(str(self.project.base_dir))
        self._save_config()
        self._refresh_status()
        self._log(f"Projektordner: {self.project.base_dir}")

    def _choose_project_dir(self) -> None:
        chosen = filedialog.askdirectory(
            title="Projektordner wählen",
            initialdir=str(self.project.base_dir) if self.project.base_dir.exists() else str(Path.home()),
            mustexist=True,
        )
        if chosen:
            self._set_project_dir(chosen)

    def _open_project_dir(self) -> None:
        if not self.project.base_dir.is_dir():
            messagebox.showwarning(APP_NAME, "Der Projektordner existiert nicht.")
            return
        open_path(self.project.base_dir)

    def _refresh_status(self) -> None:
        p = self.project
        if not p.base_dir.is_dir():
            self.status_dot.configure(text_color=RED)
            self.status_var.set("Projektordner existiert nicht.")
            return
        missing = p.missing_coefficient_files()
        if missing:
            self.status_dot.configure(text_color=ORANGE)
            first = "Fehlende Koeffizienten-Dateien: " + ", ".join(missing)
        else:
            self.status_dot.configure(text_color=GREEN)
            source = {
                "projekt": "aus dem Projektordner",
                "eingebaut": "in der App eingebaut",
                "gemischt": "teils Projektordner, teils in der App eingebaut",
            }[p.coefficient_source()]
            first = f"Koeffizienten bereit ({source})"
        n_in = len(p.input_files())
        n_out = len(p.output_files())
        csv_state = "vorhanden" if p.sorted_csv.is_file() else "noch nicht erzeugt"
        self.status_var.set(
            f"{first}\n{n_in} Messdatei(en) · {n_out} Output-Datei(en) · Sortierte CSV {csv_state}"
        )

    # ------------------------------------------------------------- Schritte

    def _add_input_files(self) -> None:
        if self._busy:
            return
        files = filedialog.askopenfilenames(
            title="Messdateien (CSV) auswählen",
            filetypes=[("CSV-Dateien", "*.csv"), ("Alle Dateien", "*")],
        )
        if not files:
            return
        try:
            copied = self.project.add_input_files([Path(f) for f in files], log=self._log)
        except OSError as exc:
            self._log(f"Fehler beim Kopieren: {exc}", tag="error")
            messagebox.showerror(APP_NAME, f"Fehler beim Kopieren:\n{exc}")
            return
        self._log(f"{len(copied)} Datei(en) in {self.project.input_dir} kopiert.", tag="ok")
        self._refresh_status()

    def _run_predictions(self) -> None:
        self._run_in_background("Vorhersagen berechnen", self.project.run_predictions)

    def _build_sorted_csv(self) -> None:
        self._run_in_background("Sortierte CSV erzeugen", self.project.build_sorted_csv)

    def _build_first_lines_csv(self) -> None:
        self._run_in_background("Zusammenfassung erste Zeilen", self.project.build_first_lines_csv)

    def _run_all(self) -> None:
        self._run_in_background("Auswertung", self.project.run_all)

    def _clear_input(self) -> None:
        if self._busy:
            return
        n = len(self.project.input_files())
        if n == 0:
            messagebox.showinfo(APP_NAME, "Der Input-Ordner ist bereits leer.")
            return
        if messagebox.askyesno(APP_NAME, f"{n} CSV-Datei(en) aus dem Input-Ordner löschen?"):
            self.project.clear_input(log=self._log)
            self._refresh_status()

    def _clear_output(self) -> None:
        if self._busy:
            return
        n = len(self.project.output_files())
        if n == 0:
            messagebox.showinfo(APP_NAME, "Der Output-Ordner ist bereits leer.")
            return
        if messagebox.askyesno(APP_NAME, f"{n} Output-Datei(en) löschen?"):
            self.project.clear_output(log=self._log)
            self._refresh_status()

    # ------------------------------------------------------------ Ergebnis

    def _ensure_csv(self) -> Path | None:
        csv_path = self.project.sorted_csv
        if not csv_path.is_file():
            messagebox.showwarning(
                APP_NAME,
                "Die sortierte CSV wurde noch nicht erzeugt.\n"
                "Bitte zuerst Schritt 3 „Sortierte CSV erzeugen“ ausführen.",
            )
            return None
        return csv_path

    def _open_csv(self) -> None:
        csv_path = self._ensure_csv()
        if csv_path is None:
            return
        choice = self.open_with_var.get()
        app = {"Numbers": "Numbers", "Excel": "Microsoft Excel"}.get(choice)
        if sys.platform != "darwin":
            app = None
        try:
            open_path(csv_path, app=app)
            self._log(f"Geöffnet mit {app or 'Standardprogramm'}: {csv_path.name}")
        except (OSError, subprocess.CalledProcessError) as exc:
            self._log(f"Konnte {app or 'Standardprogramm'} nicht öffnen: {exc}", tag="error")
            messagebox.showerror(
                APP_NAME,
                f"„{app or 'Standardprogramm'}“ konnte nicht geöffnet werden.\n"
                f"Ist das Programm installiert?\n\n{exc}",
            )

    def _reveal_csv(self) -> None:
        csv_path = self._ensure_csv()
        if csv_path is not None:
            reveal_in_finder(csv_path)

    # ---------------------------------------------------------- Hintergrund

    def _run_in_background(self, title: str, func) -> None:
        if self._busy:
            messagebox.showinfo(APP_NAME, "Es läuft bereits eine Auswertung.")
            return
        self._set_busy(True, title)
        self._log(f"— {title} gestartet —")

        def worker() -> None:
            try:
                func(log=self._log)
                self._log_queue.put(("done", title))
            except Exception as exc:  # noqa: BLE001 – Fehler dem Nutzer anzeigen
                self._log_queue.put(("error", (title, exc, traceback.format_exc())))

        threading.Thread(target=worker, daemon=True).start()

    def _set_busy(self, busy: bool, title: str = "") -> None:
        self._busy = busy
        state = "disabled" if busy else "normal"
        for b in self.step_buttons + self.result_buttons:
            b.configure(state=state)
        if busy:
            self.footer_var.set(f"{title} läuft…")
            self.progress.grid()
            self.progress.start()
        else:
            self.progress.stop()
            self.progress.grid_remove()
            self.footer_var.set(f"Version {__version__}")

    # -------------------------------------------------------------- Protokoll

    def _log(self, message: str, tag: str | None = None) -> None:
        """Threadsicher: Nachrichten landen in der Queue und werden im UI-Thread geschrieben."""
        self._log_queue.put(("log", (message, tag)))

    def _append_log(self, message: str, tag: str | None = None) -> None:
        self.log_text.configure(state="normal")
        if tag:
            self.log_text.insert("end", message + "\n", tag)
        else:
            self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _drain_log_queue(self) -> None:
        try:
            while True:
                kind, payload = self._log_queue.get_nowait()
                if kind == "log":
                    message, tag = payload  # type: ignore[misc]
                    self._append_log(message, tag)
                elif kind == "done":
                    self._append_log(f"— {payload} abgeschlossen —", "ok")
                    self._set_busy(False)
                    self._refresh_status()
                elif kind == "error":
                    title, exc, tb = payload  # type: ignore[misc]
                    self._append_log(f"Fehler bei „{title}“: {exc}", "error")
                    self._append_log(tb.rstrip(), "error")
                    self._set_busy(False)
                    self._refresh_status()
                    messagebox.showerror(APP_NAME, f"Fehler bei „{title}“:\n\n{exc}")
        except queue.Empty:
            pass
        self.after(100, self._drain_log_queue)

    # ------------------------------------------------------------------ Misc

    def _show_about(self) -> None:
        messagebox.showinfo(
            f"Über {APP_NAME}",
            f"{APP_NAME} {__version__}\n\n"
            "Berechnet Vorhersagen aus Messdateien und fasst die Ergebnisse\n"
            "in einer sortierten CSV-Datei zusammen.",
        )

    def _on_close(self) -> None:
        if self._busy and not messagebox.askyesno(
            APP_NAME, "Eine Auswertung läuft noch. Trotzdem beenden?"
        ):
            return
        self.destroy()


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
