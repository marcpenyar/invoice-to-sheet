"""Command line: invoice-to-sheet <folder with PDFs> [-o <output folder>]."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .invoice import process
from .sheet import write_csv, write_xlsx


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="invoice-to-sheet",
        description="Saca proveedor, NIF, número, fecha, base, IVA, retención y total "
                    "de facturas en PDF a una hoja (CSV y XLSX), con estado OK o REVISAR.",
    )
    parser.add_argument("folder", type=Path, help="carpeta con las facturas en PDF")
    parser.add_argument("-o", "--out", type=Path, default=Path("out"),
                        help="carpeta de salida (por defecto: out)")
    args = parser.parse_args(argv)

    if not args.folder.is_dir():
        print(f"No encuentro la carpeta {args.folder}", file=sys.stderr)
        return 2
    rows = process(args.folder)
    if not rows:
        print(f"No hay ningún PDF en {args.folder}", file=sys.stderr)
        return 2
    args.out.mkdir(parents=True, exist_ok=True)
    write_csv(rows, args.out / "facturas.csv")
    write_xlsx(rows, args.out / "facturas.xlsx")
    review = sum(1 for r in rows if r.problems)
    print(f"{len(rows)} facturas: {len(rows) - review} OK, {review} a REVISAR. "
          f"Hoja en {args.out / 'facturas.csv'} y {args.out / 'facturas.xlsx'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
