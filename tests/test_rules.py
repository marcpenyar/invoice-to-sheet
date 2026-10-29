"""The fixed rules on their own, with values small enough to check by hand."""
import datetime as dt
from decimal import Decimal
from pathlib import Path

import pytest

from invoice_to_sheet import rules
from invoice_to_sheet.invoice import Row, check, read_invoice


@pytest.mark.parametrize("nif", ["00000000T", "X0000000T", "B00000018", "A00000034", "Q0000000J"])
def test_valid_check_characters(nif):
    assert rules.nif_problem(nif) is None


@pytest.mark.parametrize("nif,start", [
    ("00000000A", "NIF con la letra de control mal"),
    ("X0000000A", "NIE con la letra de control mal"),
    ("B00000019", "CIF con el dígito de control mal"),
    ("Q00000000", "CIF con el dígito de control mal"),
    ("1234", "NIF con un formato"),
])
def test_wrong_check_characters(nif, start):
    assert rules.nif_problem(nif).startswith(start)


def test_nif_is_normalized():
    assert rules.normalize_nif(" es-b0000.0018 ") == "B00000018"


@pytest.mark.parametrize("text,value", [
    ("1.240,00 €", "1240.00"), ("-180,50 €", "-180.50"), ("86,36", "86.36"), ("12.345.678,90", "12345678.90"),
])
def test_amounts(text, value):
    assert rules.parse_amount(text) == Decimal(value)


@pytest.mark.parametrize("text,expected", [
    ("12/01/2026", dt.date(2026, 1, 12)), ("29/02/2028", dt.date(2028, 2, 29)),
    ("30/02/2026", None), ("29/02/2026", None), ("2026-01-12", None), ("", None),
])
def test_dates(text, expected):
    assert rules.parse_date(text) == expected


def test_vat_rounds_half_up_to_the_cent():
    # 86,36 x 10 % = 8,636 -> 8,64; one cent off is already wrong
    assert rules.vat_problem(Decimal("86.36"), Decimal("10"), Decimal("8.64")) is None
    assert rules.vat_problem(Decimal("86.36"), Decimal("10"), Decimal("8.63")) is not None


def test_total_takes_withholding_off():
    assert rules.total_problem(Decimal("950.00"), Decimal("199.50"), Decimal("180.50"), Decimal("969.00")) is None
    assert rules.total_problem(Decimal("950.00"), Decimal("199.50"), Decimal("0.00"), Decimal("969.00")) is not None


def test_empty_row_lists_everything_missing_and_invents_nothing():
    row = Row(file="vacia.pdf")
    check(row)
    assert row.status == "REVISAR"
    assert row.problems == [
        "falta el proveedor", "falta el NIF del proveedor", "falta el número de factura",
        "falta la base imponible", "falta el tipo de IVA", "falta la cuota de IVA",
        "falta el total", "falta la fecha",
    ]
    assert all(getattr(row, a) is None for a in ("supplier", "nif", "number", "date", "base", "vat", "total"))


def test_pdf_without_text_is_flagged(tmp_path: Path):
    from fpdf import FPDF  # in requirements-dev.txt: missing it is a failure, not a skip

    pdf = FPDF()
    pdf.add_page()
    pdf.rect(10, 10, 50, 50)  # a page with a drawing and no text, like a scan
    path = tmp_path / "escaneada.pdf"
    pdf.output(str(path))
    row = read_invoice(path)
    check(row)
    assert row.problems == ["el PDF no tiene texto (puede ser un escaneado): no se ha leído nada"]
