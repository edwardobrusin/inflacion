import subprocess
import sys
import os

def run_script(script_path):
    print(f"\n{'='*50}")
    print(f"▶ Ejecutando: {script_path}")
    print(f"{'='*50}")
    
    result = subprocess.run(
        [sys.executable, script_path],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.abspath(__file__))  # Asegura rutas relativas correctas
    )
    
    # Imprimir stdout y stderr SIEMPRE para debugging en CI
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(f"⚠️ STDERR:\n{result.stderr}", file=sys.stderr)
    
    if result.returncode != 0:
        print(f"❌ FALLÓ: {script_path} (exit code {result.returncode})")
        sys.exit(result.returncode)
    
    print(f"✅ Completado: {script_path}")

def main():
    scripts = [
        "consulta_ccif.py",
        "inf_inc_v2.py",
        "generar_pdf.py",
        "send_whatsapp.py"
    ]
    
    for script in scripts:
        run_script(script)

if __name__ == "__main__":
    main()