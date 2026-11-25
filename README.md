# SniferReposGitHub

Avisa al móvil cuando alguien descarga un archivo de las **Releases** de tus repositorios de GitHub.

Cada 5 minutos un workflow de GitHub Actions consulta el contador de descargas de cada archivo publicado en las Releases de los repos de `config.json`. Si alguno ha subido, envía una notificación con [ntfy.sh](https://ntfy.sh).

## Qué cuenta y qué no

- ✅ Descargas de archivos subidos a una Release (`.exe`, `.zip`, …).
- ❌ Los "Source code (zip/tar.gz)" automáticos y los `git clone`: GitHub no da contador para ellos.
- ❌ Quién descarga: GitHub solo da el número. Los bots y escáneres también suman.
- El aviso puede llegar con unos minutos de retraso: GitHub no garantiza la hora exacta de los cron.

## Puesta en marcha

1. **Móvil:** instala la app **ntfy** (Android o iOS), pulsa **+** y suscríbete a un tema con un nombre difícil de adivinar, por ejemplo `descargas-k39fq2zx`. Cualquiera que conozca el nombre puede leer los avisos.
2. **Repos a vigilar:** edita `config.json` y pon tus repos en formato `usuario/repo`.
3. **Sube esta carpeta** a un repositorio **público** nuevo en GitHub. En un repo público los minutos de Actions son ilimitados.
4. **Secret:** en el repo, ve a *Settings → Secrets and variables → Actions → New repository secret*. Nombre: `NTFY_TOPIC`. Valor: el tema del paso 1.
5. **Primera ejecución:** en *Actions → Monitor de descargas → Run workflow*. Esta primera vez solo guarda los contadores actuales en `estado.json` y no avisa.
6. A partir de ahí se ejecuta solo cada 5 minutos.

Para probar el aviso, descarga tú mismo un archivo de una Release y lanza el workflow a mano.

## Archivos

| Archivo | Para qué |
|---|---|
| `config.json` | Lista de repos a vigilar |
| `monitor.py` | Consulta los contadores, compara y avisa (Python sin dependencias) |
| `estado.json` | Últimos contadores conocidos. Lo genera y actualiza el workflow |
| `.github/workflows/monitor.yml` | Ejecución programada cada 5 minutos |

Al añadir un repo nuevo a `config.json`, la primera pasada guarda sus contadores sin avisar.

## Probar en local

```powershell
python monitor.py --dry-run
```

Muestra qué avisaría, sin enviar nada ni guardar `estado.json`.

## Notas

- GitHub desactiva los cron de un repo tras 60 días sin actividad. Para evitarlo, el script hace un commit de `estado.json` al menos una vez al mes.
- Si un repo da error (por ejemplo, porque lo has renombrado), se salta y se mantienen sus contadores anteriores.
