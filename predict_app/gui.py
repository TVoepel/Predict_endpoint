"""Grafische Oberfläche (Tkinter) für die Vorhersage-Auswertung."""

from __future__ import annotations

import queue
import subprocess
import sys
import threading
import traceback
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .core import Project
from .paths import (APP_NAME, bundled_coefficient_dir, default_project_dir,
                    load_config, save_config)

PADX = 12
PADY = 6


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


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.minsize(720, 560)

        self._log_queue: "queue.Queue[tuple[str, object]]" = queue.Queue()
        self._busy = False

        config = load_config()
        start_dir = config.get("project_dir") or str(default_project_dir())
        self.project_var = tk.StringVar(value=start_dir)
        self.project = Project(start_dir, fallback_coeff_dir=bundled_coefficient_dir())

        self._build_menu()
        self._build_widgets()
        self._refresh_status()
        self.after(100, self._drain_log_queue)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ UI

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)

        if sys.platform == "darwin":
            app_menu = tk.Menu(menubar, name="apple", tearoff=0)
            app_menu.add_command(label=f"Über {APP_NAME}", command=self._show_about)
            menubar.add_cascade(menu=app_menu)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Projektordner wählen…", command=self._choose_project_dir,
                              accelerator="Cmd+O" if sys.platform == "darwin" else "Ctrl+O")
        file_menu.add_command(label="Messdateien hinzufügen…", command=self._add_input_files)
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
        run_menu.add_command(label="Alles ausführen", command=self._run_all,
                             accelerator="Cmd+R" if sys.platform == "darwin" else "Ctrl+R")
        run_menu.add_separator()
        run_menu.add_command(label="Input-Ordner leeren…", command=self._clear_input)
        run_menu.add_command(label="Output-Ordner leeren…", command=self._clear_output)
        menubar.add_cascade(label="Auswertung", menu=run_menu)

        self.config(menu=menubar)

        mod = "Command" if sys.platform == "darwin" else "Control"
        self.bind_all(f"<{mod}-o>", lambda e: self._choose_project_dir())
        self.bind_all(f"<{mod}-r>", lambda e: self._run_all())

    def _build_widgets(self) -> None:
        outer = ttk.Frame(self, padding=(PADX, PADY))
        outer.pack(fill="both", expand=True)

        # --- Projektordner --------------------------------------------
        proj = ttk.LabelFrame(outer, text="Projektordner (input_csv, output, Ergebnis-CSV)")
        proj.pack(fill="x", pady=(0, PADY))

        entry = ttk.Entry(proj, textvariable=self.project_var)
        entry.grid(row=0, column=0, sticky="ew", padx=(PADX, 4), pady=PADY)
        entry.bind("<Return>", lambda e: self._set_project_dir(self.project_var.get()))
        entry.bind("<FocusOut>", lambda e: self._set_project_dir(self.project_var.get()))
        ttk.Button(proj, text="Wählen…", command=self._choose_project_dir).grid(
            row=0, column=1, padx=2, pady=PADY)
        ttk.Button(proj, text="Im Finder zeigen", command=self._open_project_dir).grid(
            row=0, column=2, padx=(2, PADX), pady=PADY)
        proj.columnconfigure(0, weight=1)

        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(proj, textvariable=self.status_var, justify="left")
        self.status_label.grid(row=1, column=0, columnspan=3, sticky="w",
                               padx=PADX, pady=(0, PADY))

        # --- Arbeitsschritte ------------------------------------------
        steps = ttk.LabelFrame(outer, text="Arbeitsschritte")
        steps.pack(fill="x", pady=(0, PADY))

        self.step_buttons: list[ttk.Button] = []

        def add_step(row: int, number: str, text: str, desc: str, command) -> None:
            btn = ttk.Button(steps, text=f"{number}  {text}", command=command, width=34)
            btn.grid(row=row, column=0, sticky="w", padx=(PADX, 8), pady=4)
            ttk.Label(steps, text=desc, foreground="#555555").grid(
                row=row, column=1, sticky="w", pady=4)
            self.step_buttons.append(btn)

        add_step(0, "1.", "Messdateien hinzufügen…",
                 "CSV-Dateien auswählen; sie werden in den Ordner input_csv kopiert.",
                 self._add_input_files)
        add_step(1, "2.", "Vorhersagen berechnen",
                 "Erzeugt für jede Messdatei eine *_output.txt im Ordner output.",
                 self._run_predictions)
        add_step(2, "3.", "Sortierte CSV erzeugen",
                 "Fasst alle Output-Dateien in all_predict_lines_sorted.csv zusammen.",
                 self._build_sorted_csv)
        add_step(3, "4.", "CSV öffnen (Numbers / Excel)",
                 "Öffnet die sortierte CSV im Tabellenprogramm.",
                 self._open_csv_dialog)

        ttk.Separator(steps, orient="horizontal").grid(
            row=4, column=0, columnspan=2, sticky="ew", padx=PADX, pady=6)

        run_all_btn = ttk.Button(steps, text="▶  Schritte 2 + 3 ausführen", command=self._run_all,
                                 width=34)
        run_all_btn.grid(row=5, column=0, sticky="w", padx=(PADX, 8), pady=(0, PADY))
        self.step_buttons.append(run_all_btn)
        ttk.Label(steps, text="Berechnet alle Vorhersagen und erzeugt danach die sortierte CSV.",
                  foreground="#555555").grid(row=5, column=1, sticky="w", pady=(0, PADY))

        steps.columnconfigure(1, weight=1)

        # --- Ergebnis-Buttons -----------------------------------------
        results = ttk.Frame(outer)
        results.pack(fill="x", pady=(0, PADY))
        ttk.Label(results, text="Ergebnis:").pack(side="left", padx=(0, 8))
        self.result_buttons: list[ttk.Button] = []
        for label, cmd in (
            ("In Numbers öffnen", lambda: self._open_csv(app="Numbers")),
            ("In Excel öffnen", lambda: self._open_csv(app="Microsoft Excel")),
            ("Standardprogramm", lambda: self._open_csv(app=None)),
            ("Im Finder zeigen", self._reveal_csv),
        ):
            b = ttk.Button(results, text=label, command=cmd)
            b.pack(side="left", padx=2)
            self.result_buttons.append(b)

        # --- Protokoll ------------------------------------------------
        log_frame = ttk.LabelFrame(outer, text="Protokoll")
        log_frame.pack(fill="both", expand=True)

        self.log_text = tk.Text(log_frame, height=12, wrap="word", state="disabled",
                                font=("Menlo", 11) if sys.platform == "darwin" else None)
        scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)
        self.log_text.pack(side="left", fill="both", expand=True, padx=(PADX, 0), pady=PADY)
        scroll.pack(side="right", fill="y", padx=(0, PADX), pady=PADY)

        self.log_text.tag_configure("error", foreground="#b00020")
        self.log_text.tag_configure("ok", foreground="#1b7f3b")

        # --- Fortschritt ----------------------------------------------
        bottom = ttk.Frame(outer)
        bottom.pack(fill="x", pady=(PADY, 0))
        self.progress = ttk.Progressbar(bottom, mode="indeterminate")
        self.progress.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(bottom, text="Protokoll leeren", command=self._clear_log).pack(side="right")

    # ------------------------------------------------------------ Projekt

    def _set_project_dir(self, path: str) -> None:
        path = path.strip()
        if not path:
            return
        new = Path(path).expanduser()
        if self.project.base_dir == new.resolve():
            self._refresh_status()
            return
        self.project = Project(new, fallback_coeff_dir=bundled_coefficient_dir())
        self.project_var.set(str(self.project.base_dir))
        save_config({"project_dir": str(self.project.base_dir)})
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
        lines = []
        if not p.base_dir.is_dir():
            lines.append("⚠️  Projektordner existiert nicht.")
        else:
            missing = p.missing_coefficient_files()
            if missing:
                lines.append("⚠️  Fehlende Koeffizienten-Dateien: " + ", ".join(missing))
            else:
                source = {
                    "projekt": "aus dem Projektordner",
                    "eingebaut": "in der App eingebaut",
                    "gemischt": "teils Projektordner, teils in der App eingebaut",
                }[p.coefficient_source()]
                lines.append(f"✅  Koeffizienten-Dateien vorhanden ({source}).")
            n_in = len(p.input_files())
            n_out = len(p.output_files())
            lines.append(f"Input-Dateien: {n_in}    Output-Dateien: {n_out}    "
                         f"Sortierte CSV: {'vorhanden' if p.sorted_csv.is_file() else 'noch nicht erzeugt'}")
        self.status_var.set("\n".join(lines))

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
        self._run_in_background("Schritte 2 + 3", self.project.run_all)

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

    def _open_csv(self, app: str | None) -> None:
        csv_path = self._ensure_csv()
        if csv_path is None:
            return
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

    def _open_csv_dialog(self) -> None:
        csv_path = self._ensure_csv()
        if csv_path is None:
            return
        if sys.platform != "darwin":
            self._open_csv(app=None)
            return

        dlg = tk.Toplevel(self)
        dlg.title("CSV öffnen")
        dlg.transient(self)
        dlg.resizable(False, False)
        ttk.Label(dlg, text=f"{csv_path.name} öffnen mit:", padding=(PADX, PADY)).pack()
        row = ttk.Frame(dlg, padding=(PADX, 0, PADX, PADY))
        row.pack()

        def choose(app: str | None) -> None:
            dlg.destroy()
            self._open_csv(app=app)

        ttk.Button(row, text="Numbers", command=lambda: choose("Numbers")).pack(side="left", padx=4)
        ttk.Button(row, text="Excel", command=lambda: choose("Microsoft Excel")).pack(side="left", padx=4)
        ttk.Button(row, text="Standardprogramm", command=lambda: choose(None)).pack(side="left", padx=4)
        ttk.Button(row, text="Abbrechen", command=dlg.destroy).pack(side="left", padx=4)
        dlg.grab_set()

    # ---------------------------------------------------------- Hintergrund

    def _run_in_background(self, title: str, func) -> None:
        if self._busy:
            messagebox.showinfo(APP_NAME, "Es läuft bereits eine Auswertung.")
            return
        self._set_busy(True)
        self._log(f"--- {title} gestartet ---")

        def worker() -> None:
            try:
                func(log=self._log)
                self._log_queue.put(("done", title))
            except Exception as exc:  # noqa: BLE001 – Fehler dem Nutzer anzeigen
                self._log_queue.put(("error", (title, exc, traceback.format_exc())))

        threading.Thread(target=worker, daemon=True).start()

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        state = "disabled" if busy else "normal"
        for b in self.step_buttons + self.result_buttons:
            b.configure(state=state)
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()

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
                    self._append_log(f"--- {payload} abgeschlossen ---", "ok")
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
