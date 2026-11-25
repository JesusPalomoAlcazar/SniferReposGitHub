"""
Vigila las descargas de los assets de las Releases de los repos de config.json
y envía un aviso al móvil (ntfy.sh) cuando el contador sube.

Variables de entorno:
  NTFY_TOPIC    Tema de ntfy al que estás suscrito en el móvil (obligatorio salvo con --dry-run).
  GITHUB_TOKEN  Opcional. En GitHub Actions se pasa solo y sube el límite de la API.

Uso:
  python monitor.py            # comprueba y avisa
  python monitor.py --dry-run  # comprueba y muestra lo que avisaría, sin enviar ni guardar
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path(__file__).parent
CONFIG = BASE / "config.json"
ESTADO = BASE / "estado.json"
DIAS_KEEPALIVE = 30  # GitHub desactiva los cron tras 60 días sin actividad en el repo


def api(url: str):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "repo-download-monitor",
    })
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def contadores(repo: str) -> dict:
    """Devuelve {"tag/archivo": descargas} de todas las releases del repo."""
    resultado, pagina = {}, 1
    while True:
        releases = api(f"https://api.github.com/repos/{repo}/releases?per_page=100&page={pagina}")
        for rel in releases:
            for asset in rel.get("assets", []):
                resultado[f"{rel['tag_name']}/{asset['name']}"] = asset["download_count"]
        if len(releases) < 100:
            return resultado
        pagina += 1


def avisar(topic: str, titulo: str, mensaje: str):
    req = urllib.request.Request(
        f"https://ntfy.sh/{topic}",
        data=mensaje.encode("utf-8"),
        headers={"Title": titulo, "Tags": "inbox_tray"},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=30).close()


def main():
    dry_run = "--dry-run" in sys.argv
    topic = os.environ.get("NTFY_TOPIC", "").strip()
    if not topic and not dry_run:
        sys.exit("Falta la variable de entorno NTFY_TOPIC")

    repos = json.loads(CONFIG.read_text(encoding="utf-8"))["repos"]
    estado = json.loads(ESTADO.read_text(encoding="utf-8")) if ESTADO.exists() else {}
    anterior = estado.get("repos", {})
    nuevo, avisos, errores = {}, [], 0

    for repo in repos:
        try:
            actual = contadores(repo)
        except Exception as e:  # un repo caído no debe parar al resto
            print(f"[ERROR] {repo}: {e}")
            nuevo[repo] = anterior.get(repo, {})
            errores += 1
            continue

        nuevo[repo] = actual
        if repo not in anterior:
            print(f"[NUEVO] {repo}: guardo {len(actual)} assets como punto de partida, sin avisar")
            continue

        for asset, total in actual.items():
            delta = total - anterior[repo].get(asset, 0)
            if delta > 0:
                avisos.append(f"{repo.split('/')[-1]} {asset}: +{delta} (total {total})")

    for linea in avisos:
        print(f"[DESCARGA] {linea}")
    if not avisos:
        print("Sin descargas nuevas")

    if dry_run:
        return

    if avisos:
        n = len(avisos)
        avisar(topic, "Nueva descarga" if n == 1 else f"{n} assets con descargas nuevas", "\n".join(avisos))

    # Guardamos solo si cambian los contadores, o una vez al mes para que GitHub no desactive el cron.
    ahora = datetime.now(timezone.utc)
    ultimo = datetime.fromisoformat(estado.get("keepalive", "2000-01-01T00:00:00+00:00"))
    if nuevo != anterior or ahora - ultimo > timedelta(days=DIAS_KEEPALIVE):
        ESTADO.write_text(
            json.dumps({"keepalive": ahora.isoformat(timespec="seconds"), "repos": nuevo},
                       indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    if errores == len(repos):
        sys.exit("No se pudo consultar ningún repo")


if __name__ == "__main__":
    main()
