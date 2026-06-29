# iPod Sync Studio mk3 · Interfaz y empaquetado EXE

Esta carpeta contiene la integración inicial de la interfaz tipo iTunes para la rama `mk3` del proyecto.

## Archivos principales

- `desktop_app.py`: launcher de escritorio ligero. Sirve la UI desde un servidor local `127.0.0.1` y la abre en el navegador predeterminado.
- `ui/ipod_sync_studio_mk3_desktop_preview.html`: interfaz visual tipo iTunes con todos los modos del script, reproductor integrado y panel de empaquetado.
- `build_exe.py`: script de build con PyInstaller para generar un ejecutable portable.

## Ejecutar la interfaz en desarrollo

Desde la carpeta `mk3`:

```powershell
python desktop_app.py
```

La app abrirá la interfaz en:

```text
http://127.0.0.1:8765/ipod_sync_studio_mk3_desktop_preview.html
```

Puedes cambiar el puerto con:

```powershell
$env:IPOD_SYNC_STUDIO_PORT="8787"
python desktop_app.py
```

## Empaquetar como EXE

1. Instala dependencias:

```powershell
pip install -r requirements.txt
```

2. Ejecuta el build:

```powershell
python build_exe.py
```

3. El ejecutable se generará en:

```text
mk3/dist/iPodSyncStudio-mk3.exe
```

## Próximas mejoras recomendadas

- Conectar los botones de la UI con endpoints locales del backend Python.
- Exponer acciones reales para Spotify, YouTube, tagging, SQLite y SFTP.
- Incluir `ffmpeg` como asset de build si se decide convertir audio a M4A durante el empaquetado.
- Cambiar de navegador externo a ventana embebida con WebView cuando se quiera una experiencia 100% desktop.
