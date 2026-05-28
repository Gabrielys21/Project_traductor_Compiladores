"""
Módulo Lexer del compilador traductor Inglés-Español.
Fase 1: análisis léxico — convierte texto plano en una secuencia de Tokens clasificados.
"""

import re
import sys
import os

# Importaciones compatibles con ejecución directa (python core/lexer.py)
# y con importación como módulo (from core.lexer import ...)
try:
    from token_types import (
        TokenType, Token, ErrorTipo, CompilerError, SIGNOS_PUNTUACION,
    )
    from dictionary_en import LEXICON_EN
    from dictionary_es import LEXICON_ES
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from token_types import (
        TokenType, Token, ErrorTipo, CompilerError, SIGNOS_PUNTUACION,
    )
    from dictionary_en import LEXICON_EN
    from dictionary_es import LEXICON_ES


# ── Patrones globales compilados una sola vez ────────────────────────────────

# Captura (en orden de prioridad):
#   [¿¡]           → signos de apertura españoles (un carácter)
#   \.{3}           → elipsis (exactamente tres puntos)
#   [\w]+(?:'[\w]+)* → palabras con posibles contracciones (don't, i'm)
#                     \w en Python 3 incluye letras con tilde (á é í ó ú ñ)
#   [^\w\s]         → cualquier otro símbolo que no sea letra ni espacio
_PATRON_LEXICO = r"[¿¡]|\.{3}|[\w]+(?:'[\w]+)*|[^\w\s]"

# Detecta enteros o decimales simples ("42", "3.14")
_RE_NUMERO = re.compile(r'^\d+(\.\d+)?$')


# ── Detección de idioma ──────────────────────────────────────────────────────

def detectar_idioma(texto: str) -> str:
    """
    Detecta si el texto dominante es inglés ('EN') o español ('ES').
    Estrategia: cuenta palabras que pertenecen EXCLUSIVAMENTE a cada léxico.
    En caso de empate devuelve 'EN'.
    """
    palabras = re.findall(r"[\w']+", texto.lower())
    solo_en = sum(1 for p in palabras if p in LEXICON_EN and p not in LEXICON_ES)
    solo_es = sum(1 for p in palabras if p in LEXICON_ES and p not in LEXICON_EN)
    return 'EN' if solo_en >= solo_es else 'ES'


# ── Tokenización cruda ───────────────────────────────────────────────────────

def _separar_tokens_raw(texto: str) -> list[str]:
    """
    Divide el texto en unidades léxicas crudas (strings sin clasificar).
    Usa re.findall con el patrón léxico definido globalmente.
    """
    return re.findall(_PATRON_LEXICO, texto)


# ── Clase principal ──────────────────────────────────────────────────────────

class Lexer:
    """
    Analizador léxico del compilador traductor Inglés-Español.

    Uso básico:
        lexer = Lexer()
        tokens, errores = lexer.analizar("The dog runs fast.")
    """

    def analizar(self, texto: str) -> tuple[list[Token], list[CompilerError]]:
        """
        Realiza el análisis léxico completo del texto.

        Pasos:
          1. Detecta el idioma.
          2. Divide el texto en unidades crudas con posición exacta.
          3. Clasifica cada unidad (bigrama/trigrama antes que token individual).
          4. Signos de puntuación → SIGNO_PUNT.
          5. Números → NUMERAL_CARD.
          6. No encontradas → UNKNOWN + CompilerError(LEXICO).
          7. Agrega token EOF al final.

        Retorna (list[Token], list[CompilerError]).
        """
        if not texto or not texto.strip():
            return [Token(TokenType.EOF, '', 0)], []

        idioma: str = detectar_idioma(texto)
        lexicon: dict[str, TokenType] = LEXICON_EN if idioma == 'EN' else LEXICON_ES

        tokens: list[Token] = []
        errores: list[CompilerError] = []

        # finditer en lugar de findall para conservar la posición de cada match
        coincidencias = list(re.finditer(_PATRON_LEXICO, texto))
        i = 0

        while i < len(coincidencias):

            # ── Trigrama: intentar reconocer frase de 3 unidades ─────────────
            if i + 2 < len(coincidencias):
                clave3 = (
                    f"{coincidencias[i    ].group().lower()} "
                    f"{coincidencias[i + 1].group().lower()} "
                    f"{coincidencias[i + 2].group().lower()}"
                )
                if clave3 in lexicon:
                    valor = (
                        f"{coincidencias[i    ].group()} "
                        f"{coincidencias[i + 1].group()} "
                        f"{coincidencias[i + 2].group()}"
                    )
                    tokens.append(
                        Token(lexicon[clave3], valor,
                              coincidencias[i].start(), idioma=idioma)
                    )
                    i += 3
                    continue

            # ── Bigrama: intentar reconocer frase de 2 unidades ──────────────
            if i + 1 < len(coincidencias):
                clave2 = (
                    f"{coincidencias[i    ].group().lower()} "
                    f"{coincidencias[i + 1].group().lower()}"
                )
                if clave2 in lexicon:
                    valor = (
                        f"{coincidencias[i    ].group()} "
                        f"{coincidencias[i + 1].group()}"
                    )
                    tokens.append(
                        Token(lexicon[clave2], valor,
                              coincidencias[i].start(), idioma=idioma)
                    )
                    i += 2
                    continue

            # ── Token individual ──────────────────────────────────────────────
            unidad   = coincidencias[i].group()
            posicion = coincidencias[i].start()
            clave    = unidad.lower()

            if unidad in SIGNOS_PUNTUACION:
                # Signo de puntuación reconocido explícitamente
                tipo, tiene_error = TokenType.SIGNO_PUNT, False

            elif _RE_NUMERO.match(clave):
                # Literal numérico (entero o decimal)
                tipo, tiene_error = TokenType.NUMERAL_CARD, False

            elif clave in lexicon:
                # Palabra encontrada en el léxico del idioma detectado
                tipo, tiene_error = lexicon[clave], False

            else:
                # Palabra desconocida → error léxico
                tipo, tiene_error = TokenType.UNKNOWN, True
                errores.append(CompilerError(
                    tipo=ErrorTipo.LEXICO,
                    posicion=posicion,
                    palabra=unidad,
                    descripcion=f"'{unidad}' no se encontró en el léxico {idioma}.",
                    sugerencia="Verifique la ortografía o amplíe el diccionario.",
                ))

            tokens.append(
                Token(tipo, unidad, posicion, idioma=idioma, tiene_error=tiene_error)
            )
            i += 1

        # Token especial de fin de entrada (posición = longitud total del texto)
        tokens.append(Token(TokenType.EOF, '', len(texto), idioma=idioma))
        return tokens, errores


# ── Generador de tabla de símbolos ───────────────────────────────────────────

def generar_tabla_simbolos(tokens: list[Token]) -> list[dict]:
    """
    Convierte la lista de tokens en una tabla de símbolos (lista de dicts).
    Excluye el token EOF del resultado.
    """
    return [tok.to_dict() for tok in tokens if tok.tipo != TokenType.EOF]


# ── Bloque de prueba ─────────────────────────────────────────────────────────

if __name__ == "__main__":

    lexer = Lexer()

    oraciones = [
        # 1 — Inglés básico (1 error esperado: "brown" no está en el léxico)
        "The quick brown fox jumps over the lazy dog.",
        # 2 — Inglés con contracciones (0 errores)
        "I can't believe he doesn't know the answer yet.",
        # 3 — Español con verbos conjugados (1 error esperado: "días" → plural no incluido)
        "El niño aprende y trabaja todos los días.",
        # 4 — Español con auxiliares y conjunción causal (0 errores)
        "Nosotros estudiamos y aprendemos juntos cada mes.",
        # 5 — Palabras inventadas + número → errores léxicos intencionales
        "The xlerp blarg 42 words zorp definitely work.",
    ]

    print("=" * 70)
    print("  PRUEBA DEL MÓDULO core/lexer.py")
    print("=" * 70)

    for idx, oracion in enumerate(oraciones, 1):
        tokens, errores = lexer.analizar(oracion)
        idioma_det = tokens[0].idioma if tokens else '??'

        print(f"\n{'─' * 70}")
        print(f"  Oración {idx}: {oracion}")
        print(
            f"  Idioma detectado : {idioma_det}   |   "
            f"Tokens: {len(tokens) - 1}   |   "
            f"Errores léxicos: {len(errores)}"
        )
        print()
        for tok in tokens:
            print(f"    {tok}")

        if errores:
            print()
            for err in errores:
                print(f"    {err}")

    # ── Tabla de símbolos detallada para la oración 5 ────────────────────────
    print(f"\n{'─' * 70}")
    print("  Tabla de símbolos — Oración 5 (con errores intencionales)")
    print(f"{'─' * 70}")

    tokens5, _ = lexer.analizar(oraciones[4])
    tabla = generar_tabla_simbolos(tokens5)

    col = f"  {'pos':>4}  {'tipo':<16}  {'categoría':<23}  {'valor':<12}  idioma  error"
    print(col)
    print(f"  {'─'*4}  {'─'*16}  {'─'*23}  {'─'*12}  {'─'*6}  {'─'*5}")
    for fila in tabla:
        print(
            f"  {fila['posicion']:>4}  "
            f"{fila['tipo']:<16}  "
            f"{fila['categoria']:<23}  "
            f"{fila['valor']:<12}  "
            f"{fila['idioma']:<6}  "
            f"{str(fila['tiene_error'])}"
        )

    print(f"\n{'=' * 70}")
    print(f"  Total entradas en tabla (sin EOF): {len(tabla)}")
    print(f"{'=' * 70}")
