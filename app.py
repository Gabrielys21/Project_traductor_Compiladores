"""
Servidor Flask del compilador traductor Inglés-Español.

Rutas:
  GET  /         → página principal (templates/index.html)
  POST /traducir → pipeline léxico → sintáctico → semántico → Gemini
"""

import os
from flask import Flask, request, jsonify, render_template

from core.lexer import Lexer, generar_tabla_simbolos
from core.error_table import ErrorTable
from core.parser import Parser
from core.semantic_analyzer import SemanticAnalyzer
from core.gemini_translator import GeminiTranslator


# ── Instancias globales ───────────────────────────────────────────────────────

app = Flask(__name__)

# GeminiTranslator es stateless (sin estado mutable por request): global es seguro.
try:
    translator = GeminiTranslator()
except (ValueError, ImportError) as exc:
    translator = None
    print(f"[ADVERTENCIA] Traductor Gemini no disponible: {exc}")


# ── Rutas ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Sirve la página principal."""
    return render_template('index.html')


@app.route('/traducir', methods=['POST'])
def traducir():
    """
    Ejecuta el pipeline completo sobre el texto recibido.

    Cuerpo esperado  (JSON): {"texto": "..."}

    Respuesta sin errores:
        {"exito": true, "traduccion": "...", "idioma_origen": "EN"|"ES",
         "tabla_simbolos": [...], "errores": []}

    Respuesta con errores de análisis:
        {"exito": false, "errores": [...], "tabla_simbolos": [...]}
    """
    datos = request.get_json(force=True, silent=True) or {}
    texto = (datos.get('texto') or '').strip()

    # ── Validación de entrada ────────────────────────────────────────────────

    if not texto:
        return jsonify({
            'exito':          False,
            'errores':        [{
                'tipo':        'INPUT',
                'posicion':    0,
                'palabra':     '',
                'descripcion': 'El texto no puede estar vacío.',
                'sugerencia':  'Ingrese una oración para traducir.',
            }],
            'tabla_simbolos': [],
        }), 400

    if translator is None:
        return jsonify({
            'exito':          False,
            'errores':        [{
                'tipo':        'CONFIG',
                'posicion':    0,
                'palabra':     '',
                'descripcion': 'GEMINI_API_KEY no configurada: el traductor no está disponible.',
                'sugerencia':  'Configure la variable de entorno GEMINI_API_KEY '
                               'antes de iniciar el servidor.',
            }],
            'tabla_simbolos': [],
        }), 503

    # ── Instancias locales por request (evita estado compartido entre requests) ──

    tabla_err = ErrorTable()
    lexer     = Lexer()
    parser    = Parser(tabla_err)
    sem       = SemanticAnalyzer(tabla_err)

    # ── Pipeline de análisis ─────────────────────────────────────────────────

    tokens, err_lex = lexer.analizar(texto)          # fase 1 — léxico
    tabla_err.agregar_lista(err_lex)                 # errores léxicos bloquean traducción
    arbol,  _       = parser.analizar(tokens)        # fase 2 — sintáctico (→ tabla_err)
    sem.analizar(tokens, arbol)                      # fase 3 — semántico  (→ tabla_err)

    tabla_simbolos = generar_tabla_simbolos(tokens)

    # ── Decisión: hay errores → no traducir ──────────────────────────────────

    if tabla_err.hay_errores():
        return jsonify({
            'exito':          False,
            'errores':        tabla_err.to_list(),
            'tabla_simbolos': tabla_simbolos,
        })

    # ── Sin errores → llamar a Gemini ────────────────────────────────────────

    resultado = translator.traducir(texto, tokens, lexer.idioma)

    return jsonify({
        'exito':          True,
        'traduccion':     resultado['traduccion'],
        'idioma_origen':  lexer.idioma,
        'tabla_simbolos': tabla_simbolos,
        'errores':        [],
    })


# ── Punto de entrada ──────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(debug=True)
