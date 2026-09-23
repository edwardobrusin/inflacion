import subprocess
import sys

def run_script(script_path):
    result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(1)

def main():
    scripts = [
        "scripts/consulta_ccif.py",
        "scripts/clean_pond_v2.py",
        "scripts/inf_inc_v2.py",
        "scripts/generar_pdf.py",
        "scripts/send_whatsapp.py"
    ]
    for script in scripts:
        run_script(script)

if __name__ == "__main__":
    main()