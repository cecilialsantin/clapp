
import subprocess
import shutil

def check_tesseract():
    print("🔍 Verificando Tesseract...")
    if shutil.which("tesseract"):
        version = subprocess.check_output(["tesseract", "--version"], text=True).splitlines()[0]
        print(f"✅ Tesseract instalado: {version}")
    else:
        print("❌ Tesseract no está instalado o no está en el PATH.")

def check_ollama():
    print("\n🔍 Verificando Ollama...")
    if shutil.which("ollama"):
        try:
            models = subprocess.check_output(["ollama", "list"], text=True)
            print(f"✅ Ollama instalado. Modelos disponibles:")
            print(models)
        except subprocess.CalledProcessError as e:
            print("⚠️ Ollama instalado, pero no pudo listar modelos. ¿Está el demonio corriendo?")
    else:
        print("❌ Ollama no está instalado o no está en el PATH.")

def check_mistral():
    print("\n🔍 Probando modelo 'mistral' con Ollama...")
    try:
        output = subprocess.check_output(
            ['ollama', 'run', 'mistral'],
            input='¿Cuál es la capital de Francia?',
            text=True,
            timeout=20
        )
        if 'París' in output or 'Paris' in output:
            print("✅ Mistral respondió correctamente.")
        else:
            print("⚠️ Mistral respondió, pero la respuesta fue inesperada.")
        print(f"🧠 Respuesta parcial: {output[:100]}...")
    except subprocess.TimeoutExpired:
        print("❌ El modelo tardó demasiado. Verificá que Ollama esté bien instalado.")
    except FileNotFoundError:
        print("❌ Ollama no está instalado.")
    except Exception as e:
        print(f"❌ Error al ejecutar el modelo: {e}")

if __name__ == "__main__":
    print("\n📦 Verificación del entorno de checkLabelApp\n")
    check_tesseract()
    check_ollama()
    check_mistral()
