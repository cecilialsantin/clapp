from flask import Flask, render_template, request
from PIL import Image
import pytesseract
import os
import subprocess
import re
import shutil

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Limpieza de archivos luego del análisis
def limpiar_uploads():
    shutil.rmtree(UPLOAD_FOLDER)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Extrae el texto de la imagen
def extraer_texto(image_path):
    return pytesseract.image_to_string(Image.open(image_path), lang='spa')

# Analiza si hay datos nutricionales en el texto
def analizar_nutricional(texto):
    patron = r"(energ\w*|calor\w*|prote\w*|grasa\w*|carbohidr\w*|sodio|fibra|az\w*)"
    encontrados = re.findall(patron, texto, re.IGNORECASE)
    return list(set([e.capitalize() for e in encontrados]))

# Busca posibles RNE y RNPA
def validar_rne_rnpa(texto):
    rne = re.findall(r"RNE\s*:?\s*\d+", texto)
    rnpa = re.findall(r"RNPA\s*:?\s*\d+", texto)
    return rne, rnpa

# Analiza el texto con el modelo de lenguaje local (ollama)
def analizar_texto_con_ollama(texto):
    prompt = f"""
    Evaluá si el siguiente rótulo de alimento contiene:
    - Nombre del producto
    - Ingredientes
    - Contenido neto
    - Fecha de vencimiento
    - Lote
    - Datos del elaborador (RNE/RNPA)
    - Información nutricional
    - Leyendas obligatorias como \"SIN TACC\"

    Texto del rótulo:
    {texto}

    Respondé en JSON indicando qué elementos están presentes y cuáles faltan.
    """
    process = subprocess.Popen(
        ['ollama', 'run', 'mistral'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    output, error = process.communicate(input=prompt)
    return output

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        archivo = request.files['imagen']
        if archivo:
            ruta = os.path.join(app.config['UPLOAD_FOLDER'], archivo.filename)
            archivo.save(ruta)
            texto = extraer_texto(ruta)
            nutricional = analizar_nutricional(texto)
            rne, rnpa = validar_rne_rnpa(texto)
            resultado = analizar_texto_con_ollama(texto)
            limpiar_uploads()
            return render_template('resultado.html', texto=texto, resultado=resultado, nutricional=nutricional, rne=rne, rnpa=rnpa)
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
