"""Kernlogik der Auswertung.

Enthält die Funktionen aus den ursprünglichen Skripten
``coeff_calc_batch_predict_project.py``,
``extract_all_predict_lines_sorted.py`` und ``extract_first_lines.py``,
jedoch mit frei wählbarem Projektordner, damit sie sowohl aus der
Kommandozeile als auch aus der App heraus verwendet werden können.

Ein Projektordner hat folgenden Aufbau::

    <Projektordner>/
        coeff_300.csv      intercept_300.txt
        coeff_600.csv      intercept_600.txt
        coeff_1800.csv     intercept_1800.txt
        coeff_3599.csv     intercept_3599.txt
        input_csv/         <- zu analysierende Messdateien (*.csv)
        output/            <- erzeugte *_output.txt Dateien
        all_predict_lines_sorted.csv
        first_lines_summary.csv
"""

from __future__ import annotations

import csv
import re
import shutil
from pathlib import Path
from typing import Callable, Iterable

Logger = Callable[[str], None]

# (Anzahl Messwerte, Koeffizientendatei, Intercept-Datei, Bezeichnung)
SETTINGS = [
    (151, "coeff_300.csv", "intercept_300.txt", "300"),
    (301, "coeff_600.csv", "intercept_600.txt", "600"),
    (901, "coeff_1800.csv", "intercept_1800.txt", "1800"),
    (1800, "coeff_3599.csv", "intercept_3599.txt", "3599"),
]

INPUT_DIR_NAME = "input_csv"
OUTPUT_DIR_NAME = "output"
SORTED_CSV_NAME = "all_predict_lines_sorted.csv"
FIRST_LINES_CSV_NAME = "first_lines_summary.csv"

LINE_PATTERN = re.compile(r"predict\s+(\d+):([-\d.eE]+)\s+err:\s+([-\d.eE]+)")
DEVICE_PATTERN = re.compile(r"DEVICE_ID_(\d+)")


def _noop(_: str) -> None:
    pass


# ---------------------------------------------------------------------------
# Schritt 1: Vorhersagen berechnen (coeff_calc_batch_predict_project.py)
# ---------------------------------------------------------------------------

def get_real_res(mess_file: Path) -> float:
    """Letzter gültiger Messwert (Spalte 5) einer Messdatei."""
    last_row = None

    with open(mess_file, newline="", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)
        next(reader, None)

        for row in reader:
            if row and len(row) > 4:
                last_row = row

    if last_row is None:
        raise ValueError(f"Keine gültigen Daten in {mess_file}")

    return float(last_row[4].strip())


def get_predict(mess_file: Path, index_len: int, coef_file: Path, intercept_file: Path) -> float:
    """Lineare Vorhersage aus den ersten ``index_len`` Messwerten."""
    values = []

    with open(mess_file, newline="", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)
        next(reader, None)

        for i, row in enumerate(reader):
            if i >= index_len:
                break
            if len(row) > 4:
                values.append(float(row[4].strip()))

    coeffs = []
    with open(coef_file, newline="", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)

        for i, row in enumerate(reader):
            if i >= index_len:
                break
            coeffs.append(float(row[0].strip()))

    with open(intercept_file, "r", encoding="utf-8") as file:
        intercept = float(file.read().strip().strip("[]"))

    predicted_result = 0.0
    for i in range(min(len(values), len(coeffs))):
        predicted_result += values[i] * coeffs[i]

    return predicted_result + intercept


def process_file(
    csv_file: Path,
    output_dir: Path,
    base_dir: Path,
    resolve: Callable[[str], Path] | None = None,
) -> Path:
    """Berechnet alle Vorhersagen einer Messdatei und schreibt die Output-Datei.

    ``resolve`` liefert den Pfad zu einer Koeffizienten-Datei anhand ihres
    Namens; ohne Angabe wird sie direkt in ``base_dir`` erwartet.
    """
    if resolve is None:
        resolve = lambda name: base_dir / name  # noqa: E731

    real_res = get_real_res(csv_file)
    results = []

    for index_len, coeff_name, intercept_name, label in SETTINGS:
        predicted_result = get_predict(
            csv_file, index_len, resolve(coeff_name), resolve(intercept_name)
        )
        err = abs(1 - predicted_result / real_res) * 100
        results.append(f"predict {label}:{predicted_result} err: {err}")

    output_file = output_dir / f"{csv_file.stem}_output.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(results))

    return output_file


# ---------------------------------------------------------------------------
# Schritt 2: Output-Dateien zu CSV zusammenführen
# ---------------------------------------------------------------------------

def _parse_predict_line(line: str):
    match = LINE_PATTERN.match(line)
    if match:
        return match.group(1), float(match.group(2)), float(match.group(3))
    return "", "", ""


def extract_all_predict_lines_sorted(output_dir: Path, output_csv: Path) -> int:
    """Alle Zeilen aller ``*_output.txt`` sortiert in eine CSV schreiben.

    Entspricht ``extract_all_predict_lines_sorted.py``. Gibt die Anzahl der
    geschriebenen Datenzeilen zurück.
    """
    rows = []

    for txt_file in output_dir.glob("*_output.txt"):
        device_match = DEVICE_PATTERN.search(txt_file.name)
        device_id = device_match.group(1) if device_match else ""

        with open(txt_file, "r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue

                predict_label, predicted_value, err_value = _parse_predict_line(line)

                rows.append([
                    line_number,
                    txt_file.name,
                    device_id,
                    line,
                    predict_label,
                    predicted_value,
                    err_value,
                ])

    rows.sort(key=lambda x: (x[0], x[1]))

    with open(output_csv, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "line_number",
            "filename",
            "device_id",
            "raw_line",
            "predict_label",
            "predicted_value",
            "err_value",
        ])
        writer.writerows(rows)

    return len(rows)


def extract_first_lines(output_dir: Path, output_csv: Path) -> int:
    """Nur die erste Zeile jeder ``*_output.txt`` in eine CSV schreiben.

    Entspricht ``extract_first_lines.py``. Gibt die Anzahl der Zeilen zurück.
    """
    rows = []

    for txt_file in sorted(output_dir.glob("*_output.txt")):
        with open(txt_file, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()

        predict_label, predicted_value, err_value = _parse_predict_line(first_line)

        rows.append([
            txt_file.name,
            first_line,
            predict_label,
            predicted_value,
            err_value,
        ])

    with open(output_csv, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "filename",
            "first_line",
            "predict_label",
            "predicted_value",
            "err_value",
        ])
        writer.writerows(rows)

    return len(rows)


# ---------------------------------------------------------------------------
# Projekt: bündelt Ordner und Arbeitsschritte
# ---------------------------------------------------------------------------

class Project:
    """Ein Projektordner mit Eingabe- und Ausgabeordner.

    Koeffizienten-Dateien werden zuerst im Projektordner gesucht. Fehlen sie
    dort, wird auf ``fallback_coeff_dir`` zurückgegriffen (z. B. die in die
    App eingebauten Dateien). So kann ein Projektordner eigene Koeffizienten
    mitbringen, muss es aber nicht.
    """

    def __init__(self, base_dir: Path | str, fallback_coeff_dir: Path | str | None = None):
        self.base_dir = Path(base_dir).expanduser().resolve()
        self.fallback_coeff_dir = (
            Path(fallback_coeff_dir).expanduser().resolve() if fallback_coeff_dir else None
        )

    @property
    def input_dir(self) -> Path:
        return self.base_dir / INPUT_DIR_NAME

    @property
    def output_dir(self) -> Path:
        return self.base_dir / OUTPUT_DIR_NAME

    @property
    def sorted_csv(self) -> Path:
        return self.base_dir / SORTED_CSV_NAME

    @property
    def first_lines_csv(self) -> Path:
        return self.base_dir / FIRST_LINES_CSV_NAME

    def coefficient_names(self) -> list[str]:
        names = []
        for _, coeff_name, intercept_name, _ in SETTINGS:
            names.append(coeff_name)
            names.append(intercept_name)
        return names

    def coefficient_path(self, name: str) -> Path:
        """Pfad einer Koeffizienten-Datei: Projektordner vor Fallback-Ordner."""
        local = self.base_dir / name
        if local.is_file() or self.fallback_coeff_dir is None:
            return local
        fallback = self.fallback_coeff_dir / name
        return fallback if fallback.is_file() else local

    def coefficient_files(self) -> list[Path]:
        return [self.coefficient_path(n) for n in self.coefficient_names()]

    def missing_coefficient_files(self) -> list[str]:
        return [p.name for p in self.coefficient_files() if not p.is_file()]

    def coefficient_source(self) -> str:
        """"projekt", "eingebaut", "gemischt" oder "fehlend"."""
        files = self.coefficient_files()
        if any(not p.is_file() for p in files):
            return "fehlend"
        local = sum(1 for p in files if p.parent == self.base_dir)
        if local == len(files):
            return "projekt"
        if local == 0:
            return "eingebaut"
        return "gemischt"

    def ensure_dirs(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.input_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)

    def input_files(self) -> list[Path]:
        if not self.input_dir.is_dir():
            return []
        return sorted(self.input_dir.glob("*.csv"))

    def output_files(self) -> list[Path]:
        if not self.output_dir.is_dir():
            return []
        return sorted(self.output_dir.glob("*_output.txt"))

    # -- Schritt 1: Daten in den Input-Ordner kopieren ---------------------

    def add_input_files(self, paths: Iterable[Path | str], log: Logger = _noop) -> list[Path]:
        """Kopiert CSV-Dateien in den Input-Ordner. Gibt die Ziele zurück."""
        self.ensure_dirs()
        copied = []
        for src in paths:
            src = Path(src)
            if src.suffix.lower() != ".csv":
                log(f"Übersprungen (keine CSV): {src.name}")
                continue
            dst = self.input_dir / src.name
            if src.resolve() == dst.resolve():
                log(f"Bereits im Input-Ordner: {src.name}")
                continue
            shutil.copy2(src, dst)
            copied.append(dst)
            log(f"Kopiert: {src.name}")
        return copied

    def clear_input(self, log: Logger = _noop) -> int:
        count = 0
        for f in self.input_files():
            f.unlink()
            count += 1
        log(f"{count} Datei(en) aus dem Input-Ordner entfernt.")
        return count

    def clear_output(self, log: Logger = _noop) -> int:
        count = 0
        for f in self.output_files():
            f.unlink()
            count += 1
        log(f"{count} Datei(en) aus dem Output-Ordner entfernt.")
        return count

    # -- Schritt 2: Vorhersagen berechnen ----------------------------------

    def run_predictions(self, log: Logger = _noop) -> list[Path]:
        """Entspricht ``python3 coeff_calc_batch_predict_project.py``."""
        self.ensure_dirs()

        missing = self.missing_coefficient_files()
        if missing:
            raise FileNotFoundError(
                "Fehlende Koeffizienten-Dateien im Projektordner: " + ", ".join(missing)
            )

        csv_files = self.input_files()
        if not csv_files:
            log(f"Keine CSV-Dateien gefunden in: {self.input_dir}")
            return []

        outputs = []
        for csv_file in csv_files:
            outputs.append(
                process_file(csv_file, self.output_dir, self.base_dir, self.coefficient_path)
            )
            log(f"Verarbeitet: {csv_file.name}")

        log(f"Ergebnisse gespeichert in: {self.output_dir}")
        return outputs

    # -- Schritt 3: Sortierte CSV erzeugen ---------------------------------

    def build_sorted_csv(self, log: Logger = _noop) -> Path:
        """Entspricht ``python3 extract_all_predict_lines_sorted.py``."""
        self.ensure_dirs()
        count = extract_all_predict_lines_sorted(self.output_dir, self.sorted_csv)
        log(f"CSV geschrieben ({count} Zeilen): {self.sorted_csv}")
        return self.sorted_csv

    def build_first_lines_csv(self, log: Logger = _noop) -> Path:
        """Entspricht ``python3 extract_first_lines.py``."""
        self.ensure_dirs()
        count = extract_first_lines(self.output_dir, self.first_lines_csv)
        log(f"CSV geschrieben ({count} Zeilen): {self.first_lines_csv}")
        return self.first_lines_csv

    # -- Alles auf einmal --------------------------------------------------

    def run_all(self, log: Logger = _noop) -> Path:
        self.run_predictions(log)
        return self.build_sorted_csv(log)
