"""Generate the made-up sample invoices in samples/.

Every company, address and NIF here is invented. The NIFs are company CIFs built
as letter + 00 + a five digit serial + the check character our own rules compute,
so they pass (or, on purpose, fail) the check digit without being anyone's.
Postal code 00000 does not exist in Spain.

Run: python tools/make_samples.py [output folder]   (default: samples)
"""
from __future__ import annotations

import datetime as dt
import sys
from decimal import Decimal
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import XPos, YPos

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from invoice_to_sheet import rules  # noqa: E402

FIXED_DATE = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)


def cif(letter: str, serial: int, broken: bool = False) -> str:
    """Invented CIF: letter + '00' + serial, with a valid check char unless broken."""
    digits = f"00{serial:05d}"
    digit, control_letter = rules.cif_control(letter, digits)
    control = control_letter if letter in rules.CIF_LETTER_CONTROL else digit
    if broken:
        control = str((int(control) + 1) % 10)
    return f"{letter}{digits}{control}"


CLIENT = ("Gestoría de Ejemplo S.L.", cif("B", 99))

# Each invoice: what is printed on it. Bad ones are bad on purpose (see "why").
INVOICES = [
    dict(file="factura-01.pdf", why="buena, IVA 21 %",
         supplier="Papelería Inventada S.L.", nif=cif("B", 1), number="PI-2026-0007",
         date="12/01/2026", concept="Material de oficina",
         base="184,30", rate="21", vat="38,70", total="223,00"),
    dict(file="factura-02.pdf", why="buena, IVA 10 %",
         supplier="Restaurante Ficticio Ejemplo S.L.", nif=cif("B", 2), number="R-0153",
         date="03/02/2026", concept="Comida de trabajo",
         base="86,36", rate="10", vat="8,64", total="95,00"),
    dict(file="factura-03.pdf", why="buena, IVA 4 %",
         supplier="Librería Imaginaria S.A.", nif=cif("A", 3), number="L-2026/044",
         date="17/02/2026", concept="Libros técnicos",
         base="57,69", rate="4", vat="2,31", total="60,00"),
    dict(file="factura-04.pdf", why="buena, alquiler con retención del 19 %",
         supplier="Locales Inventados S.L.", nif=cif("B", 4), number="ALQ-2026-03",
         date="01/03/2026", concept="Alquiler del local, marzo",
         base="950,00", rate="21", vat="199,50", wh_rate="19", wh="180,50", total="969,00"),
    dict(file="factura-05.pdf", why="buena, importe con miles",
         supplier="Transportes de Mentira S.A.", nif=cif("A", 5), number="TM-88412",
         date="20/03/2026", concept="Portes de marzo",
         base="1.240,00", rate="21", vat="260,40", total="1.500,40"),
    dict(file="factura-06.pdf", why="mala: la cuota de IVA no es el 21 % de la base",
         supplier="Reformas Ficticias S.L.", nif=cif("B", 6), number="RF-0031",
         date="02/04/2026", concept="Pintura de la oficina",
         base="500,00", rate="21", vat="100,00", total="600,00"),
    dict(file="factura-07.pdf", why="mala: el CIF tiene el dígito de control cambiado",
         supplier="Limpiezas Imaginarias S.L.", nif=cif("B", 7, broken=True), number="LIM-112",
         date="15/04/2026", concept="Limpieza de abril",
         base="300,00", rate="21", vat="63,00", total="363,00"),
    dict(file="factura-08.pdf", why="mala: no lleva fecha",
         supplier="Consultora Inventada S.L.", nif=cif("B", 8), number="CI-2026-019",
         date=None, concept="Asesoramiento",
         base="1.000,00", rate="21", vat="210,00", total="1.210,00"),
    dict(file="factura-09.pdf", why="mala: repite proveedor y número de factura-02",
         supplier="Restaurante Ficticio Ejemplo S.L.", nif=cif("B", 2), number="R-0153",
         date="03/02/2026", concept="Comida de trabajo",
         base="86,36", rate="10", vat="8,64", total="95,00"),
    dict(file="factura-10.pdf", why="mala: el total no es base más IVA",
         supplier="Imprenta de Ejemplo S.L.", nif=cif("B", 10), number="IE-0450",
         date="05/05/2026", concept="Tarjetas de visita",
         base="420,00", rate="21", vat="88,20", total="518,20"),
    dict(file="factura-11.pdf", why="mala: el 30 de febrero no existe",
         supplier="Mensajería Ficticia S.L.", nif=cif("B", 11), number="MF-7781",
         date="30/02/2026", concept="Envío urgente",
         base="45,00", rate="21", vat="9,45", total="54,45"),
    dict(file="factura-12.pdf", why="mala: la retención no es el 19 % de la base",
         supplier="Locales Inventados S.L.", nif=cif("B", 4), number="ALQ-2026-04",
         date="01/04/2026", concept="Alquiler del local, abril",
         base="950,00", rate="21", vat="199,50", wh_rate="19", wh="171,00", total="978,50"),
]


def money(text: str) -> str:
    return f"{text} €"


def render(inv: dict, path: Path) -> None:
    pdf = FPDF(format="A4")
    pdf.core_fonts_encoding = "windows-1252"  # Helvetica with the euro sign
    pdf.set_creation_date(FIXED_DATE)
    pdf.set_title(f"Factura {inv['number']}")
    pdf.set_author("invoice-to-sheet (datos inventados)")
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, "FACTURA", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 11)

    def line(text: str) -> None:
        pdf.cell(0, 7, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    line(f"Emisor: {inv['supplier']}")
    line(f"NIF emisor: {inv['nif']}")
    line("Calle Inventada 1, 00000 Ciudad de Ejemplo")
    pdf.ln(4)
    line(f"Cliente: {CLIENT[0]}")
    line(f"NIF cliente: {CLIENT[1]}")
    pdf.ln(4)
    line(f"Número de factura: {inv['number']}")
    if inv["date"] is not None:
        line(f"Fecha de factura: {inv['date']}")
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(130, 8, "Concepto", border="B")
    pdf.cell(50, 8, "Importe", border="B", align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(130, 8, inv["concept"])
    pdf.cell(50, 8, money(inv["base"]), align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(6)

    def total_line(label: str, value: str, bold: bool = False) -> None:
        pdf.set_font("Helvetica", "B" if bold else "", 11)
        pdf.cell(130, 7, label)
        pdf.cell(50, 7, value, align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    total_line("Base imponible:", money(inv["base"]))
    total_line(f"IVA {inv['rate']} %:", money(inv["vat"]))
    if "wh" in inv:
        total_line(f"Retención {inv['wh_rate']} %:", money("-" + inv["wh"]))
    total_line("Total factura:", money(inv["total"]), bold=True)

    pdf.ln(14)
    pdf.set_font("Helvetica", "I", 8)
    line("Factura inventada para probar invoice-to-sheet. Empresas, direcciones y NIF ficticios.")
    pdf.output(str(path))


def main(argv: list[str]) -> int:
    out = Path(argv[0]) if argv else Path(__file__).resolve().parent.parent / "samples"
    out.mkdir(parents=True, exist_ok=True)
    for inv in INVOICES:
        render(inv, out / inv["file"])
    print(f"{len(INVOICES)} facturas inventadas en {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
