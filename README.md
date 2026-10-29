# invoice-to-sheet

Saca los números de las facturas en PDF a una hoja de cálculo lista para que el técnico la revise: proveedor, NIF, número, fecha, base, tipo de IVA, cuota, retención si la hay y total. Cada factura es una fila que acaba en **OK** o en **REVISAR**, y cuando es REVISAR, la fila dice por qué.

## Qué hace

Le das una carpeta con facturas en PDF y te devuelve la hoja en dos formatos, CSV y Excel. Antes de escribir cada fila comprueba cinco cosas:

1. Que el NIF del proveedor tenga bien la letra o el dígito de control. Una errata al copiarlo salta aquí.
2. Que la base por el tipo de IVA dé la cuota que pone la factura, al céntimo.
3. Que la base más el IVA, menos la retención, dé el total.
4. Que la fecha exista. Un 30 de febrero no pasa.
5. Que no haya dos facturas con el mismo NIF y el mismo número. La primera se queda como está y la repetida va a REVISAR.

Si a una factura le falta un dato, su casilla se queda vacía y el motivo lo dice («falta la fecha»). Nunca rellena un hueco con lo que le parece.

Con las mismas facturas sale siempre la misma hoja, idéntica hasta la última letra, hoy y dentro de un año.

## Qué no hace

- Facturas escaneadas o fotos, no. El PDF tiene que llevar el texto dentro: si puedes seleccionar las palabras con el ratón, vale. Si le llega un escaneado, lo marca y no lee nada.
- Solo lee los datos que van al lado de su nombre de siempre: «Base imponible», «IVA 21 %», «Retención 19 %», «Total factura», «NIF emisor», «Número de factura», «Fecha de factura». Una factura con otro diseño puede quedarse con casillas vacías, y entonces lo dice.
- Un solo tipo de IVA por factura. Si trae dos, por ejemplo 21 % y 10 %, la manda a REVISAR.
- Tampoco contabiliza ni presenta nada a Hacienda. Del NIF mira que esté bien escrito, pero no si la empresa existe en el censo.

## Por qué reglas fijas y no IA

Porque con el mismo PDF tiene que salir siempre lo mismo. Una IA puede leer mejor una factura rara, pero a veces completa el dato que falta con uno que suena bien, y en una factura ese error pasa sin que nadie lo vea. Aquí cada comprobación es una cuenta que el técnico puede repetir con la calculadora, y cuando algo no cuadra la fila lo dice con los dos números delante.

## Las facturas de ejemplo

En [`samples/`](samples/) hay 12 facturas inventadas. Cinco están bien y siete llevan un fallo puesto adrede, para ver cómo lo caza:

| Factura | Qué tiene | Qué sale |
|---|---|---|
| factura-01 | Papelería, IVA al 21 % | OK |
| factura-02 | Restaurante, IVA al 10 % | OK |
| factura-03 | Librería, IVA al 4 % | OK |
| factura-04 | Alquiler de local, IVA al 21 % y retención del 19 % | OK |
| factura-05 | Transportes, importe con miles | OK |
| factura-06 | La cuota de IVA no es el 21 % de la base | REVISAR |
| factura-07 | El CIF tiene el dígito de control cambiado | REVISAR |
| factura-08 | No lleva fecha | REVISAR |
| factura-09 | Repite proveedor y número de la factura-02 | REVISAR |
| factura-10 | El total no es la base más el IVA | REVISAR |
| factura-11 | Fecha del 30 de febrero | REVISAR |
| factura-12 | La retención no es el 19 % de la base | REVISAR |

La hoja que sale de esas 12 está en [`demo/facturas.csv`](demo/facturas.csv) (GitHub la enseña como tabla) y en [`demo/facturas.xlsx`](demo/facturas.xlsx).

**Todo es inventado.** Los nombres de empresa se ven ficticios a primera vista (Papelería Inventada, Transportes de Mentira), la dirección es «Calle Inventada 1, 00000 Ciudad de Ejemplo» y ningún código postal de España empieza por 00. Los NIF son CIF de sociedad hechos a mano con la misma forma en todos: la letra, luego 00, luego un número de serie corto (00001, 00002...) y el carácter de control calculado con la regla oficial, para que la herramienta los dé por buenos (menos el de la factura-07, que lo trae mal adrede). Esa forma tan repetitiva los aleja de los NIF reales, pero no los hemos cotejado con el censo de Hacienda, así que no podemos garantizar que ninguno coincida con el de una empresa existente. Si coincidiera, sería casualidad: ninguna de estas facturas tiene nada que ver con ella.

## Cómo se usa

Probado con Python 3.14 en macOS y en Ubuntu (el de GitHub Actions).

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m invoice_to_sheet carpeta-con-facturas -o out
```

Escribe `out/facturas.csv` y `out/facturas.xlsx` y dice cuántas han salido OK y cuántas a REVISAR. Las columnas son: Archivo, Proveedor, NIF, Número, Fecha, Base, Tipo IVA, Cuota IVA, Tipo retención, Retención, Total, Estado y Motivo. Si una factura tiene varios problemas, el motivo los lista separados por punto y coma.

- **CSV**: separado por `;`, céntimos con coma (`1240,00`) y UTF-8 con BOM, para que Excel en español lo abra tal cual.
- **XLSX**: importes como números con dos decimales, fechas como fechas y las filas a REVISAR en color. El zip se reescribe con fecha fija y sin comprimir, para que dos ejecuciones den el mismo fichero byte a byte.

Las dependencias van fijadas a una versión exacta en `requirements.txt` (`pypdf` para leer el texto del PDF y `openpyxl` para el Excel): con otra versión de `pypdf` el texto extraído podría cambiar, y con él la hoja.

### Las pruebas

```sh
pip install -r requirements-dev.txt
python -m pytest
```

Son 44 y comprueban tres cosas: que cada factura mala sale en REVISAR con su motivo exacto y las buenas en OK con todos los datos, que dos ejecuciones dan la misma hoja byte a byte y la misma que hay en `demo/`, y que las reglas sueltas (control del NIF, NIE y CIF, redondeo al céntimo, fechas imposibles) aciertan y fallan donde toca. Corren solas en cada push con GitHub Actions (`.github/workflows/tests.yml`).

Las facturas de ejemplo se regeneran con `python tools/make_samples.py`, que usa `fpdf2` y siempre da los mismos PDF.

### Rómpelo tú

Una prueba que no puede fallar no prueba nada. Para ver que estas sí:

1. Abre `invoice_to_sheet/invoice.py` y busca la línea que mira el IVA:
   ```python
   if problem := rules.vat_problem(row.base, row.vat_rate, row.vat):
   ```
2. Cámbiala por `if problem := None:` (así ya no compara la cuota con la base).
3. `python -m pytest`: fallan 2. La factura-06 sale OK cuando debía salir REVISAR, y la hoja ya no coincide con `demo/`.
4. `git checkout invoice_to_sheet/invoice.py` y vuelve a pasar todo.

Lo mismo con cualquier otra regla: quita la llamada a `mark_duplicates(rows)` en `process()` y cae la prueba de la factura-09.

### Dónde está cada cosa

| Ruta | Qué es |
|---|---|
| `invoice_to_sheet/rules.py` | Las reglas: control del NIF, NIE y CIF, importes, fechas, IVA, retención y total |
| `invoice_to_sheet/invoice.py` | Lee cada PDF por sus etiquetas, aplica las reglas y marca las repetidas |
| `invoice_to_sheet/sheet.py` | Escribe el CSV y el XLSX de forma que salgan siempre iguales |
| `invoice_to_sheet/cli.py` | La orden `python -m invoice_to_sheet` |
| `tools/make_samples.py` | Genera las facturas inventadas de `samples/` |
| `tests/` | Las pruebas |

## Licencia

MIT, Marc Peña 2026. Ver [`LICENSE`](LICENSE).

## Quién lo ha hecho

Marc Peña, consultor de automatización en Barcelona para gestorías, asesorías y pequeños negocios. Lo que hace está en [marcpenya.com](https://marcpenya.com), y lo que hace para gestorías, en [marcpenya.com/gestorias](https://marcpenya.com/gestorias/).
