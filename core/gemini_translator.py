"""
Módulo GeminiTranslator del compilador traductor Inglés-Español.
Fase 4: síntesis de la traducción final mediante la API de Google Gemini.
Requiere: pip install google-genai
"""

from __future__ import annotations

import os
import sys

# Importación opcional: el módulo es cargable aunque el paquete no esté instalado.
# La validación real ocurre en __init__.
try:
    from google import genai
    _GENAI_DISPONIBLE = True
except ImportError:
    genai = None          # evita NameError si se inspecciona el módulo
    _GENAI_DISPONIBLE = False

try:
    from token_types import TokenType, Token, nombre_tipo
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from token_types import TokenType, Token, nombre_tipo


# ── Constantes ───────────────────────────────────────────────────────────────

_MODELO_ID = "gemini-1.5-flash"

# Mapas de idioma para mensajes y lógica de dirección
_NOMBRE_IDIOMA: dict[str, str] = {'EN': 'inglés', 'ES': 'español'}
_IDIOMA_DESTINO: dict[str, str] = {'EN': 'ES',    'ES': 'EN'}


# ── Clase principal ───────────────────────────────────────────────────────────

class GeminiTranslator:
    """
    Traductor Inglés↔Español basado en la API de Google Gemini.

    Enriquece el prompt con la lista de tokens producida por el Lexer para
    que el modelo disponga del análisis gramatical de la oración.

    Uso básico:
        traductor = GeminiTranslator()          # lee GEMINI_API_KEY del entorno
        resultado = traductor.traducir(texto, tokens, 'EN')
    """

    def __init__(self, api_key: str | None = None) -> None:
        # Verificar que el paquete esté instalado
        if not _GENAI_DISPONIBLE:
            raise ImportError(
                "El paquete 'google-generativeai' no está instalado.\n"
                "Instálalo con:  pip install google-generativeai"
            )

        # Leer la clave de entorno si no se pasa explícitamente
        clave = api_key or os.environ.get('GEMINI_API_KEY', '').strip()
        if not clave:
            raise ValueError(
                "No se encontró la API key de Gemini.\n\n"
                "Opciones para configurarla:\n"
                "  Windows : set GEMINI_API_KEY=tu_clave\n"
                "  Linux   : export GEMINI_API_KEY=tu_clave\n"
                "  Mac     : export GEMINI_API_KEY=tu_clave\n"
                "  Código  : GeminiTranslator(api_key='tu_clave')\n\n"
                "Obtén una clave gratuita en: https://aistudio.google.com/apikey"
            )

        # Nuevo SDK google-genai: cliente con clave explícita
        self._cliente = genai.Client(api_key=clave)

    # ── Método público ───────────────────────────────────────────────────────

    def traducir(
        self, texto: str, tokens: list[Token], idioma_origen: str
    ) -> dict:
        """
        Traduce el texto al idioma opuesto usando Gemini.

        Parámetros:
            texto         — texto original tal como llegó al compilador
            tokens        — lista de Token del Lexer (puede incluir EOF)
            idioma_origen — 'EN' o 'ES'

        Retorna un dict con claves:
            traduccion    (str)  — texto traducido; '' en caso de error
            idioma_origen (str)  — 'EN' o 'ES'
            idioma_destino(str)  — idioma opuesto al origen
            modelo        (str)  — identificador del modelo usado
            exito         (bool) — True si la llamada fue exitosa
            error         (str)  — descripción del error; '' si exito=True
        """
        origen   = idioma_origen.upper()
        destino  = _IDIOMA_DESTINO.get(origen, 'ES')
        n_origen = _NOMBRE_IDIOMA.get(origen, origen)
        n_destino = _NOMBRE_IDIOMA.get(destino, destino)

        resultado: dict = {
            'traduccion':    '',
            'idioma_origen': origen,
            'idioma_destino': destino,
            'modelo':        _MODELO_ID,
            'exito':         False,
            'error':         '',
        }

        try:
            prompt    = self._construir_prompt(texto, tokens, n_origen, n_destino)
            respuesta = self._cliente.models.generate_content(
                model=_MODELO_ID, contents=prompt
            )
            # .text lanza ValueError si la respuesta fue bloqueada por el filtro
            resultado['traduccion'] = respuesta.text.strip()
            resultado['exito']      = True
        except Exception as exc:
            resultado['error'] = str(exc)

        return resultado

    # ── Construcción del prompt ──────────────────────────────────────────────

    def _construir_prompt(
        self,
        texto: str,
        tokens: list[Token],
        nombre_origen: str,
        nombre_destino: str,
    ) -> str:
        """
        Construye el prompt enriquecido con el análisis léxico.
        La instrucción final pide SOLO la traducción, sin explicaciones.
        """
        # Tabla de tokens: excluir EOF y signos de puntuación para reducir ruido
        lineas: list[str] = []
        for tok in tokens:
            if tok.tipo in (TokenType.EOF, TokenType.SIGNO_PUNT):
                continue
            lineas.append(f"  • '{tok.valor}' → {nombre_tipo(tok.tipo)}")

        tabla_tokens = '\n'.join(lineas) if lineas else '  (sin tokens reconocidos)'

        return (
            f"Eres un traductor experto de {nombre_origen} a {nombre_destino}.\n"
            f"Se te proporciona el texto original junto con su análisis gramatical "
            f"(salida de un analizador léxico) para que la traducción sea precisa "
            f"y respete la estructura de la oración.\n\n"
            f"Texto original en {nombre_origen}:\n"
            f"  {texto}\n\n"
            f"Análisis léxico de los tokens:\n"
            f"{tabla_tokens}\n\n"
            f"Responde ÚNICAMENTE con la traducción al {nombre_destino}. "
            f"Sin comillas, sin explicaciones, sin texto adicional."
        )


# ── Bloque de prueba ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        from lexer import Lexer
    except ImportError:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from lexer import Lexer

    # Verificar que el paquete esté instalado
    if not _GENAI_DISPONIBLE:
        print("=" * 60)
        print("  PAQUETE NO INSTALADO")
        print("=" * 60)
        print("\n  Instala google-genai antes de continuar:")
        print("    pip install google-genai\n")
        print("=" * 60)
        sys.exit(0)

    # Verificar que la clave esté configurada
    if not os.environ.get('GEMINI_API_KEY', '').strip():
        print("=" * 60)
        print("  CONFIGURACIÓN REQUERIDA — GEMINI_API_KEY no encontrada")
        print("=" * 60)
        print("\n  Configura la variable de entorno antes de ejecutar:\n")
        print("    Windows : set GEMINI_API_KEY=tu_clave")
        print("    Linux   : export GEMINI_API_KEY=tu_clave")
        print("    Mac     : export GEMINI_API_KEY=tu_clave\n")
        print("  Obtén una clave gratuita en:")
        print("    https://aistudio.google.com/apikey\n")
        print("=" * 60)
        sys.exit(0)

    lexer     = Lexer()
    traductor = GeminiTranslator()

    oraciones = [
        # (texto original,                          idioma origen)
        ("The dog runs fast in the park.",          'EN'),
        ("He does not know the answer.",            'EN'),
        ("El niño estudia todos los días.",         'ES'),
        ("Nosotros aprendemos juntos cada mes.",    'ES'),
    ]

    print("=" * 70)
    print("  PRUEBA DEL MÓDULO core/gemini_translator.py")
    print("=" * 70)

    for texto, idioma in oraciones:
        tokens, _ = lexer.analizar(texto)
        resultado = traductor.traducir(texto, tokens, idioma)

        n_origen  = _NOMBRE_IDIOMA.get(resultado['idioma_origen'],  resultado['idioma_origen']).upper()
        n_destino = _NOMBRE_IDIOMA.get(resultado['idioma_destino'], resultado['idioma_destino']).upper()

        print(f"\n{'─' * 70}")
        print(f"  [{n_origen} → {n_destino}]  {texto}")
        if resultado['exito']:
            print(f"  Traducción : {resultado['traduccion']}")
        else:
            print(f"  Error      : {resultado['error']}")
        print(f"  Modelo     : {resultado['modelo']}")

    print(f"\n{'=' * 70}")
