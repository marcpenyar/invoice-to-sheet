"""Read one invoice PDF into a row, then run the fixed rules over all rows.

The reader only takes values that sit next to a label it knows ("Base imponible",
"IVA 21 %", "Total factura"...). If a label is not there, the field stays empty and
the row says what is missing. It never guesses a value from the rest of the page.
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from pypdf import PdfReader

from . import rules

AMOUNT = r"(-?\d{1,3}(?:\.\d{3})+,\d{2}|-?\d+,\d{2})\s*(?:€|EUR)?"
RATE = r"(\d{1,2}(?:[.,]\d{1,2})?)\s*%"

LABELS = {
    "supplier": re.compile(r"^\s*(?:Emisor|Proveedor)\s*:\s*(.+?)\s*$", re.I | re.M),
    "nif": re.compile(r"^\s*(?:NIF|CIF)\s+(?:del\s+)?(?:emisor|proveedor)\s*:\s*([A-Za-z0-9 .\-]+?)\s*$", re.I | re.M),
    "number": re.compile(r"^\s*(?:N[úu]mero de factura|Factura\s+n[º°o]\.?)\s*:?\s*(\S+)\s*$", re.I | re.M),
    "date": re.compile(r"^\s*Fecha(?:\s+de\s+(?:factura|emisi[óo]n))?\s*:\s*(\S+)\s*$", re.I | re.M),
    "base": re.compile(rf"^\s*Base imponible\s*:?\s*{AMOUNT}\s*$", re.I | re.M),
    "vat": re.compile(rf"^\s*(?:Cuota\s+)?IVA\s*(?:al\s+)?{RATE}\s*:?\s*{AMOUNT}\s*$", re.I | re.M),
    "withholding": re.compile(rf"^\s*Retenci[óo]n(?:\s+IRPF)?\s*{RATE}\s*:?\s*{AMOUNT}\s*$", re.I | re.M),
    "total": re.compile(rf"^\s*Total(?:\s+factura|\s+a\s+pagar)?\s*:?\s*{AMOUNT}\s*$", re.I | re.M),
}

COLUMNS = [
    ("file", "Archivo"),
    ("supplier", "Proveedor"),
    ("nif", "NIF"),
    ("number", "Número"),
    ("date", "Fecha"),
    ("base", "Base"),
    ("vat_rate", "Tipo IVA"),
    ("vat", "Cuota IVA"),
    ("wh_rate", "Tipo retención"),
    ("withholding", "Retención"),
    ("total", "Total"),
    ("status", "Estado"),
    ("reasons", "Motivo"),
]


@dataclass
class Row:
    file: str
    supplier: str | None = None
    nif: str | None = None
    number: str | None = None
    date: dt.date | None = None
    base: Decimal | None = None
    vat_rate: Decimal | None = None
    vat: Decimal | None = None
    wh_rate: Decimal | None = None
    withholding: Decimal | None = None
    total: Decimal | None = None
    problems: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        return "REVISAR" if self.problems else "OK"

    @property
    def reasons(self) -> str:
        return "; ".join(self.problems)


def pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def read_invoice(path: Path) -> Row:
    """Fill a Row from the labelled values in the PDF. Missing stays None."""
    row = Row(file=path.name)
    text = pdf_text(path)
    if not text.strip():
        row.problems.append("el PDF no tiene texto (puede ser un escaneado): no se ha leído nada")
        return row

    if m := LABELS["supplier"].search(text):
        row.supplier = m.group(1)
    if m := LABELS["nif"].search(text):
        row.nif = rules.normalize_nif(m.group(1))
    if m := LABELS["number"].search(text):
        row.number = m.group(1)
    if m := LABELS["date"].search(text):
        row.date = rules.parse_date(m.group(1))
        if row.date is None:
            row.problems.append(f"fecha imposible o mal escrita: {m.group(1)}")
    if m := LABELS["base"].search(text):
        row.base = rules.parse_amount(m.group(1))
    vat_lines = LABELS["vat"].findall(text)
    if len({rate for rate, _ in vat_lines}) > 1:
        row.problems.append("varios tipos de IVA en la misma factura: esta versión solo lee uno")
    elif vat_lines:
        row.vat_rate = rules.parse_rate(vat_lines[0][0])
        row.vat = rules.parse_amount(vat_lines[0][1])
    if m := LABELS["withholding"].search(text):
        row.wh_rate = rules.parse_rate(m.group(1))
        row.withholding = abs(rules.parse_amount(m.group(2)))
    if m := LABELS["total"].search(text):
        row.total = rules.parse_amount(m.group(1))
    return row


MISSING = [
    ("supplier", "falta el proveedor"),
    ("nif", "falta el NIF del proveedor"),
    ("number", "falta el número de factura"),
    ("base", "falta la base imponible"),
    ("vat_rate", "falta el tipo de IVA"),
    ("vat", "falta la cuota de IVA"),
    ("total", "falta el total"),
]


def check(row: Row) -> None:
    """Apply the fixed rules to one row. Adds a reason per broken rule."""
    if any(p.startswith("el PDF no tiene texto") for p in row.problems):
        return
    several_rates = any(p.startswith("varios tipos de IVA") for p in row.problems)
    for attr, reason in MISSING:
        if several_rates and attr in ("vat_rate", "vat"):
            continue
        if getattr(row, attr) is None:
            row.problems.append(reason)
    if row.date is None and not any(p.startswith("fecha") for p in row.problems):
        row.problems.append("falta la fecha")

    if row.nif is not None and (problem := rules.nif_problem(row.nif)):
        row.problems.append(problem)
    if None not in (row.base, row.vat_rate, row.vat):
        if problem := rules.vat_problem(row.base, row.vat_rate, row.vat):
            row.problems.append(problem)
    if None not in (row.base, row.wh_rate, row.withholding):
        if problem := rules.withholding_problem(row.base, row.wh_rate, row.withholding):
            row.problems.append(problem)
    if None not in (row.base, row.vat, row.total):
        withholding = row.withholding if row.withholding is not None else Decimal("0.00")
        if problem := rules.total_problem(row.base, row.vat, withholding, row.total):
            row.problems.append(problem)


def mark_duplicates(rows: list[Row]) -> None:
    """Same supplier NIF and same invoice number: every copy after the first goes to review."""
    seen: dict[tuple[str, str], str] = {}
    for row in rows:
        if row.nif is None or row.number is None:
            continue
        key = (row.nif, row.number)
        if key in seen:
            row.problems.append(f"repetida: mismo NIF y número que {seen[key]}")
        else:
            seen[key] = row.file


def process(folder: Path) -> list[Row]:
    """Read every PDF in the folder, in name order, and run all the rules."""
    paths = sorted(p for p in folder.iterdir() if p.suffix.lower() == ".pdf")
    rows = [read_invoice(p) for p in paths]
    for row in rows:
        check(row)
    mark_duplicates(rows)
    return rows
