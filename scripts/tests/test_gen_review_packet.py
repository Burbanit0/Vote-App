"""The expert-review packet's generator (scripts/gen_review_packet.py). The packet is a dated
snapshot to send, named by the registry's content hash, so a registry change does not have
to regenerate it; what is checked is that the generator still reads everything it needs.

Run: python3 -m unittest discover -s scripts/tests -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gen_review_packet as grp  # noqa: E402


class ReviewPacketTest(unittest.TestCase):
    def test_the_packet_renders_with_every_label_and_source_read(self) -> None:
        # render() refuses an unlabelled rule or criterion and an unreadable source.
        packet = grp.render()
        self.assertIn("| Split Cycle |", packet)
        self.assertIn("Moulin, Hervé (1988)", packet)

    def test_bibtex_escapes_and_ranges_read_as_text(self) -> None:
        self.assertEqual(grp.latex_to_text("Moulin, Herv{\\'e}"), "Moulin, Hervé")
        self.assertEqual(grp.latex_to_text("Papers \\& Proceedings, {587--601}"), "Papers & Proceedings, 587–601")

    def test_a_table_cell_stays_on_one_line(self) -> None:
        self.assertEqual(grp.md("a |\nb"), "a \\| b")

    def test_a_missing_source_names_itself(self) -> None:
        with self.assertRaises(SystemExit):
            grp.bib_entry("nobody2099")


if __name__ == "__main__":
    unittest.main()
