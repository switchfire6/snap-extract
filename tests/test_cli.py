import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from snap_extract.__main__ import main


class CliTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.source = self.root / "state/CollectionState.json"
        self.source.parent.mkdir()
        self.source.write_text(json.dumps({"ServerState": {"Cards": [{"CardDefId": "A"}]}}), encoding="utf-8")
        self.catalog = {"cards": {"A": {"card_id": "A", "name": "Alpha", "cost": 1,
                                      "power": 2, "ability": "No ability."}}}

    def run_cli(self, *args):
        with patch("sys.argv", ["snap-extract", "--collection", str(self.source), *args]), \
                patch("snap_extract.__main__.load_catalog", return_value=self.catalog), \
                patch("snap_extract.__main__.refresh_catalog", side_effect=AssertionError("Unexpected network")), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return main()

    def test_existing_export_requires_force(self):
        output = self.root / "cards.json"
        output.write_text("original", encoding="utf-8")
        self.assertEqual(self.run_cli("--export", str(output), "--format", "json"), 1)
        self.assertEqual(output.read_text(), "original")
        self.assertEqual(self.run_cli("--export", str(output), "--format", "json", "--force"), 0)
        self.assertEqual(json.loads(output.read_text())[0]["name"], "Alpha")

    def test_export_options_without_destination_rejected(self):
        with self.assertRaises(SystemExit) as error:
            self.run_cli("--search", "Alpha")
        self.assertEqual(error.exception.code, 2)

    def test_collection_override_forwarded_to_gui(self):
        with patch("snap_extract.gui.main") as gui:
            self.assertEqual(self.run_cli(), 0)
            gui.assert_called_once_with(collection_path=self.source)

    def test_invalid_columns_and_empty_filters_do_not_write(self):
        output = self.root / "cards.csv"
        self.assertEqual(self.run_cli("--export", str(output), "--columns", "name,name"), 1)
        self.assertEqual(self.run_cli("--export", str(output), "--search", "absent"), 1)
        self.assertFalse(output.exists())

    def test_force_cannot_overwrite_collection(self):
        before = self.source.read_bytes()
        self.assertEqual(self.run_cli("--export", str(self.source), "--force"), 1)
        self.assertEqual(self.source.read_bytes(), before)

    def test_file_created_during_loading_is_not_overwritten(self):
        output = self.root / "concurrent.json"

        def render(*args):
            output.write_text("another process wrote this", encoding="utf-8")
            return "[]"

        with patch("snap_extract.__main__.render_export", side_effect=render):
            self.assertEqual(self.run_cli("--export", str(output), "--format", "json"), 1)
        self.assertEqual(output.read_text(), "another process wrote this")
