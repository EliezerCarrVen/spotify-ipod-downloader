import os
from ytmusicapi import YTMusic
import yt_dlp
import time
import random

class YouTubeDownloader:
    def __init__(self, download_dir='downloads'):
        self.yt = YTMusic()
        self.download_dir = download_dir
        self.browser_cookies_failed = False
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

    def handle_cookie_error(self, err_msg):
        if not self.browser_cookies_failed:
            print("\n[!] ERROR DE COOKIES: yt-dlp no pudo descifrar las cookies del navegador (DPAPI / App-Bound Encryption).")
            print("    Para solucionarlo:")
            print("    1. Instala una extensión en tu navegador (ej: 'Get cookies.txt LOCALLY') y exporta las cookies de YouTube a un archivo 'cookies.txt' en esta carpeta.")
            print("    2. O cambia el navegador a uno no-Chromium como Firefox en tu archivo .env (YT_DLP_COOKIES_FROM_BROWSER=firefox) y loguéate en YouTube allí.")
            print("    Se desactivarán las cookies del navegador para el resto de la sesión para evitar bloqueos y lentitud.\n")
            self.browser_cookies_failed = True

    def get_ydl_opts(self, extra_opts=None):
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        if extra_opts:
            ydl_opts.update(extra_opts)
            
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
            if cookies_browser and not self.browser_cookies_failed:
                ydl_opts['cookiesfrombrowser'] = (cookies_browser, None, None, None)
        return ydl_opts

    def search_song(self, title, artist):
        """Busca en YouTube Music la versión de estudio (Audio) de la canción"""
        query = f"{title} {artist}"
        
        # Pequeña pausa aleatoria para no saturar ytmusicapi y evadir detección de bots
        time.sleep(random.uniform(0.5, 1.5))
        
        try:
            results = self.yt.search(query, filter="songs", limit=1)
            if not results:
                return None
            return results[0]['videoId']
        except Exception as e:
            print(f"  [Aviso] Error en YTMusic API (¿Posible bloqueo de bot?): {e}")
            print(f"  [Rescate] Usando yt-dlp nativo para buscar: {query}")
            return f"ytsearch1:{query}"

    def download_m4a(self, video_id, spotify_id):
        """Descarga el audio de YT Music en M4A 256kbps usando yt-dlp"""
        output_template = os.path.join(self.download_dir, f"{spotify_id}.%(ext)s")
        
        # El archivo final será spotify_id.m4a
        final_path = os.path.join(self.download_dir, f"{spotify_id}.m4a")
        
        if os.path.exists(final_path):
            return final_path

        ydl_opts = self.get_ydl_opts({
            'format': 'bestaudio[ext=m4a]/bestaudio',
            'outtmpl': output_template,
            'remote_components': ['ejs:github'],
        })

        try:
            # Si video_id es una URL completa o una instrucción de búsqueda de yt-dlp (ytsearch, scsearch)
            if video_id.startswith("http://") or video_id.startswith("https://") or ":" in video_id:
                url = video_id
            else:
                url = f"https://www.youtube.com/watch?v={video_id}"
                
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
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
            err_msg = str(e)
            print(f"Error descargando {video_id}: {err_msg}")
            if "DPAPI" in err_msg or "Failed to decrypt" in err_msg or "cookie" in err_msg.lower():
                self.handle_cookie_error(err_msg)
            return None

    def get_library_playlists(self):
        """Obtiene las playlists guardadas en la cuenta de YouTube usando cookies o navegador"""
        ydl_opts = self.get_ydl_opts({
            'extract_flat': True,
        })

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
            err_msg = str(e)
            print(f"Error al obtener tus playlists de YouTube: {err_msg}")
            if "DPAPI" in err_msg or "Failed to decrypt" in err_msg or "cookie" in err_msg.lower():
                self.handle_cookie_error(err_msg)
            return []

    def download_video(self, url, spotify_id):
        """Descarga un video en formato MP4 optimizado para iOS 8 (H.264 + AAC)"""
        filename_template = os.path.join(self.download_dir, f"{spotify_id}.%(ext)s")
        
        # Para iOS 8 (iPod Touch 5) y VLC, lo mejor es mp4 con h264 y aac.
        # Limitamos a 1080p máximo para asegurar reproducción fluida.
        ydl_opts = self.get_ydl_opts({
            'format': 'bestvideo[ext=mp4][height<=1080][vcodec^=avc1]+bestaudio[ext=m4a]/best[ext=mp4][height<=1080]/best',
            'outtmpl': filename_template,
            'merge_output_format': 'mp4',
        })
        
        try:
            import yt_dlp
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                final_filename = ydl.prepare_filename(info)
                
                # yt-dlp might change extension to mp4 after merging
                if not final_filename.endswith('.mp4'):
                    base = os.path.splitext(final_filename)[0]
                    if os.path.exists(base + '.mp4'):
                        final_filename = base + '.mp4'
                        
                return final_filename
        except Exception as e:
            err_msg = str(e)
            print(f"Error descargando video {url}: {err_msg}")
            if "DPAPI" in err_msg or "Failed to decrypt" in err_msg or "cookie" in err_msg.lower():
                self.handle_cookie_error(err_msg)
            return None

    def download_podcast(self, url, spotify_id):
        """Descarga un podcast o audio largo en la mejor calidad posible sin interrupciones."""
        filename_template = os.path.join(self.download_dir, f"{spotify_id}.%(ext)s")
        
        ydl_opts = self.get_ydl_opts({
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'outtmpl': filename_template,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'm4a',
                'preferredquality': '192',
            }],
            # Configuración para descargas largas/inestables
            'retries': 10,
            'fragment_retries': 10,
            'extractor_retries': 3,
        })
        
        try:
            import yt_dlp
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                # prepare_filename sometimes gives the pre-processed extension
                base = os.path.splitext(ydl.prepare_filename(info))[0]
                final_filename = base + '.m4a'
                if os.path.exists(final_filename):
                    return final_filename
                return ydl.prepare_filename(info)
        except Exception as e:
            err_msg = str(e)
            print(f"Error descargando podcast {url}: {err_msg}")
            if "DPAPI" in err_msg or "Failed to decrypt" in err_msg or "cookie" in err_msg.lower():
                self.handle_cookie_error(err_msg)
            return None
