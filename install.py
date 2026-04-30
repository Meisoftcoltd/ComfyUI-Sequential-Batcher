import sys
import subprocess
import os
import shutil

def install_requirements():
    req_file = os.path.join(os.path.dirname(__file__), "requirements.txt")
    if os.path.exists(req_file):
        print("📦 [Sequential Batcher] Instalando dependencias de Python...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_file])
            print("✅ Dependencias de Python instaladas.")
        except Exception as e:
            print(f"❌ Error instalando dependencias: {e}")

def check_and_install_ffmpeg():
    if shutil.which("ffmpeg") is None:
        print("⚠️ [Sequential Batcher] ADVERTENCIA CRÍTICA: FFmpeg NO está instalado.")
        print("⚠️ La extracción de audio en Video Analyzer fallará.")

        if sys.platform.startswith("linux"):
            try:
                print("⚙️ Intentando instalar FFmpeg automáticamente (Linux/WSL)...")
                subprocess.check_call(["sudo", "apt-get", "update"])
                subprocess.check_call(["sudo", "DEBIAN_FRONTEND=noninteractive", "apt-get", "install", "-y", "ffmpeg"])
                print("✅ FFmpeg instalado correctamente.")
            except Exception as e:
                print(f"❌ Falló la instalación automática de FFmpeg: {e}")
                print("👉 EJECUTA MANUALMENTE: sudo apt update && sudo apt install ffmpeg -y")
        elif sys.platform == "win32":
            print("👉 ACCIÓN REQUERIDA: Descarga FFmpeg para Windows y añádelo al PATH.")
    else:
        print("✅ [Sequential Batcher] Motor FFmpeg detectado correctamente.")

if __name__ == "__main__":
    print("🚀 Iniciando configuración de ComfyUI Sequential Batcher...")
    install_requirements()
    check_and_install_ffmpeg()
    print("🎉 Configuración finalizada.")
