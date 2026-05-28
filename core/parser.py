"""
Módulo Parser del compilador traductor Inglés-Español.
Fase 2: análisis sintáctico — construye el Árbol de Sintaxis Abstracta (AST)
a partir de la secuencia de Tokens producida por el Lexer.
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

_TIPOS_DET: frozenset[TokenType] = frozenset({
    TokenType.ARTICULO_DEF,  TokenType.ARTICULO_INDEF,
    TokenType.POSESIVO,      TokenType.DEMOSTRATIVO,
    TokenType.INDEFINIDO,    TokenType.NUMERAL_CARD,
    TokenType.NUMERAL_ORD,   TokenType.CONTRACCION,
})

_TIPOS_ADJ: frozenset[TokenType] = frozenset({
    TokenType.ADJETIVO,
    TokenType.CALIFICATIVO,
})

_TIPOS_ADV_MOD: frozenset[TokenType] = frozenset({
    TokenType.ADV_TIEMPO,     TokenType.ADV_LUGAR,
    TokenType.ADV_CANTIDAD,   TokenType.ADV_MODO,
    TokenType.ADV_AFIRMACION, TokenType.ADV_DUDA,
})

# Tipos que pueden iniciar un complemento (excluye ADV_NEGACION a propósito)
_TIPOS_INIC_COMPLEMENTO: frozenset[TokenType] = (
    frozenset({TokenType.PREPOSICION, TokenType.SUSTANTIVO})
    | _TIPOS_DET
    | _TIPOS_ADJ
    | _TIPOS_ADV_MOD
)


# ── Nodo del AST ─────────────────────────────────────────────────────────────

class NodoAST:
    """Nodo del Árbol de Sintaxis Abstracta."""

    def __init__(self, etiqueta: str, token: Token | None = None) -> None:
        self.etiqueta = etiqueta
        self.token    = token
        self.hijos: list[NodoAST] = []

    def agregar_hijo(self, hijo: NodoAST) -> None:
        self.hijos.append(hijo)

    def to_dict(self) -> dict:
        nodo: dict = {'etiqueta': self.etiqueta}
        if self.token is not None:
            nodo['token'] = {
                'tipo':  self.token.tipo.name,
                'valor': self.token.valor,
                'pos':   self.token.posicion,
            }
        nodo['hijos'] = [h.to_dict() for h in self.hijos]
        return nodo

    def imprimir(self, nivel: int = 0, es_ultimo: bool = True) -> None:
        rama   = '└── ' if es_ultimo else '├── '
        indent = '│   ' * nivel
        if self.token is not None:
            print(f"{indent}{rama}{self.etiqueta}: '{self.token.valor}' [{self.token.tipo.name}]")
        else:
            print(f"{indent}{rama}{self.etiqueta}")
        for i, hijo in enumerate(self.hijos):
            hijo.imprimir(nivel + 1, i == len(self.hijos) - 1)


# ── Clase Parser ─────────────────────────────────────────────────────────────

class Parser:
    """
    Analizador sintáctico descendente recursivo (LL(1)).

    BNF implementado:
        <oracion>     ::= <pregunta> | <sujeto> <predicado> [SIGNO_PUNT]
        <pregunta>    ::= PRON_INTERROG [VERBO_AUX] [<sujeto>]
                          [VERBO|VERBO_INF] [<complemento>] [SIGNO_PUNT]
        <sujeto>      ::= PRON_PERSONAL | [det] [adj*] SUSTANTIVO
        <predicado>   ::= [VERBO_AUX] [ADV_NEGACION|CONTRACCION]
                          [VERBO|VERBO_INF] [<complemento>]
        <complemento> ::= [PREPOSICION] [det] [adj*] [SUSTANTIVO] [adv*]
        <det>         ::= ARTICULO_DEF | ARTICULO_INDEF | POSESIVO |
                          DEMOSTRATIVO | INDEFINIDO | NUMERAL_CARD |
                          NUMERAL_ORD | CONTRACCION
    """

    def __init__(self, error_table: ErrorTable | None = None) -> None:
        self._tokens:      list[Token] = []
        self._pos:         int = 0
        self._errores:     list[CompilerError] = []
        self._error_table: ErrorTable | None = error_table

    # ── Acceso al flujo de tokens ────────────────────────────────────────────

    def _actual(self) -> Token:
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return self._tokens[-1]  # siempre apunta al EOF

    def _avanzar(self) -> Token:
        tok = self._actual()
        if tok.tipo != TokenType.EOF:
            self._pos += 1
        return tok

    def _es_tipo(self, *tipos: TokenType) -> bool:
        return self._actual().tipo in tipos

    def _es_valor(self, *valores: str) -> bool:
        return self._actual().valor.lower() in {v.lower() for v in valores}

    def _registrar_error(self, descripcion: str, sugerencia: str = '') -> None:
        tok = self._actual()
        error = CompilerError(
            tipo=ErrorTipo.SINTACTICO,
            posicion=tok.posicion,
            palabra=tok.valor,
            descripcion=descripcion,
            sugerencia=sugerencia,
        )
        self._errores.append(error)
        # Propagar a la ErrorTable global si se proporcionó una
        if self._error_table is not None:
            self._error_table.agregar(error)

    # ── Punto de entrada ─────────────────────────────────────────────────────

    def analizar(self, tokens: list[Token]) -> tuple[NodoAST, list[CompilerError]]:
        """Analiza la secuencia de tokens. Retorna (raiz_ast, errores_sintacticos)."""
        self._tokens  = tokens if tokens else [Token(TokenType.EOF, '', 0)]
        self._pos     = 0
        self._errores = []

        raiz = NodoAST('PROGRAMA')
        if not self._es_tipo(TokenType.EOF):
            raiz.agregar_hijo(self._parse_oracion())
        return raiz, self._errores

    # ── Reglas de producción ─────────────────────────────────────────────────

    def _parse_oracion(self) -> NodoAST:
        nodo = NodoAST('ORACION')
        if self._es_tipo(TokenType.PRON_INTERROG):
            nodo.agregar_hijo(self._parse_pregunta())
        else:
            nodo.agregar_hijo(self._parse_sujeto())
            nodo.agregar_hijo(self._parse_predicado())
            if self._es_tipo(TokenType.SIGNO_PUNT):
                nodo.agregar_hijo(NodoAST('SIGNO_FINAL', self._avanzar()))
        return nodo

    def _parse_pregunta(self) -> NodoAST:
        nodo = NodoAST('PREGUNTA')
        nodo.agregar_hijo(NodoAST('PRON_INTERROG', self._avanzar()))

        if self._es_tipo(TokenType.VERBO_AUX):
            nodo.agregar_hijo(NodoAST('VERBO_AUX', self._avanzar()))

        if self._es_tipo(TokenType.PRON_PERSONAL, *_TIPOS_DET, TokenType.SUSTANTIVO):
            nodo.agregar_hijo(self._parse_sujeto())

        if self._es_tipo(TokenType.VERBO, TokenType.VERBO_INF):
            nodo.agregar_hijo(NodoAST('VERBO', self._avanzar()))

        if self._es_tipo(*_TIPOS_INIC_COMPLEMENTO):
            nodo.agregar_hijo(self._parse_complemento())

        if self._es_tipo(TokenType.SIGNO_PUNT):
            nodo.agregar_hijo(NodoAST('SIGNO_FINAL', self._avanzar()))
        return nodo

    def _parse_sujeto(self) -> NodoAST:
        nodo = NodoAST('SUJETO')

        if self._es_tipo(TokenType.PRON_PERSONAL):
            nodo.agregar_hijo(NodoAST('PRON_PERSONAL', self._avanzar()))
            return nodo

        if self._es_tipo(*_TIPOS_DET):
            nodo.agregar_hijo(NodoAST('DET', self._avanzar()))

        while self._es_tipo(*_TIPOS_ADJ):
            nodo.agregar_hijo(NodoAST('ADJ', self._avanzar()))

        if self._es_tipo(TokenType.SUSTANTIVO):
            nodo.agregar_hijo(NodoAST('SUSTANTIVO', self._avanzar()))
        else:
            # Error: sustantivo obligatorio no encontrado
            self._registrar_error(
                f"Se esperaba SUSTANTIVO en el sujeto, "
                f"se encontró '{self._actual().valor}' ({self._actual().tipo.name}).",
                "Verifique que el sujeto contenga un sustantivo.",
            )
            # Recuperación: no consumir si el siguiente token es un verbo
            if not self._es_tipo(
                TokenType.EOF,       TokenType.VERBO,
                TokenType.VERBO_AUX, TokenType.VERBO_INF,
            ):
                self._avanzar()
        return nodo

    def _parse_predicado(self) -> NodoAST:
        nodo = NodoAST('PREDICADO')

        if self._es_tipo(TokenType.VERBO_AUX):
            nodo.agregar_hijo(NodoAST('VERBO_AUX', self._avanzar()))

        # Negación explícita (not) o contracción negativa (don't, can't…)
        if self._es_tipo(TokenType.ADV_NEGACION):
            nodo.agregar_hijo(NodoAST('ADV_NEGACION', self._avanzar()))
        elif self._es_tipo(TokenType.CONTRACCION):
            nodo.agregar_hijo(NodoAST('CONTRACCION', self._avanzar()))

        if self._es_tipo(TokenType.VERBO, TokenType.VERBO_INF):
            nodo.agregar_hijo(NodoAST('VERBO', self._avanzar()))
        elif not self._es_tipo(TokenType.SIGNO_PUNT, TokenType.EOF):
            # Error solo cuando hay tokens nominales donde debería ir un verbo
            if self._es_tipo(TokenType.SUSTANTIVO, *_TIPOS_ADJ, *_TIPOS_DET):
                self._registrar_error(
                    f"Se esperaba VERBO en el predicado, "
                    f"se encontró '{self._actual().valor}' ({self._actual().tipo.name}).",
                    "Verifique que el predicado contenga un verbo principal.",
                )

        if self._es_tipo(*_TIPOS_INIC_COMPLEMENTO):
            nodo.agregar_hijo(self._parse_complemento())
        return nodo

    def _parse_complemento(self) -> NodoAST:
        nodo = NodoAST('COMPLEMENTO')

        if self._es_tipo(TokenType.PREPOSICION):
            nodo.agregar_hijo(NodoAST('PREPOSICION', self._avanzar()))

        if self._es_tipo(*_TIPOS_DET):
            nodo.agregar_hijo(NodoAST('DET', self._avanzar()))

        while self._es_tipo(*_TIPOS_ADJ):
            nodo.agregar_hijo(NodoAST('ADJ', self._avanzar()))

        if self._es_tipo(TokenType.SUSTANTIVO):
            nodo.agregar_hijo(NodoAST('SUSTANTIVO', self._avanzar()))

        while self._es_tipo(*_TIPOS_ADV_MOD):
            nodo.agregar_hijo(NodoAST('ADV', self._avanzar()))
        return nodo


# ── Bloque de prueba ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        from lexer import Lexer
    except ImportError:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from lexer import Lexer

    lexer  = Lexer()
    parser = Parser()

    casos = [
        # (descripción,              oración de prueba)
        ("Inglés válida",    "The dog runs well."),
        ("Español válida",   "Nosotros estudiamos juntos."),
        ("Pregunta",         "What does the dog do?"),
        ("Con negación",     "He does not run."),
        ("Error de orden",   "Runs the dog well."),   # verbo al inicio → sin sujeto
    ]

    print("=" * 70)
    print("  PRUEBA DEL MÓDULO core/parser.py")
    print("=" * 70)

    for titulo, oracion in casos:
        tokens, err_lex  = lexer.analizar(oracion)
        ast,    err_sint = parser.analizar(tokens)

        tabla_errores = ErrorTable()
        tabla_errores.agregar_lista(err_lex)
        tabla_errores.agregar_lista(err_sint)

        idioma = tokens[0].idioma if tokens else '??'
        print(f"\n{'─' * 70}")
        print(f"  Caso [{titulo}]: {oracion}")
        print(
            f"  Idioma: {idioma}  |  "
            f"Errores léxicos: {len(err_lex)}  |  "
            f"Errores sintácticos: {len(err_sint)}"
        )
        print()
        ast.imprimir()

        if tabla_errores.hay_errores():
            print()
            tabla_errores.imprimir()

    print(f"\n{'=' * 70}")
