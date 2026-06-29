# Guía de Instalación y Configuración: Spotify a iPod Touch (VLC)

¡Excelente! Ahora que tienes el archivo `.ipa` de VLC en tu PC, AppSync en tu iPod y Filza File Manager en tu iPod, estamos listos para realizar la instalación y la primera sincronización.

Sigue estos sencillos pasos:

---

## Paso 1: Instalar VLC en tu iPod Touch usando Filza

Como tienes **AppSync Unified** instalado en tu iPod, puedes instalar cualquier archivo `.ipa` de forma directa usando **Filza File Manager**:

1. **Abrir el Servidor Web de Filza**:
   * Abre **Filza** en tu iPod.
   * Toca el icono de menú o el engranaje abajo (o pulsa el botón del medio/icono de globo) y busca la opción **Servidor Web** (Web Server).
   * Actívalo. Verás que Filza te mostrará una dirección URL IP en tu pantalla, como por ejemplo: `http://192.168.1.15:34567`.
2. **Subir la IPA desde tu PC**:
   * En el navegador web de tu PC (Chrome, Edge, Firefox), introduce esa dirección URL exacta.
   * Esto abrirá una interfaz para ver los archivos de tu iPod. Navega a una carpeta cómoda (por ejemplo, `/var/mobile/Documents/`).
   * Haz clic en **Subir archivo** (Upload) en el navegador y selecciona el archivo `.ipa` de VLC que descargaste en tu PC.
3. **Instalar la app en el iPod**:
   * En la pantalla de tu iPod (dentro de Filza), ve a la carpeta donde subiste el archivo.
   * Toca el archivo `.ipa` de VLC y presiona **Instalar** (Install) en la esquina superior derecha.
   * Espera a que termine el proceso. ¡El icono de VLC aparecerá en la pantalla de inicio de tu iPod!

> [!IMPORTANT]
> **Abre VLC en el iPod por lo menos una vez**. Esto es necesario para que iOS cree las carpetas del contenedor (sandbox) de la aplicación, donde se almacenará la música y las playlists.

---

## Paso 2: Obtener la ruta de almacenamiento de VLC

VLC guarda sus archivos dentro de una carpeta privada del sistema iOS con un identificador único (UUID). Para encontrarlo con Filza:

1. En **Filza**, ve a los **Ajustes** (icono de engranaje en la barra inferior).
2. Entra en **Gestor de archivos** (File manager) y asegúrate de activar la opción **"Mostrar nombre de aplicación"** (Show application name).
3. Sal de ajustes y navega a la ruta:
   `/var/mobile/Containers/Data/Application/`
4. Verás una lista de carpetas con nombres extraños, pero Filza te mostrará el nombre real y el icono debajo. Busca la carpeta de **VLC**.
5. Entra en la carpeta de **VLC** y verás una carpeta llamada **Documents**.
6. Mantén presionado sobre la carpeta **Documents** (o toca la pequeña "i" a la derecha) y copia la **Ruta absoluta** (Absolute path).
   * La ruta será algo similar a: `/var/mobile/Containers/Data/Application/XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX/Documents` (donde las X son letras y números).

---

## Paso 3: Configurar el archivo de configuración `.env` en tu PC

En tu PC, en la carpeta `c:\Users\373r9\Documents\Ipod\`:

1. Haz una copia del archivo `.env.example` y renómbralo a **`.env`** (asegúrate de quitarle el `.example`).
2. Abre el archivo `.env` con un editor de texto (como el Bloc de Notas) y edita los siguientes valores:
   * **`SPOTIPY_CLIENT_ID`** y **`SPOTIPY_CLIENT_SECRET`**:
     * Si no tienes credenciales de Spotify Developer, entra a [Spotify Developer Dashboard](https://developer.spotify.com/dashboard), inicia sesión, haz clic en **Create App**, ponle cualquier nombre y agrega en **Redirect URIs** el valor `http://localhost:8888/callback`. Luego guarda y copia el *Client ID* y *Client Secret*.
   * **`IPOD_IP`**: Coloca la dirección IP local de tu iPod (puedes verla yendo en el iPod a Ajustes > Wi-Fi > pulsando en la "i" de tu red Wi-Fi).
   * **`IPOD_SONGS_PATH`**: Pega la ruta que copiaste en el paso anterior agregando `/Songs` al final. Ejemplo:
     `/var/mobile/Containers/Data/Application/XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX/Documents/Songs`
   * **`IPOD_PLAYLISTS_PATH`**: Pega la ruta que copiaste en el paso anterior agregando `/Playlists` al final. Ejemplo:
     `/var/mobile/Containers/Data/Application/XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX/Documents/Playlists`

---

## Paso 4: Ejecutar el sincronizador

Una vez que tengas configurado el archivo `.env`:

1. Abre PowerShell o el Símbolo del Sistema en tu PC.
2. Navega al directorio del proyecto e instala las dependencias necesarias de Python ejecutando:
   ```powershell
   cd c:\Users\373r9\Documents\Ipod
   pip install -r requirements.txt
   ```
3. Ejecuta el programa principal:
   ```powershell
   python main.py
   ```

### ¿Qué pasará al ejecutarlo?
* **Primera ejecución**: Se abrirá una ventana del navegador de tu PC pidiéndote autorización con tu cuenta de Spotify. Dale permisos y serás redirigido a una página en blanco (o que dará error de conexión); **copia la URL completa de la barra de direcciones de esa página en blanco** y pégala en la terminal de la PC cuando te lo solicite.
* **Descarga y conversión**: El script buscará tus canciones en YouTube Music, las descargará en formato M4A de alta calidad, les pondrá las portadas oficiales, letras de canciones (lyrics) y las subirá automáticamente por Wi-Fi a tu iPod.
* **Sincronización M3U**: Creará listas de reproducción M3U para que no se dupliquen archivos si una canción está en varias playlists.

¡Una vez finalizado, abre VLC en tu iPod, ve a la sección de Playlists y reproduce tu música!
