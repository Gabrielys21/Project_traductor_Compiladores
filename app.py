"""
Servidor Flask del compilador traductor Inglés-Español.

Rutas:
  GET  /login    → pantalla de acceso
  POST /login    → valida contraseña, inicia sesión
  GET  /logout   → cierra sesión, redirige a /login
  GET  /         → página principal (requiere sesión)
  POST /traducir → pipeline léxico → sintáctico → semántico → Gemini (requiere sesión)
"""

import os
from flask import Flask, request, jsonify, render_template, session, redirect, url_for

from core.lexer import Lexer, generar_tabla_simbolos
from core.error_table import ErrorTable
from core.parser import Parser
from core.semantic_analyzer import SemanticAnalyzer
from core.gemini_translator import GeminiTranslator


# ── Configuración global ──────────────────────────────────────────────────────

app            = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'clave_dev_local')

ACCESS_PASSWORD = os.getenv('ACCESS_PASSWORD', '')

# GeminiTranslator es stateless (sin estado mutable por request): global es seguro.
try:
    translator = GeminiTranslator()
except (ValueError, ImportError) as exc:
    translator = None
    print(f'[ADVERTENCIA] Traductor Gemini no disponible: {exc}')


# ── Helpers ───────────────────────────────────────────────────────────────────

def _autenticado() -> bool:
    return session.get('autenticado') is True


# ── Rutas de autenticación ────────────────────────────────────────────────────

@app.route('/login', methods=['GET'])
def login_page():
    """Muestra la pantalla de acceso; si ya hay sesión redirige a /."""
    if _autenticado():
        return redirect(url_for('index'))
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def login_post():
    """
    Valida la contraseña recibida por JSON.
    Retorna {"exito": true} o {"exito": false, "error": "..."}.
    """
    datos    = request.get_json(force=True, silent=True) or {}
    password = datos.get('password', '')

    if ACCESS_PASSWORD and password == ACCESS_PASSWORD:
        session['autenticado'] = True
        return jsonify({'exito': True})

    return jsonify({'exito': False, 'error': 'Contraseña incorrecta.'}), 401


@app.route('/logout')
def logout():
    """Cierra la sesión y redirige a /login."""
    session.clear()
    return redirect(url_for('login_page'))


# ── Rutas protegidas ──────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Sirve la página principal (requiere sesión activa)."""
    if not _autenticado():
        return redirect(url_for('login_page'))
    return render_template('index.html')


@app.route('/traducir', methods=['POST'])
def traducir():
    """
    Ejecuta el pipeline completo sobre el texto recibido (requiere sesión activa).

    Cuerpo esperado  (JSON): {"texto": "..."}

    Respuesta exitosa (siempre que Gemini responda):
        {"exito": true, "traduccion": "...", "idioma_origen": "EN"|"ES",
         "tabla_simbolos": [...], "errores": [...]}  ← errores puede ser [] o tener entradas

    Respuesta fallida (solo si Gemini falla):
        {"exito": false, "errores": [...], "tabla_simbolos": [...]}
    """
    if not _autenticado():
        return jsonify({'exito': False, 'error': 'No autenticado.'}), 401

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
    tabla_err.agregar_lista(err_lex)                 # acumula errores léxicos
    arbol,  _       = parser.analizar(tokens)        # fase 2 — sintáctico (→ tabla_err)
    sem.analizar(tokens, arbol)                      # fase 3 — semántico  (→ tabla_err)

    tabla_simbolos = generar_tabla_simbolos(tokens)

    # ── Siempre traducir con Gemini, independientemente de errores ────────────

    resultado = translator.traducir(texto, tokens, lexer.idioma)

    if not resultado['exito']:
        print("GEMINI ERROR:", resultado.get('error'))
        print("DETALLE:", resultado.get('detalle'))

    if not resultado['exito']:
        return jsonify({
            'exito':          False,
            'errores':        tabla_err.to_list(),
            'tabla_simbolos': tabla_simbolos,
        })

    return jsonify({
        'exito':          True,
        'traduccion':     resultado['traduccion'],
        'idioma_origen':  lexer.idioma,
        'tabla_simbolos': tabla_simbolos,
        'errores':        tabla_err.to_list(),
    })


# ── Punto de entrada ──────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
