# Predict Endpoint

macOS-App mit grafischer Oberfläche im iOS-Stil für die Vorhersage-Auswertung
von Messdateien. Die Oberfläche nutzt [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
(abgerundete Karten, System-Akzentfarbe, helles und dunkles Erscheinungsbild).
Die App bündelt die drei bisherigen Skripte
(`coeff_calc_batch_predict_project.py`, `extract_all_predict_lines_sorted.py`,
`extract_first_lines.py`) hinter vier Schaltflächen:

1. **Messdateien hinzufügen** – CSV-Dateien auswählen, sie werden nach `input_csv/` kopiert.
2. **Vorhersagen berechnen** – erzeugt für jede Messdatei eine `*_output.txt` in `output/`.
3. **Sortierte CSV erzeugen** – fasst alle Output-Dateien in `all_predict_lines_sorted.csv` zusammen.
4. **CSV öffnen** – öffnet die CSV direkt in Numbers, Excel oder dem Standardprogramm.

Mit „Schritte 2 + 3 ausführen“ laufen Berechnung und CSV-Erzeugung in einem Rutsch.

## Projektordner

Die App arbeitet in einem **Projektordner** mit den beiden Unterordnern für
Ein- und Ausgabe. Die Koeffizienten-Dateien sind in die gebaute App eingebaut;
liegen sie zusätzlich im Projektordner, haben diese Vorrang (so lassen sich
Koeffizienten ohne Neubau austauschen):

```
Projektordner/
├── input_csv/                     ← Messdateien
├── output/                        ← *_output.txt
└── all_predict_lines_sorted.csv   ← Ergebnis
```

Standardmäßig ist das der Ordner, in dem die App liegt (bzw. dieses Repository beim
Start aus dem Quellcode). Über „Wählen…“ kann ein anderer Ordner gesetzt werden; die
Auswahl wird gespeichert. Die Statuszeile unter dem Ordnerpfad zeigt, ob die
Koeffizienten aus der App oder aus dem Projektordner stammen.

## App erstellen (macOS)

Voraussetzung: Python 3 von [python.org](https://www.python.org/downloads/macos/)
(enthält Tkinter; das mit Xcode gelieferte Python reicht nicht immer).

```bash
./build_app.sh
```

Danach liegt `dist/Predict Endpoint.app` bereit. Die App kann an einen beliebigen
Ort verschoben werden, z. B. nach `/Applications`. Als Projektordner nimmt sie
zunächst den Ordner, in dem sie liegt; ein anderer lässt sich über „Wählen…“ setzen.

Beim ersten Start meldet macOS evtl. „Entwickler kann nicht verifiziert werden“:
Rechtsklick auf die App → „Öffnen“.

## Ohne Build starten

```bash
python3 -m pip install -r requirements.txt   # einmalig: CustomTkinter
python3 main.py
```

Ist CustomTkinter nicht installiert, startet automatisch die klassische
Tkinter-Oberfläche (`predict_app/gui_classic.py`).

oder per Doppelklick auf `Predict Endpoint starten.command`.

## Kommandozeile wie bisher

Die alten Aufrufe funktionieren weiterhin und nutzen dieselbe Logik:

```bash
python3 coeff_calc_batch_predict_project.py     # Vorhersagen berechnen
python3 extract_all_predict_lines_sorted.py     # sortierte CSV erzeugen
python3 extract_first_lines.py                  # nur erste Zeilen zusammenfassen
```

## Tests

```bash
python3 -m unittest discover -s tests -v
```
