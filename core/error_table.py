"""
Módulo ErrorTable del compilador traductor Inglés-Español.
Centraliza y gestiona los errores producidos por las tres fases del análisis:
  Fase 1 → LEXICO   (palabras no reconocidas)
  Fase 2 → SINTACTICO (estructura gramatical inválida)
  Fase 3 → SEMANTICO  (incoherencias de significado)
"""

try:
    from token_types import CompilerError, ErrorTipo
except ImportError:
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from token_types import CompilerError, ErrorTipo


class ErrorTable:
    """
    Tabla centralizada de errores del compilador.
    Acumula CompilerError de cualquier fase y ofrece consultas por tipo.
    """

    def __init__(self) -> None:
        self._errores: list[CompilerError] = []

    # ── Inserción ────────────────────────────────────────────────────────────

    def agregar(self, error: CompilerError) -> None:
        """Agrega un único CompilerError a la tabla."""
        if not isinstance(error, CompilerError):
            raise TypeError(f"Se esperaba CompilerError, se recibió {type(error).__name__}.")
        self._errores.append(error)

    def agregar_lista(self, errores: list[CompilerError]) -> None:
        """Agrega una lista de CompilerError a la tabla."""
        for error in errores:
            self.agregar(error)

    # ── Consultas booleanas ───────────────────────────────────────────────────

    def hay_errores(self) -> bool:
        """Retorna True si la tabla contiene al menos un error."""
        return len(self._errores) > 0

    def hay_errores_de(self, tipo: ErrorTipo) -> bool:
        """Retorna True si existe al menos un error del tipo indicado."""
        return any(e.tipo == tipo for e in self._errores)

    # ── Recuperación ─────────────────────────────────────────────────────────

    def obtener_todos(self) -> list[CompilerError]:
        """Retorna todos los errores en orden de inserción."""
        return list(self._errores)

    def obtener_por_tipo(self, tipo: ErrorTipo) -> list[CompilerError]:
        """Retorna solo los errores del tipo indicado."""
        return [e for e in self._errores if e.tipo == tipo]

    # ── Conteo y resumen ──────────────────────────────────────────────────────

    def total(self) -> int:
        """Retorna el número total de errores registrados."""
        return len(self._errores)

    def resumen(self) -> dict:
        """
        Retorna un diccionario con el conteo por fase.
        Claves: total, lexicos, sintacticos, semanticos.
        """
        return {
            'total':       len(self._errores),
            'lexicos':     sum(1 for e in self._errores if e.tipo == ErrorTipo.LEXICO),
            'sintacticos': sum(1 for e in self._errores if e.tipo == ErrorTipo.SINTACTICO),
            'semanticos':  sum(1 for e in self._errores if e.tipo == ErrorTipo.SEMANTICO),
        }

    # ── Limpieza ──────────────────────────────────────────────────────────────

    def limpiar(self) -> None:
        """Elimina todos los errores de la tabla."""
        self._errores.clear()

    # ── Serialización ────────────────────────────────────────────────────────

    def to_list(self) -> list[dict]:
        """Retorna todos los errores como lista de diccionarios (via .to_dict())."""
        return [e.to_dict() for e in self._errores]

    # ── Presentación ─────────────────────────────────────────────────────────

    def imprimir(self) -> None:
        """Imprime la tabla de errores formateada en consola."""
        if not self._errores:
            print("  (sin errores registrados)")
            return

        ancho = 72
        print("┌" + "─" * ancho + "┐")
        print(f"│{'  TABLA DE ERRORES':^{ancho}}│")
        print("├" + "─" * 5 + "┬" + "─" * 10 + "┬" + "─" * 6 + "┬" + "─" * (ancho - 24) + "┤")
        print(f"│{'#':^5}│{'  Tipo':<10}│{'  pos':^6}│  {'Palabra / Descripción':<{ancho - 26}}│")
        print("├" + "─" * 5 + "┼" + "─" * 10 + "┼" + "─" * 6 + "┼" + "─" * (ancho - 24) + "┤")

        for n, err in enumerate(self._errores, 1):
            tipo_str   = f"  {err.tipo.name}"
            pos_str    = f" {err.posicion:>4}"
            desc_corta = f"'{err.palabra}' — {err.descripcion}"
            # Truncar descripción si excede el ancho de columna
            col_ancho = ancho - 26
            if len(desc_corta) > col_ancho:
                desc_corta = desc_corta[:col_ancho - 1] + "…"
            print(f"│{n:^5}│{tipo_str:<10}│{pos_str:^6}│  {desc_corta:<{col_ancho}}│")
            if err.sugerencia:
                sug = f"↳ {err.sugerencia}"
                if len(sug) > col_ancho:
                    sug = sug[:col_ancho - 1] + "…"
                print(f"│{'':5}│{'':10}│{'':6}│  {sug:<{col_ancho}}│")

        print("└" + "─" * 5 + "┴" + "─" * 10 + "┴" + "─" * 6 + "┴" + "─" * (ancho - 24) + "┘")

        res = self.resumen()
        print(
            f"  Total: {res['total']}  |  "
            f"Léxicos: {res['lexicos']}  |  "
            f"Sintácticos: {res['sintacticos']}  |  "
            f"Semánticos: {res['semanticos']}"
        )

    def __len__(self) -> int:
        return len(self._errores)

    def __repr__(self) -> str:
        r = self.resumen()
        return (
            f"ErrorTable(total={r['total']}, léxicos={r['lexicos']}, "
            f"sintácticos={r['sintacticos']}, semánticos={r['semanticos']})"
        )


# ── Bloque de prueba ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    tabla = ErrorTable()

    # Crear un error de cada tipo
    e1 = CompilerError(
        tipo=ErrorTipo.LEXICO,
        posicion=4,
        palabra="xlerp",
        descripcion="'xlerp' no se encontró en el léxico EN.",
        sugerencia="Verifique la ortografía o amplíe el diccionario.",
    )
    e2 = CompilerError(
        tipo=ErrorTipo.SINTACTICO,
        posicion=12,
        palabra="jumps",
        descripcion="Se esperaba un sustantivo después del artículo.",
        sugerencia="Revise el orden de los constituyentes de la oración.",
    )
    e3 = CompilerError(
        tipo=ErrorTipo.SEMANTICO,
        posicion=20,
        palabra="colorless",
        descripcion="El adjetivo 'colorless' es semánticamente incompatible con el sustantivo.",
        sugerencia="Use un adjetivo que sea compatible con ideas concretas.",
    )

    print("=" * 74)
    print("  PRUEBA DEL MÓDULO core/error_table.py")
    print("=" * 74)

    # agregar() y agregar_lista()
    tabla.agregar(e1)
    tabla.agregar_lista([e2, e3])
    print(f"\n  repr       : {tabla!r}")

    # hay_errores() y hay_errores_de()
    print(f"\n  hay_errores()                         → {tabla.hay_errores()}")
    print(f"  hay_errores_de(LEXICO)                → {tabla.hay_errores_de(ErrorTipo.LEXICO)}")
    print(f"  hay_errores_de(SEMANTICO)             → {tabla.hay_errores_de(ErrorTipo.SEMANTICO)}")

    # total() y resumen()
    print(f"\n  total()                               → {tabla.total()}")
    print(f"  resumen()                             → {tabla.resumen()}")

    # obtener_por_tipo()
    lexico_list = tabla.obtener_por_tipo(ErrorTipo.LEXICO)
    print(f"\n  obtener_por_tipo(LEXICO) [{len(lexico_list)} error/es]:")
    for err in lexico_list:
        print(f"    {err}")

    # to_list()
    print(f"\n  to_list()[0] → {tabla.to_list()[0]}")

    # imprimir()
    print()
    tabla.imprimir()

    # limpiar()
    tabla.limpiar()
    print(f"\n  Tras limpiar():  hay_errores() → {tabla.hay_errores()}  |  total() → {tabla.total()}")
    print("=" * 74)
