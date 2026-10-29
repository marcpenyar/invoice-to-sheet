"""Same PDFs, same sheet, byte for byte: twice in a row and against the committed demo."""
import subprocess
import sys
from pathlib import Path

from invoice_to_sheet.cli import main
from invoice_to_sheet.invoice import process

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "samples"
DEMO = ROOT / "demo"


def run(out: Path) -> dict[str, bytes]:
    assert main([str(SAMPLES), "-o", str(out)]) == 0
    return {name: (out / name).read_bytes() for name in ("facturas.csv", "facturas.xlsx")}


def test_two_runs_give_identical_files(tmp_path):
    first = run(tmp_path / "a")
    second = run(tmp_path / "b")
    assert first == second


def test_output_matches_the_committed_demo(tmp_path):
    produced = run(tmp_path / "out")
    for name, content in produced.items():
        assert content == (DEMO / name).read_bytes(), f"{name} no coincide con demo/{name}"


def test_sample_generator_is_repeatable(tmp_path):
    for folder in ("a", "b"):
        subprocess.run([sys.executable, str(ROOT / "tools" / "make_samples.py"), str(tmp_path / folder)],
                       check=True, capture_output=True)
    names = sorted(p.name for p in (tmp_path / "a").iterdir())
    assert names == sorted(p.name for p in SAMPLES.glob("*.pdf"))
    for name in names:
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes(), name
    # and the regenerated invoices read exactly like the committed ones
    fresh = [(r.file, r.status, r.reasons, r.base, r.vat, r.total) for r in process(tmp_path / "a")]
    committed = [(r.file, r.status, r.reasons, r.base, r.vat, r.total) for r in process(SAMPLES)]
    assert fresh == committed
