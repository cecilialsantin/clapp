
# 📘 checkLabelApp (clApp)

**checkLabelApp** es una aplicación web construida con **Flask** que permite:

1. Subir una imagen de un rótulo de alimento.
2. Extraer el texto del rótulo con **OCR usando Tesseract**.
3. Validar si cumple con requisitos reglamentarios mediante un **modelo de lenguaje local (Ollama + Mistral)**.
4. Analizar si se incluyen datos nutricionales y los números RNE/RNPA.
5. Mostrar los resultados en una interfaz web moderna con **Bootstrap**.

---

## 🧰 Requisitos

- macOS (idealmente con chip M1/M2)
- Python 3.8+
- Homebrew (para instalar Tesseract y Ollama)
- Entorno virtual llamado `clappenv`
- Acceso a internet para la primera descarga del modelo

---

## ⚙️ Instalación paso a paso

### 1. Crear carpeta y entorno virtual

```bash
mkdir checkLabelApp
cd checkLabelApp
python3 -m venv clappenv
source clappenv/bin/activate
```

### 2. Instalar dependencias de Python

```bash
pip install flask pillow pytesseract
```

O usando el archivo `requirements.txt`:

```
Flask
pytesseract
Pillow
```

---

## 🚀 Instalación de Tesseract y Ollama (⚠️ fuera del entorno virtual)

### 📌 Tesseract OCR (requiere Homebrew):

```bash
brew install tesseract
```

Verificá que funcione con:

```bash
tesseract --version
```

### 📌 Ollama + modelo `mistral`

```bash
brew install ollama
ollama run mistral
```

> Esto descargará el modelo Mistral (~4 GB). Solo lo hace una vez.

---

## 📁 Estructura del proyecto

```
checkLabelApp/
├── app.py
├── templates/
│   ├── index.html
│   └── resultado.html
├── static/
│   └── uploads/
├── requirements.txt
├── README.md
```

---

## 🖼️ Interfaz con Bootstrap

- `index.html`: formulario simple para subir la imagen
- `resuls.html`: muestra el texto extraído, el análisis del modelo, los datos nutricionales y RNE/RNPA detectados

---

## ✅ Ejecutar la app

Con tu entorno `clappenv` activado:

```bash
export FLASK_APP=app.py
flask run
```

Abre en el navegador:  
👉 http://127.0.0.1:5000

---

## 🔍 ¿Qué analiza el sistema?

- Nombre del producto
- Lista de ingredientes
- Contenido neto
- Fecha de vencimiento
- Número de lote
- Información nutricional
- Datos del elaborador (RNE/RNPA)
- Leyendas obligatorias como “SIN TACC”

---

## 🧼 Limpieza automática

Luego del análisis, el archivo subido se borra automáticamente de `static/uploads` para mantener la carpeta limpia.

---

## 💡 Futuras mejoras

- Consulta en línea de validez de RNE/RNPA
- Exportación del informe en PDF
- Registro de auditorías por usuario
