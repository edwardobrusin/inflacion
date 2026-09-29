import subprocess
import sys
from pathlib import Path

# main_pipeline.py está en scripts/
# ROOT_DIR será la raíz del repositorio
ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT_DIR / "scripts"

def run_script(script_name):
    script_path = SCRIPTS_DIR / script_name

    print(f"\n{'='*50}")
    print(f"▶ Ejecutando: {script_path}")
    print(f"Directorio de trabajo: {ROOT_DIR}")
    print(f"{'='*50}")

    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        cwd=ROOT_DIR  # Importante: ejecutar desde la raíz del repositorio
    )

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