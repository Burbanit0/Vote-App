"""The expert-review packet (docs/research/expert-review-packet.md) is regenerated, never
edited by hand: it must be what scripts/gen_review_packet.py writes from the registry now.

Run: python3 -m unittest discover -s scripts/tests -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gen_review_packet as grp  # noqa: E402


class ReviewPacketTest(unittest.TestCase):
    def test_the_committed_packet_is_what_the_registry_generates(self) -> None:
        self.assertEqual(
            grp.OUT.read_text(encoding="utf-8"), grp.render(),
            "the packet is stale: run python3 scripts/gen_review_packet.py and commit it",
        )

    def test_bibtex_accents_and_ranges_read_as_text(self) -> None:
        self.assertEqual(grp.latex_to_text("Moulin, Herv{\\'e}"), "Moulin, Hervé")
        self.assertEqual(grp.latex_to_text("{587--601}"), "587–601")

    def test_a_source_is_cited_from_the_bibliography(self) -> None:
        self.assertEqual(grp.cite("moulin1988"), "Moulin (1988)")
        with self.assertRaises(SystemExit):
            grp.bib_entry("nobody2099")


if __name__ == "__main__":
    unittest.main()
