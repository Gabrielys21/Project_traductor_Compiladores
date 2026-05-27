"""
Módulo base del compilador traductor Inglés-Español (v2).
Define todos los tipos de token, estructuras de datos y errores usados en el sistema.

Arquitectura:
  - Fases 1-3 (léxico, sintáctico, semántico) → Python puro
  - Fase 4 (traducción final) → Gemini API
  Por eso Token no almacena 'traduccion'; esa responsabilidad pertenece a la Fase 4.
"""

from enum import Enum, auto
from dataclasses import dataclass


# 1. Enumeración de tipos de token

class TokenType(Enum):
    # Sustantivos y adjetivos
    SUSTANTIVO      = auto()
    ADJETIVO        = auto()
    CALIFICATIVO    = auto()

    # Determinantes
    ARTICULO_DEF    = auto()
    ARTICULO_INDEF  = auto()
    POSESIVO        = auto()
    DEMOSTRATIVO    = auto()
    INDEFINIDO      = auto()
    NUMERAL_CARD    = auto()
    NUMERAL_ORD     = auto()

    # Pronombres
    PRON_PERSONAL   = auto()
    PRON_NUMERAL    = auto()
    PRON_DEMOSTR    = auto()
    PRON_INTERROG   = auto()

    # Verbos
    VERBO           = auto()
    VERBO_AUX       = auto()
    VERBO_INF       = auto()

    # Adverbios
    ADV_TIEMPO      = auto()
    ADV_LUGAR       = auto()
    ADV_CANTIDAD    = auto()
    ADV_MODO        = auto()
    ADV_AFIRMACION  = auto()
    ADV_NEGACION    = auto()
    ADV_DUDA        = auto()

    # Preposiciones
    PREPOSICION     = auto()

    # Conjunciones coordinantes
    CONJ_COPUL      = auto()
    CONJ_ADVERS     = auto()
    CONJ_DISYUNT    = auto()
    CONJ_DISTRIB    = auto()
    CONJ_EXPLIC     = auto()

    # Conjunciones subordinantes
    CONJ_COND       = auto()
    CONJ_CAUSAL     = auto()
    CONJ_CONSEC     = auto()
    CONJ_CONCES     = auto()
    CONJ_COMPAR     = auto()
    CONJ_FINAL      = auto()

    # Otros
    INTERJECCION    = auto()
    CONTRACCION     = auto()
    SIGNO_PUNT      = auto()

    # Especiales internos
    UNKNOWN         = auto()
    EOF             = auto()


# ---------------------------------------------------------------------------
# 2. Dataclass Token  (sin atributo 'traduccion' — responsabilidad de Fase 4)
# ---------------------------------------------------------------------------

@dataclass
class Token:
    tipo: TokenType
    valor: str          # Palabra original
    posicion: int       # Índice 0-based en el texto
    idioma: str = 'EN'  # 'EN' o 'ES'
    tiene_error: bool = False

    def __str__(self) -> str:
        error_marca = ' ⚠' if self.tiene_error else ''
        return f"[{self.posicion}] {self.tipo.name} '{self.valor}'{error_marca}"

    def to_dict(self) -> dict:
        return {
            'posicion':    self.posicion,
            'tipo':        self.tipo.name,
            'categoria':   _categoria(self.tipo),
            'valor':       self.valor,
            'idioma':      self.idioma,
            'tiene_error': self.tiene_error,
        }


# ---------------------------------------------------------------------------
# 3. Enumeración de tipos de error
# ---------------------------------------------------------------------------

class ErrorTipo(Enum):
    LEXICO      = auto()
    SINTACTICO  = auto()
    SEMANTICO   = auto()


# ---------------------------------------------------------------------------
# 4. Dataclass CompilerError
# ---------------------------------------------------------------------------

@dataclass
class CompilerError:
    tipo: ErrorTipo
    posicion: int
    palabra: str
    descripcion: str
    sugerencia: str = ''

    def __str__(self) -> str:
        lineas = [
            f"[Error {self.tipo.name}] posición {self.posicion}: '{self.palabra}'",
            f"  Descripción : {self.descripcion}",
        ]
        if self.sugerencia:
            lineas.append(f"  Sugerencia  : {self.sugerencia}")
        return '\n'.join(lineas)

    def to_dict(self) -> dict:
        return {
            'tipo':        self.tipo.name,
            'posicion':    self.posicion,
            'palabra':     self.palabra,
            'descripcion': self.descripcion,
            'sugerencia':  self.sugerencia,
        }


# ---------------------------------------------------------------------------
# 5. Signos de puntuación reconocidos
# ---------------------------------------------------------------------------

SIGNOS_PUNTUACION: set = {'.', ',', '!', '?', ';', ':', '...', '¡', '¿'}


# ---------------------------------------------------------------------------
# 6. Función nombre_tipo y mapa de categorías (auxiliar para to_dict)
# ---------------------------------------------------------------------------

_NOMBRES_LEGIBLES: dict[TokenType, str] = {
    # Sustantivos y adjetivos
    TokenType.SUSTANTIVO:     "Sustantivo",
    TokenType.ADJETIVO:       "Adjetivo",
    TokenType.CALIFICATIVO:   "Adjetivo calificativo",
    # Determinantes
    TokenType.ARTICULO_DEF:   "Artículo definido",
    TokenType.ARTICULO_INDEF: "Artículo indefinido",
    TokenType.POSESIVO:       "Determinante posesivo",
    TokenType.DEMOSTRATIVO:   "Determinante demostrativo",
    TokenType.INDEFINIDO:     "Determinante indefinido",
    TokenType.NUMERAL_CARD:   "Numeral cardinal",
    TokenType.NUMERAL_ORD:    "Numeral ordinal",
    # Pronombres
    TokenType.PRON_PERSONAL:  "Pronombre personal",
    TokenType.PRON_NUMERAL:   "Pronombre numeral",
    TokenType.PRON_DEMOSTR:   "Pronombre demostrativo",
    TokenType.PRON_INTERROG:  "Pronombre interrogativo",
    # Verbos
    TokenType.VERBO:          "Verbo",
    TokenType.VERBO_AUX:      "Verbo auxiliar",
    TokenType.VERBO_INF:      "Verbo en infinitivo",
    # Adverbios
    TokenType.ADV_TIEMPO:     "Adverbio de tiempo",
    TokenType.ADV_LUGAR:      "Adverbio de lugar",
    TokenType.ADV_CANTIDAD:   "Adverbio de cantidad",
    TokenType.ADV_MODO:       "Adverbio de modo",
    TokenType.ADV_AFIRMACION: "Adverbio de afirmación",
    TokenType.ADV_NEGACION:   "Adverbio de negación",
    TokenType.ADV_DUDA:       "Adverbio de duda",
    # Preposiciones
    TokenType.PREPOSICION:    "Preposición",
    # Conjunciones coordinantes
    TokenType.CONJ_COPUL:     "Conjunción copulativa",
    TokenType.CONJ_ADVERS:    "Conjunción adversativa",
    TokenType.CONJ_DISYUNT:   "Conjunción disyuntiva",
    TokenType.CONJ_DISTRIB:   "Conjunción distributiva",
    TokenType.CONJ_EXPLIC:    "Conjunción explicativa",
    # Conjunciones subordinantes
    TokenType.CONJ_COND:      "Conjunción condicional",
    TokenType.CONJ_CAUSAL:    "Conjunción causal",
    TokenType.CONJ_CONSEC:    "Conjunción consecutiva",
    TokenType.CONJ_CONCES:    "Conjunción concesiva",
    TokenType.CONJ_COMPAR:    "Conjunción comparativa",
    TokenType.CONJ_FINAL:     "Conjunción final",
    # Otros
    TokenType.INTERJECCION:   "Interjección",
    TokenType.CONTRACCION:    "Contracción",
    TokenType.SIGNO_PUNT:     "Signo de puntuación",
    # Especiales internos
    TokenType.UNKNOWN:        "Tipo desconocido",
    TokenType.EOF:            "Fin de entrada",
}

_CATEGORIAS: dict[TokenType, str] = {
    TokenType.SUSTANTIVO:     "Sustantivo/Adjetivo",
    TokenType.ADJETIVO:       "Sustantivo/Adjetivo",
    TokenType.CALIFICATIVO:   "Sustantivo/Adjetivo",
    TokenType.ARTICULO_DEF:   "Determinante",
    TokenType.ARTICULO_INDEF: "Determinante",
    TokenType.POSESIVO:       "Determinante",
    TokenType.DEMOSTRATIVO:   "Determinante",
    TokenType.INDEFINIDO:     "Determinante",
    TokenType.NUMERAL_CARD:   "Determinante",
    TokenType.NUMERAL_ORD:    "Determinante",
    TokenType.PRON_PERSONAL:  "Pronombre",
    TokenType.PRON_NUMERAL:   "Pronombre",
    TokenType.PRON_DEMOSTR:   "Pronombre",
    TokenType.PRON_INTERROG:  "Pronombre",
    TokenType.VERBO:          "Verbo",
    TokenType.VERBO_AUX:      "Verbo",
    TokenType.VERBO_INF:      "Verbo",
    TokenType.ADV_TIEMPO:     "Adverbio",
    TokenType.ADV_LUGAR:      "Adverbio",
    TokenType.ADV_CANTIDAD:   "Adverbio",
    TokenType.ADV_MODO:       "Adverbio",
    TokenType.ADV_AFIRMACION: "Adverbio",
    TokenType.ADV_NEGACION:   "Adverbio",
    TokenType.ADV_DUDA:       "Adverbio",
    TokenType.PREPOSICION:    "Preposición",
    TokenType.CONJ_COPUL:     "Conjunción coordinante",
    TokenType.CONJ_ADVERS:    "Conjunción coordinante",
    TokenType.CONJ_DISYUNT:   "Conjunción coordinante",
    TokenType.CONJ_DISTRIB:   "Conjunción coordinante",
    TokenType.CONJ_EXPLIC:    "Conjunción coordinante",
    TokenType.CONJ_COND:      "Conjunción subordinante",
    TokenType.CONJ_CAUSAL:    "Conjunción subordinante",
    TokenType.CONJ_CONSEC:    "Conjunción subordinante",
    TokenType.CONJ_CONCES:    "Conjunción subordinante",
    TokenType.CONJ_COMPAR:    "Conjunción subordinante",
    TokenType.CONJ_FINAL:     "Conjunción subordinante",
    TokenType.INTERJECCION:   "Otro",
    TokenType.CONTRACCION:    "Otro",
    TokenType.SIGNO_PUNT:     "Otro",
    TokenType.UNKNOWN:        "Especial",
    TokenType.EOF:            "Especial",
}


def _categoria(token_type: TokenType) -> str:
    """Retorna la categoría gramatical agrupada de un TokenType."""
    return _CATEGORIAS.get(token_type, "Desconocido")


def nombre_tipo(token_type: TokenType) -> str:
    """Retorna el nombre legible en español para un TokenType dado."""
    return _NOMBRES_LEGIBLES.get(token_type, token_type.name)


# ---------------------------------------------------------------------------
# 7. Bloque de prueba
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("  PRUEBA DEL MÓDULO core/token_types.py  [v2]")
    print("=" * 60)

    # 7 tokens de prueba (sin atributo traduccion)
    tokens_prueba = [
        Token(TokenType.ARTICULO_DEF,  'The',   0),
        Token(TokenType.ADJETIVO,      'quick',  4),
        Token(TokenType.SUSTANTIVO,    'fox',   10),
        Token(TokenType.VERBO_AUX,     'does',  14),
        Token(TokenType.ADV_NEGACION,  'not',   19),
        Token(TokenType.VERBO_INF,     'jump',  23),
        Token(TokenType.SIGNO_PUNT,    '.',     27, tiene_error=True),
    ]

    print("\n--- Tokens de prueba ---")
    for tok in tokens_prueba:
        print(tok)

    print("\n--- to_dict() del primer token ---")
    for clave, valor in tokens_prueba[0].to_dict().items():
        print(f"  {clave:12s}: {valor}")

    print("\n--- to_dict() del token con error ---")
    for clave, valor in tokens_prueba[-1].to_dict().items():
        print(f"  {clave:12s}: {valor}")

    # 1 CompilerError de tipo LEXICO
    error_lexico = CompilerError(
        tipo=ErrorTipo.LEXICO,
        posicion=27,
        palabra='.',
        descripcion="Signo de puntuación encontrado en posición inesperada.",
        sugerencia="Verificar si el símbolo pertenece al conjunto SIGNOS_PUNTUACION.",
    )

    print("\n--- CompilerError de ejemplo ---")
    print(error_lexico)

    print("\n--- to_dict() del error ---")
    for clave, valor in error_lexico.to_dict().items():
        print(f"  {clave:12s}: {valor}")

    # Verificación total de tipos
    total = len(TokenType)
    print(f"\n{'=' * 60}")
    print(f"  Total de tipos de TokenType: {total}")
    assert total == 41, f"Se esperaban 41 tipos, se encontraron {total}"
    print("  Verificación exitosa: 41 tipos confirmados.")
    print("=" * 60)
