from flask import Flask, render_template, request
from PIL import Image
import pytesseract
import os
import subprocess
import re
import shutil
import json
import cv2
import numpy as np

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Limpieza de archivos luego del análisis
def limpiar_uploads():
    shutil.rmtree(UPLOAD_FOLDER)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Extrae el texto de la imagen con preprocesamiento
def extraer_texto(image_path):
    img = cv2.imread(image_path)
    gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binaria = cv2.threshold(gris, 150, 255, cv2.THRESH_BINARY)
    agrandada = cv2.resize(binaria, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_LINEAR)
    temp_path = "temp_ocr.jpg"
    cv2.imwrite(temp_path, agrandada)
    texto = pytesseract.image_to_string(Image.open(temp_path), lang='spa')
    os.remove(temp_path)
    return texto

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

# Detecta sellos de advertencia del rotulado frontal
def detectar_sellos_octogonales(texto):
    sellos = re.findall(r"(EXCESO EN [A-ZÁÉÍÓÚ]+|CONTIENE EDULCORANTES|CONTIENE CAFE[IÍ]NA)", texto, re.IGNORECASE)
    return [sello.upper() for sello in sellos]

# Verifica si ollama está corriendo
def ollama_esta_activo():
    try:
        result = subprocess.run(["pgrep", "-f", "ollama"], stdout=subprocess.PIPE)
        return result.returncode == 0
    except:
        return False

# Usa Mistral para detectar ingredientes agregados
def detectar_agregados_con_mistral(lista_ingredientes):
    prompt = f'''
Dada la siguiente lista de ingredientes, indicá si contiene alguno de los siguientes agregados:

1. Azúcares agregados (como azúcar, jarabes, miel, etc.)
2. Sal o compuestos de sodio agregados
3. Grasas o aceites agregados (incluyendo manteca, margarina, aceite de palma, leche entera en polvo, etc.)

Ingredientes:
{lista_ingredientes}

Respondé en formato JSON con tres claves:
- "azucares_agregados": true/false
- "sodio_agregado": true/false
- "grasas_agregadas": true/false
'''
    process = subprocess.Popen(
        ['ollama', 'run', 'mistral'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    output, _ = process.communicate(input=prompt)
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return {
            "azucares_agregados": False,
            "sodio_agregado": False,
            "grasas_agregadas": False
        }

# Evalúa rotulado frontal en base a ingredientes y composición nutricional
def evaluar_rotulado_frontal(texto):
    resultado = {
        "azucares_agregados": False,
        "sodio_agregado": False,
        "grasas_agregadas": False,
        "exceso_azucares": False,
        "exceso_sodio": False,
        "exceso_grasas_totales": False,
        "exceso_grasas_saturadas": False,
        "exceso_calorias": False,
        "requiere_octogonos": [],
        "leyendas_obligatorias": [],
        "sellos_presentes_en_rotulo": detectar_sellos_octogonales(texto),
        "sellos_faltantes": []
    }

    match = re.search(r"ingredientes[:\s]+(.+?)(informaci[oó]n nutricional|contenido neto|peso neto|fecha de vencimiento|lote|$)", texto, re.IGNORECASE | re.DOTALL)
    lista_ingredientes = match.group(1).strip() if match else texto

    agregados = detectar_agregados_con_mistral(lista_ingredientes)

    # Refuerzo manual para sal
    if "sal" in lista_ingredientes.lower() or "cloruro de sodio" in lista_ingredientes.lower():
        agregados["sodio_agregado"] = True

    # Refuerzo manual para grasas comunes
    grasas_clave = ["aceite", "grasa", "manteca", "margarina", "palma", "coco", "leche entera"]
    if any(g in lista_ingredientes.lower() for g in grasas_clave):
        agregados["grasas_agregadas"] = True

    resultado.update(agregados)

    def extraer_valor(campo):
        match = re.search(rf"{campo}.*?(\d+[\.,]?\d*)", texto, re.IGNORECASE)
        if match:
            return float(match.group(1).replace(',', '.'))
        return 0.0

    azucares = extraer_valor("azúcares")
    sodio = extraer_valor("sodio")
    grasas_totales = extraer_valor("grasas?\s+totales")
    grasas_saturadas = extraer_valor("grasas?\s+saturadas")
    calorias = extraer_valor("energ[íi]a")

    if resultado["azucares_agregados"] and azucares * 4 > calorias * 0.10:
        resultado["exceso_azucares"] = True
        resultado["requiere_octogonos"].append("EXCESO EN AZÚCARES")

    if resultado["sodio_agregado"]:
        if sodio > 300 or (calorias > 0 and sodio / calorias > 1):
            resultado["exceso_sodio"] = True
            resultado["requiere_octogonos"].append("EXCESO EN SODIO")

    if resultado["grasas_agregadas"]:
        if grasas_totales * 9 > calorias * 0.30:
            resultado["exceso_grasas_totales"] = True
            resultado["requiere_octogonos"].append("EXCESO EN GRASAS TOTALES")
        if grasas_saturadas * 9 > calorias * 0.10:
            resultado["exceso_grasas_saturadas"] = True
            resultado["requiere_octogonos"].append("EXCESO EN GRASAS SATURADAS")

    if resultado["requiere_octogonos"] and calorias > 275:
        resultado["exceso_calorias"] = True
        resultado["requiere_octogonos"].append("EXCESO EN CALORÍAS")

    if "edulcorante" in texto.lower():
        resultado["leyendas_obligatorias"].append("Contiene edulcorantes. No recomendable en niños/as.")
    if "cafeína" in texto.lower():
        resultado["leyendas_obligatorias"].append("Contiene cafeína. Evitar en niños/as.")

    resultado["sellos_faltantes"] = list(set(resultado["requiere_octogonos"]) - set(resultado["sellos_presentes_en_rotulo"]))

    return resultado

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
    - Sellos de advertencia de rotulado frontal según Ley de Promoción de la Alimentación Saludable (Ley 27.642):
      - Exceso en azúcares
      - Exceso en grasas totales
      - Exceso en grasas saturadas
      - Exceso en sodio
      - Exceso en calorías
      - Leyendas como \"Contiene edulcorantes\" o \"Contiene cafeína\"

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
    ollama_activo = ollama_esta_activo()
    if request.method == 'POST':
        archivo = request.files['imagen']
        if archivo:
            ruta = os.path.join(app.config['UPLOAD_FOLDER'], archivo.filename)
            archivo.save(ruta)
            texto = extraer_texto(ruta)
            nutricional = analizar_nutricional(texto)
            rne, rnpa = validar_rne_rnpa(texto)
            sellos = detectar_sellos_octogonales(texto)
            rotulado = evaluar_rotulado_frontal(texto)
            resultado = analizar_texto_con_ollama(texto)
            limpiar_uploads()
            return render_template('resultado.html', texto=texto, resultado=resultado, nutricional=nutricional, rne=rne, rnpa=rnpa, sellos=sellos, rotulado=rotulado, ollama_activo=ollama_activo)
    return render_template('index.html', ollama_activo=ollama_activo)

if __name__ == '__main__':
    app.run(debug=True)
