"""
Launcher para Wigolo_chain — un solo comando para arrancar todo.

    python start.py

Levanta:
  1. Verifica que Ollama este corriendo (y lo inicia si no)
  2. wigolo serve (como proceso background en Windows)
  3. chainlit (interfaz del agente)

Al cerrar chainlit (Ctrl+C), limpia todos los procesos automaticamente.
"""

import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.resolve()

# ── Config ──────────────────────────────────────────────────────────
OLLAMA_URL = "http://127.0.0.1:11434"
WIGOLO_URL = "http://127.0.0.1:3333"
WIGOLO_PORT = 3333
STARTUP_TIMEOUT = 30


# ── Node.js / nvm resolver ──────────────────────────────────────────
def _find_node_home() -> Path | None:
    """Encuentra el directorio de Node.js activo (nvm o instalacion directa)."""
    # 1. NVM: buscar en APPDATA/nvm/
    appdata = os.environ.get("APPDATA", "")
    nvm_root = Path(appdata) / "nvm"
    if nvm_root.exists():
        # Intentar leer la version activa desde nvm
        settings = nvm_root / "settings.txt"
        if settings.exists():
            version = None
            for line in settings.read_text(errors="replace").splitlines():
                if line.startswith("root:"):
                    root_path = line.split(":", 1)[1].strip()
                    nvm_root = Path(root_path)
            # Buscar el directorio de version mas reciente
            versions = sorted(
                [d for d in nvm_root.iterdir() if d.is_dir() and d.name.startswith("v")],
                key=lambda d: d.name,
                reverse=True,
            )
            if versions:
                return versions[0]
        # Fallback: buscar versiones directamente
        versions = sorted(
            [d for d in nvm_root.iterdir() if d.is_dir() and d.name.startswith("v")],
            key=lambda d: d.name,
            reverse=True,
        )
        if versions:
            return versions[0]

    # 2. Instalacion directa: Program Files/nodejs/
    for base in [Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "nodejs",
                 Path("C:/Program Files") / "nodejs"]:
        if (base / "npx.cmd").exists():
            return base

    # 3. Buscar en PATH
    for cmd in ["npx.cmd", "npx"]:
        found = _which(cmd)
        if found:
            return found.parent

    return None


def _which(name: str) -> Path | None:
    """Busca un ejecutable en PATH (como shutil.which pero cross-platform)."""
    for path_dir in os.environ.get("PATH", "").split(os.pathsep):
        exe = Path(path_dir) / name
        if exe.is_file():
            return exe
    return None


# ── Helpers ──────────────────────────────────────────────────────────
def is_running(url: str) -> bool:
    """Prueba si un endpoint HTTP responde."""
    try:
        urllib.request.urlopen(url, timeout=2)
        return True
    except Exception:
        return False


def _spawn(args: list[str], **kwargs) -> subprocess.Popen:
    """Spawn con PATH aumentado para incluir Node.js."""
    env = os.environ.copy()
    node_home = _find_node_home()
    if node_home:
        env["PATH"] = str(node_home) + os.pathsep + env.get("PATH", "")
    return subprocess.Popen(args, env=env, **kwargs)


# ── Service starters ─────────────────────────────────────────────────
def start_ollama():
    """Verifica que Ollama este corriendo; lo inicia si no."""
    if is_running(OLLAMA_URL):
        print("  [OK] Ollama ya esta corriendo")
        return None

    print("  Iniciando Ollama...")
    ollama_exe = _which("ollama.exe") or _which("ollama")
    if not ollama_exe:
        print("  [WARN] 'ollama' no encontrado en PATH — ¿esta instalado?")
        return None

    proc = subprocess.Popen(
        [str(ollama_exe), "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )
    for _ in range(STARTUP_TIMEOUT):
        if is_running(OLLAMA_URL):
            print("  [OK] Ollama iniciado")
            return proc
        time.sleep(1)
    print("  [WARN] Ollama no respondio a tiempo")
    return proc


def start_wigolo():
    """Inicia wigolo serve como proceso background."""
    if is_running(f"{WIGOLO_URL}/health"):
        print("  [OK] wigolo daemon ya esta corriendo")
        return None

    print("  Iniciando wigolo daemon...")

    node_home = _find_node_home()
    if not node_home:
        print("  [ERROR] Node.js no encontrado. Instala Node.js >= 20")
        sys.exit(1)

    npx = node_home / "npx.cmd"
    if not npx.exists():
        npx = node_home / "npx"
    if not npx.exists():
        print(f"  [ERROR] npx no encontrado en {node_home}")
        sys.exit(1)

    proc = _spawn(
        [str(npx), "-y", "wigolo", "serve", "--port", str(WIGOLO_PORT), "--host", "127.0.0.1"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
    )

    for i in range(STARTUP_TIMEOUT):
        if is_running(f"{WIGOLO_URL}/health"):
            print("  [OK] wigolo daemon iniciado")
            return proc
        time.sleep(1)
        if i % 5 == 4:
            print(f"  ...esperando wigolo ({i + 1}s)")

    print("  [WARN] wigolo no respondio a tiempo — continuando de todos modos")
    return proc


def cleanup(processes):
    """Detiene todos los procesos lanzados por el launcher."""
    print("\nApagando servicios...")
    for name, proc in processes:
        if proc is None:
            continue
        try:
            proc.terminate()
            proc.wait(timeout=5)
            print(f"  [OK] {name} detenido")
        except Exception:
            try:
                proc.kill()
                print(f"  [OK] {name} forzado")
            except Exception:
                pass


# ── Main ─────────────────────────────────────────────────────────────
def main():
    print("=" * 50)
    print("  Wigolo_chain — Launcher")
    print("=" * 50)

    # Mostrar info de diagnostico
    node_home = _find_node_home()
    if node_home:
        print(f"  Node.js detectado: {node_home}")
    print()

    processes: list[tuple[str, subprocess.Popen | None]] = []

    print("[1/3] Verificando Ollama...")
    p = start_ollama()
    processes.append(("Ollama", p))

    print("[2/3] Iniciando wigolo daemon...")
    p = start_wigolo()
    processes.append(("wigolo", p))

    print("[3/3] Iniciando Chainlit...")
    print()
    print("  Abre http://localhost:8000 en tu navegador")
    print("  Presiona Ctrl+C para detener todo")
    print()

    try:
        subprocess.run(
            ["chainlit", "run", "main.py", "-w"],
            cwd=str(ROOT),
            check=True,
        )
    except KeyboardInterrupt:
        print("\nInterrumpido por el usuario.")
    except subprocess.CalledProcessError:
        print("\nChainlit termino con error.")
    finally:
        cleanup(processes)
        print("\nTodo detenido. ¡Hasta luego!")


if __name__ == "__main__":
    main()
