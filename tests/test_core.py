import csv
import tempfile
import unittest
from pathlib import Path

from predict_app.core import SETTINGS, Project, get_predict, get_real_res


def write_measurement(path: Path, values, device_id="DEVICE_ID_7"):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["t", "a", "b", "c", "value"])
        for i, v in enumerate(values):
            w.writerow([i, 0, 0, 0, v])


def write_coefficients(base: Path, coeff_value=0.5, intercept=1.0):
    for index_len, coeff_name, intercept_name, _ in SETTINGS:
        with open(base / coeff_name, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            for _ in range(index_len):
                w.writerow([coeff_value])
        (base / intercept_name).write_text(f"[{intercept}]", encoding="utf-8")


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        write_coefficients(self.base)
        self.project = Project(self.base)
        self.project.ensure_dirs()

    def tearDown(self):
        self._tmp.cleanup()

    def test_missing_coefficient_files(self):
        (self.base / "coeff_600.csv").unlink()
        self.assertEqual(self.project.missing_coefficient_files(), ["coeff_600.csv"])

    def test_get_real_res_and_predict(self):
        mess = self.base / "m.csv"
        write_measurement(mess, [2.0] * 2000)
        self.assertEqual(get_real_res(mess), 2.0)
        pred = get_predict(mess, 151, self.base / "coeff_300.csv", self.base / "intercept_300.txt")
        # 151 Werte * 2.0 * 0.5 + 1.0
        self.assertAlmostEqual(pred, 151 * 2.0 * 0.5 + 1.0)

    def test_full_workflow(self):
        src_dir = self.base / "src"
        src_dir.mkdir()
        f1 = src_dir / "DEVICE_ID_12_run1.csv"
        f2 = src_dir / "DEVICE_ID_3_run2.csv"
        write_measurement(f1, [1.0] * 2000)
        write_measurement(f2, [4.0] * 2000)
        (src_dir / "notes.txt").write_text("x")

        copied = self.project.add_input_files([f1, f2, src_dir / "notes.txt"])
        self.assertEqual([p.name for p in copied], [f1.name, f2.name])
        self.assertEqual(len(self.project.input_files()), 2)

        outputs = self.project.run_predictions()
        self.assertEqual(len(outputs), 2)
        text = (self.project.output_dir / "DEVICE_ID_12_run1_output.txt").read_text()
        lines = text.splitlines()
        self.assertEqual(len(lines), 4)
        self.assertTrue(lines[0].startswith("predict 300:"))
        self.assertTrue(lines[3].startswith("predict 3599:"))

        csv_path = self.project.build_sorted_csv()
        with open(csv_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 8)
        # Sortierung: erst Zeilennummer, dann Dateiname
        self.assertEqual([r["line_number"] for r in rows], ["1", "1", "2", "2", "3", "3", "4", "4"])
        self.assertEqual(rows[0]["filename"], "DEVICE_ID_12_run1_output.txt")
        self.assertEqual(rows[0]["device_id"], "12")
        self.assertEqual(rows[1]["device_id"], "3")
        self.assertEqual(rows[0]["predict_label"], "300")
        self.assertAlmostEqual(float(rows[0]["predicted_value"]), 151 * 1.0 * 0.5 + 1.0)

        first = self.project.build_first_lines_csv()
        with open(first, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["predict_label"], "300")

    def test_run_predictions_without_coefficients_raises(self):
        (self.base / "intercept_1800.txt").unlink()
        write_measurement(self.base / "input_csv" / "a.csv", [1.0] * 10)
        with self.assertRaises(FileNotFoundError):
            self.project.run_predictions()

    def test_run_predictions_without_input(self):
        messages = []
        self.assertEqual(self.project.run_predictions(log=messages.append), [])
        self.assertTrue(messages[0].startswith("Keine CSV-Dateien gefunden"))


if __name__ == "__main__":
    unittest.main()
