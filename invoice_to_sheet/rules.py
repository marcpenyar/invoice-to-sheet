"""Fixed rules that decide whether an invoice row is OK or needs review.

Everything here is plain arithmetic on Decimal values: no guessing, no defaults.
A check that cannot run because a value is missing says so instead of passing.
"""
from __future__ import annotations

import datetime as dt
import re
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")

DNI_LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"
CIF_FIRST = "ABCDEFGHJKLMNPQRSUVW"
CIF_LETTER_CONTROL = "KPQRSNW"   # these entity types always end in a letter
CIF_DIGIT_CONTROL = "ABEH"       # these always end in a digit
CIF_CONTROL_LETTERS = "JABCDEFGHI"


def normalize_nif(raw: str) -> str:
    """Uppercase and drop spaces, dots, hyphens and a leading ES country prefix."""
    value = re.sub(r"[\s.\-]", "", raw.upper())
    if value.startswith("ES") and len(value) == 11:
        value = value[2:]
    return value


def cif_control(first_letter: str, seven_digits: str) -> tuple[str, str]:
    """Return the (digit, letter) pair a CIF with these 7 digits must end with."""
    digits = [int(c) for c in seven_digits]
    even = digits[1] + digits[3] + digits[5]
    odd = 0
    for d in digits[0::2]:
        doubled = d * 2
        odd += doubled // 10 + doubled % 10
    control = (10 - (even + odd) % 10) % 10
    return str(control), CIF_CONTROL_LETTERS[control]


def nif_problem(raw: str) -> str | None:
    """None if the NIF/NIE/CIF passes its check digit, else a plain-language reason."""
    nif = normalize_nif(raw)
    if re.fullmatch(r"\d{8}[A-Z]", nif):
        expected = DNI_LETTERS[int(nif[:8]) % 23]
        return None if nif[8] == expected else f"NIF con la letra de control mal ({nif})"
    if re.fullmatch(r"[XYZ]\d{7}[A-Z]", nif):
        number = int(str("XYZ".index(nif[0])) + nif[1:8])
        expected = DNI_LETTERS[number % 23]
        return None if nif[8] == expected else f"NIE con la letra de control mal ({nif})"
    if re.fullmatch(rf"[{CIF_FIRST}]\d{{7}}[0-9A-J]", nif):
        digit, letter = cif_control(nif[0], nif[1:8])
        last = nif[8]
        if nif[0] in CIF_LETTER_CONTROL:
            ok = last == letter
        elif nif[0] in CIF_DIGIT_CONTROL:
            ok = last == digit
        else:
            ok = last in (digit, letter)
        return None if ok else f"CIF con el dígito de control mal ({nif})"
    return f"NIF con un formato que no es de NIF, NIE ni CIF ({nif})"


def parse_amount(text: str) -> Decimal:
    """'1.234,56' -> Decimal('1234.56'). Spanish format only: comma for cents."""
    clean = text.replace("€", "").replace("EUR", "").strip().replace(" ", "")
    negative = clean.startswith("-")
    clean = clean.lstrip("-").replace(".", "").replace(",", ".")
    value = Decimal(clean).quantize(CENT)
    return -value if negative else value


def parse_rate(text: str) -> Decimal:
    """'21' -> Decimal('21'), '10' -> Decimal('10') (not 1E+1), '5,5' -> Decimal('5.5')."""
    value = Decimal(text.replace(",", "."))
    return value.quantize(Decimal(1)) if value == value.to_integral() else value.normalize()


def parse_date(text: str) -> dt.date | None:
    """dd/mm/yyyy (also with - or .) to a real calendar date, or None if impossible."""
    m = re.fullmatch(r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})", text.strip())
    if not m:
        return None
    day, month, year = (int(g) for g in m.groups())
    try:
        return dt.date(year, month, day)
    except ValueError:
        return None


def percent_of(base: Decimal, rate: Decimal) -> Decimal:
    """base x rate %, rounded to the cent the way invoices round (half up)."""
    return (base * rate / Decimal(100)).quantize(CENT, rounding=ROUND_HALF_UP)


def fmt(value: Decimal) -> str:
    """Decimal to the Spanish way of writing money, without thousands separator."""
    return f"{value:.2f}".replace(".", ",")


def vat_problem(base: Decimal, rate: Decimal, vat: Decimal) -> str | None:
    expected = percent_of(base, rate)
    if expected == vat:
        return None
    return (f"la cuota de IVA no cuadra: {fmt(base)} al {rate} % son {fmt(expected)} "
            f"y la factura dice {fmt(vat)}")


def withholding_problem(base: Decimal, rate: Decimal, amount: Decimal) -> str | None:
    expected = percent_of(base, rate)
    if expected == amount:
        return None
    return (f"la retención no cuadra: {fmt(base)} al {rate} % son {fmt(expected)} "
            f"y la factura dice {fmt(amount)}")


def total_problem(base: Decimal, vat: Decimal, withholding: Decimal, total: Decimal) -> str | None:
    expected = base + vat - withholding
    if expected == total:
        return None
    return (f"el total no cuadra: base más IVA menos retención dan {fmt(expected)} "
            f"y la factura dice {fmt(total)}")
