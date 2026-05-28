"""
Módulo SemanticAnalyzer del compilador traductor Inglés-Español.
Fase 3: análisis semántico — valida coherencia y consistencia sobre los
tokens producidos por el Lexer y el AST construido por el Parser.
"""

from __future__ import annotations

import sys
import os

try:
    from token_types import TokenType, Token, ErrorTipo, CompilerError
    from error_table import ErrorTable
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from token_types import TokenType, Token, ErrorTipo, CompilerError
    from error_table import ErrorTable


# ── Conjuntos de tipos auxiliares ────────────────────────────────────────────

_TIPOS_VERBO: frozenset[TokenType] = frozenset({
    TokenType.VERBO, TokenType.VERBO_AUX, TokenType.VERBO_INF,
})

# Tipos que pueden funcionar como sujeto gramatical
_TIPOS_SUJETO: frozenset[TokenType] = frozenset({
    TokenType.PRON_PERSONAL, TokenType.PRON_NUMERAL,
    TokenType.PRON_DEMOSTR,  TokenType.PRON_INTERROG,
    TokenType.SUSTANTIVO,
})

_TIPOS_ARTICULO: frozenset[TokenType] = frozenset({
    TokenType.ARTICULO_DEF, TokenType.ARTICULO_INDEF,
})

_TIPOS_ADJ: frozenset[TokenType] = frozenset({
    TokenType.ADJETIVO, TokenType.CALIFICATIVO,
})


# ── Analizador semántico ──────────────────────────────────────────────────────

class SemanticAnalyzer:
    """
    Analizador semántico del compilador traductor Inglés-Español.

    Ejecuta 6 validaciones sobre los tokens y el AST:
      1. Sin verbo        — la oración carece de verbo
      2. Sin sujeto       — el primer verbo principal no tiene sujeto previo
      3. Negación suelta  — ADV_NEGACION sin verbo en sus vecinos inmediatos
      4. Pregunta sin ?   — PRON_INTERROG sin signo de interrogación en la oración
      5. Arts. consecutivos — dos artículos (def/indef) seguidos
      6. Orden EN         — SUSTANTIVO seguido de ADJETIVO en inglés
    """

    def __init__(self, error_table: ErrorTable | None = None) -> None:
        self._error_table = error_table
        self._errores: list[CompilerError] = []

    # ── Punto de entrada ─────────────────────────────────────────────────────

    def analizar(self, tokens: list[Token], arbol=None) -> list[CompilerError]:
        """
        Analiza la lista de tokens (y el AST opcional) en busca de errores semánticos.
        Registra los errores en la ErrorTable provista (si la hay) y los retorna.
        """
        self._errores = []

        # Lista de trabajo: excluye EOF y signos de puntuación
        util = [t for t in tokens if t.tipo not in (TokenType.EOF, TokenType.SIGNO_PUNT)]

        if not util:
            return self._errores

        self._validar_sin_verbo(util)
        self._validar_sin_sujeto(util)
        self._validar_negacion_suelta(util)
        self._validar_pregunta_sin_signo(util, tokens)
        self._validar_articulos_consecutivos(util)
        self._validar_orden_en(util)

        if self._error_table is not None:
            self._error_table.agregar_lista(self._errores)

        return self._errores

    # ── Validaciones ─────────────────────────────────────────────────────────

    def _validar_sin_verbo(self, util: list[Token]) -> None:
        """Regla 1: la oración debe contener al menos un verbo de cualquier tipo."""
        if not any(t.tipo in _TIPOS_VERBO for t in util):
            tok = util[0]
            self._agregar(
                posicion=tok.posicion,
                palabra=tok.valor,
                descripcion="La oración no contiene ningún verbo (principal, auxiliar o infinitivo).",
                sugerencia="Agregue un verbo que indique la acción o el estado del sujeto.",
            )

    def _validar_sin_sujeto(self, util: list[Token]) -> None:
        """Regla 2: debe haber un pronombre o sustantivo antes del primer VERBO principal."""
        # Solo aplica a verbos principales; VERBO_AUX al inicio puede ser pregunta legítima
        primer_verbo_idx = next(
            (i for i, t in enumerate(util) if t.tipo == TokenType.VERBO), None
        )
        if primer_verbo_idx is None:
            return  # sin verbo principal, regla 1 ya cubre ese caso

        hay_sujeto = any(t.tipo in _TIPOS_SUJETO for t in util[:primer_verbo_idx])
        if not hay_sujeto:
            tok = util[primer_verbo_idx]
            self._agregar(
                posicion=tok.posicion,
                palabra=tok.valor,
                descripcion=(
                    f"El verbo '{tok.valor}' aparece sin sujeto previo "
                    f"(pronombre o sustantivo)."
                ),
                sugerencia="Coloque un pronombre o sustantivo sujeto antes del verbo.",
            )

    def _validar_negacion_suelta(self, util: list[Token]) -> None:
        """Regla 3: un ADV_NEGACION debe tener un verbo en uno de sus 2 vecinos inmediatos."""
        for i, tok in enumerate(util):
            if tok.tipo != TokenType.ADV_NEGACION:
                continue

            vecinos: list[Token] = []
            if i > 0:
                vecinos.append(util[i - 1])
            if i < len(util) - 1:
                vecinos.append(util[i + 1])

            if not any(v.tipo in _TIPOS_VERBO for v in vecinos):
                self._agregar(
                    posicion=tok.posicion,
                    palabra=tok.valor,
                    descripcion=(
                        f"La negación '{tok.valor}' no está adyacente a ningún verbo."
                    ),
                    sugerencia="La negación debe ir junto a un verbo auxiliar o principal.",
                )

    def _validar_pregunta_sin_signo(
        self, util: list[Token], original: list[Token]
    ) -> None:
        """Regla 4: si hay PRON_INTERROG debe existir '?' o '¿' en la oración original."""
        hay_interrog = any(t.tipo == TokenType.PRON_INTERROG for t in util)
        if not hay_interrog:
            return

        # Buscar el signo en la lista original (los SIGNO_PUNT fueron filtrados de util)
        hay_signo = any(
            t.tipo == TokenType.SIGNO_PUNT and t.valor in ('?', '¿')
            for t in original
        )
        if not hay_signo:
            tok = next(t for t in util if t.tipo == TokenType.PRON_INTERROG)
            self._agregar(
                posicion=tok.posicion,
                palabra=tok.valor,
                descripcion=(
                    f"Pregunta con '{tok.valor}' sin signo de interrogación."
                ),
                sugerencia="Cierre la pregunta con '?' o ábrala con '¿'.",
            )

    def _validar_articulos_consecutivos(self, util: list[Token]) -> None:
        """Regla 5: dos artículos (definido o indefinido) consecutivos son un error."""
        for i in range(len(util) - 1):
            if util[i].tipo in _TIPOS_ARTICULO and util[i + 1].tipo in _TIPOS_ARTICULO:
                tok = util[i + 1]
                self._agregar(
                    posicion=tok.posicion,
                    palabra=tok.valor,
                    descripcion=(
                        f"Artículo '{tok.valor}' aparece inmediatamente después "
                        f"del artículo '{util[i].valor}'."
                    ),
                    sugerencia="Elimine uno de los artículos consecutivos.",
                )

    def _validar_orden_en(self, util: list[Token]) -> None:
        """Regla 6: en inglés el adjetivo precede al sustantivo; detecta SUSTANTIVO→ADJETIVO."""
        for i in range(len(util) - 1):
            if (
                util[i].tipo == TokenType.SUSTANTIVO
                and util[i + 1].tipo in _TIPOS_ADJ
                and util[i].idioma == 'EN'
            ):
                tok = util[i + 1]
                self._agregar(
                    posicion=tok.posicion,
                    palabra=tok.valor,
                    descripcion=(
                        f"En inglés el adjetivo '{tok.valor}' debe preceder al "
                        f"sustantivo '{util[i].valor}', no seguirlo."
                    ),
                    sugerencia=(
                        f"Cambie el orden: '{tok.valor} {util[i].valor}'."
                    ),
                )

    # ── Utilidad interna ─────────────────────────────────────────────────────

    def _agregar(
        self,
        posicion: int,
        palabra: str,
        descripcion: str,
        sugerencia: str = '',
    ) -> None:
        self._errores.append(CompilerError(
            tipo=ErrorTipo.SEMANTICO,
            posicion=posicion,
            palabra=palabra,
            descripcion=descripcion,
            sugerencia=sugerencia,
        ))


# ── Bloque de prueba ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        from lexer import Lexer
        from parser import Parser
    except ImportError:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from lexer import Lexer
        from parser import Parser

    lexer    = Lexer()
    parser   = Parser()
    analizador = SemanticAnalyzer()

    casos = [
        # (regla esperada,          oración de prueba)
        ("Sin verbo",               "The good dog."),
        ("Sin sujeto",              "Runs now."),
        ("Negación suelta",         "The dog not old runs."),
        ("Pregunta sin signo",      "What does the dog do"),
        ("Artículos consecutivos",  "The a dog runs."),
        ("Orden EN (sust→adj)",     "The dog old runs."),
    ]

    print("=" * 70)
    print("  PRUEBA DEL MÓDULO core/semantic_analyzer.py")
    print("=" * 70)

    for regla, oracion in casos:
        tokens, err_lex  = lexer.analizar(oracion)
        ast,    err_sint = parser.analizar(tokens)

        tabla = ErrorTable()
        tabla.agregar_lista(err_lex)
        tabla.agregar_lista(err_sint)

        err_sem = analizador.analizar(tokens, ast)
        tabla.agregar_lista(err_sem)

        print(f"\n{'─' * 70}")
        print(f"  Regla [{regla}]: {oracion}")
        print(
            f"  Léxicos: {len(err_lex)}  |  "
            f"Sintácticos: {len(err_sint)}  |  "
            f"Semánticos: {len(err_sem)}"
        )
        tabla.imprimir()

    print(f"\n{'=' * 70}")
