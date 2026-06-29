import os
import time
import random
from ytmusicapi import YTMusic
import yt_dlp

class YouTubeDownloader:
    def __init__(self, download_dir='downloads'):
        self.yt = YTMusic()
        self.download_dir = download_dir
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
            
        # Asegurar que Deno esté en el PATH de este proceso (por si la terminal no se ha reiniciado)
        import shutil
        if not shutil.which("deno"):
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
                    user_path = winreg.QueryValueEx(key, "Path")[0]
                    for p in user_path.split(";"):
                        if "Deno" in p and os.path.isdir(p):
                            os.environ["PATH"] = p + os.path.sep + os.environ["PATH"]
                            break
            except Exception:
                pass
            
            # Fallback manual por si acaso
            if not shutil.which("deno"):
                userprofile = os.environ.get("USERPROFILE", "")
                fallback_path = os.path.join(userprofile, r"AppData\Local\Microsoft\WinGet\Packages\DenoLand.Deno_Microsoft.Winget.Source_8wekyb3d8bbwe")
                if os.path.isdir(fallback_path):
                    os.environ["PATH"] = fallback_path + os.path.sep + os.environ["PATH"]

    def search_song(self, title, artist):
        """Busca en YouTube Music la versión de estudio (Audio) de la canción"""
        # Anti-bot: pausa aleatoria entre búsquedas para evitar rate limiting
        time.sleep(random.uniform(0.5, 2.0))
        query = f"{title} {artist}"
        results = self.yt.search(query, filter="songs", limit=1)
        
        if not results:
            return None
            
        return results[0]['videoId']

    def download_m4a(self, video_id, spotify_id):
        """Descarga el audio de YT Music en M4A 256kbps usando yt-dlp"""
        output_template = os.path.join(self.download_dir, f"{spotify_id}.%(ext)s")
        
        # El archivo final será spotify_id.m4a
        final_path = os.path.join(self.download_dir, f"{spotify_id}.m4a")
        
        if os.path.exists(final_path):
            return final_path

        ydl_opts = {
            'format': '141/140/bestaudio[ext=m4a]/bestaudio',
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'remote_components': ['ejs:github'],
            # Anti-bot: medidas para evitar detección de bot por YouTube
            'sleep_interval_requests': 1,      # 1 segundo entre peticiones HTTP
            'extractor_retries': 5,             # Reintentos del extractor
            'fragment_retries': 10,             # Reintentos para fragmentos
            'retries': 5,                       # Reintentos generales
            'socket_timeout': 30,               # Timeout de conexión
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9,es;q=0.8',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            },
        }
        
        # Cargar cookies desde un archivo si existe, o desde el navegador
        if os.path.exists('cookies.txt'):
            # Copiar a un archivo temporal para evitar que yt-dlp lo sobrescriba y borre cookies de sesión
            import shutil
            temp_cookie_path = os.path.join(self.download_dir, 'cookies_temp.txt')
            try:
                shutil.copy('cookies.txt', temp_cookie_path)
                ydl_opts['cookiefile'] = temp_cookie_path
            except Exception:
                ydl_opts['cookiefile'] = 'cookies.txt'
        else:
            cookies_browser = os.getenv('YT_DLP_COOKIES_FROM_BROWSER')
            if cookies_browser:
                ydl_opts['cookiesfrombrowser'] = (cookies_browser, None, None, None)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                url = f"https://www.youtube.com/watch?v={video_id}"
                ydl.download([url])
                
            # Verificar qué archivo se creó físicamente en disco
            for ext in ['m4a', 'webm', 'opus', 'mp4', 'mka']:
                downloaded_file = os.path.join(self.download_dir, f"{spotify_id}.{ext}")
                if os.path.exists(downloaded_file):
                    if ext != 'm4a':
                        # Renombrar a .m4a para compatibilidad
                        os.rename(downloaded_file, final_path)
                    return final_path
            return None
        except Exception as e:
            print(f"Error descargando {video_id}: {str(e)}")
            return None

    def get_library_playlists(self):
        """Obtiene las playlists guardadas en la cuenta de YouTube usando cookies o navegador"""
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
        }
        
        # Cargar cookies desde un archivo si existe, o desde el navegador
        if os.path.exists('cookies.txt'):
            import shutil
            temp_cookie_path = os.path.join(self.download_dir, 'cookies_temp.txt')
            try:
                shutil.copy('cookies.txt', temp_cookie_path)
                ydl_opts['cookiefile'] = temp_cookie_path
            except Exception:
                ydl_opts['cookiefile'] = 'cookies.txt'
        else:
            cookies_browser = os.getenv('YT_DLP_COOKIES_FROM_BROWSER')
            if cookies_browser:
                ydl_opts['cookiesfrombrowser'] = (cookies_browser, None, None, None)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info("https://www.youtube.com/feed/playlists", download=False)
                
            playlists = []
            if 'entries' in info:
                for entry in info['entries']:
                    if entry:
                        playlists.append({
                            'id': entry.get('id'),
                            'name': entry.get('title'),
                            'url': entry.get('url') or f"https://www.youtube.com/playlist?list={entry.get('id')}",
                            'count': entry.get('playlist_count', 0)
                        })
            return playlists
        except Exception as e:
            print(f"Error al obtener tus playlists de YouTube: {str(e)}")
            return []
