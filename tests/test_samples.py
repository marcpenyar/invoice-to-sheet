"""Every sample invoice ends in the state it was made for, with its reason."""
from pathlib import Path

import pytest

from invoice_to_sheet.invoice import process

SAMPLES = Path(__file__).resolve().parent.parent / "samples"

GOOD = ["factura-01.pdf", "factura-02.pdf", "factura-03.pdf", "factura-04.pdf", "factura-05.pdf"]

# file -> the reason it must give (start of the text), and only that one.
BAD = {
    "factura-06.pdf": "la cuota de IVA no cuadra: 500,00 al 21 % son 105,00 y la factura dice 100,00",
    "factura-07.pdf": "CIF con el dígito de control mal (B00000076)",
    "factura-08.pdf": "falta la fecha",
    "factura-09.pdf": "repetida: mismo NIF y número que factura-02.pdf",
    "factura-10.pdf": "el total no cuadra: base más IVA menos retención dan 508,20 y la factura dice 518,20",
    "factura-11.pdf": "fecha imposible o mal escrita: 30/02/2026",
    "factura-12.pdf": "la retención no cuadra: 950,00 al 19 % son 180,50 y la factura dice 171,00",
}


@pytest.fixture(scope="module")
def rows():
    return {row.file: row for row in process(SAMPLES)}


def test_every_sample_is_covered(rows):
    assert sorted(rows) == sorted(GOOD + list(BAD))


@pytest.mark.parametrize("name", GOOD)
def test_good_invoice_is_ok_and_complete(rows, name):
    row = rows[name]
    assert row.status == "OK", row.reasons
    assert row.reasons == ""
    for attr in ("supplier", "nif", "number", "date", "base", "vat_rate", "vat", "total"):
        assert getattr(row, attr) is not None, f"{name}: {attr} vacío"


@pytest.mark.parametrize("name,reason", sorted(BAD.items()))
def test_bad_invoice_goes_to_review_with_its_reason(rows, name, reason):
    row = rows[name]
    assert row.status == "REVISAR"
    assert row.problems == [reason]


def test_missing_date_stays_empty(rows):
    assert rows["factura-08.pdf"].date is None
    assert rows["factura-11.pdf"].date is None


def test_withholding_is_read(rows):
    row = rows["factura-04.pdf"]
    assert (str(row.wh_rate), str(row.withholding), str(row.total)) == ("19", "180.50", "969.00")


def test_rate_ten_is_written_as_ten(rows):
    assert str(rows["factura-02.pdf"].vat_rate) == "10"
