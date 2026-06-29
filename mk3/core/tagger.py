import requests
from mutagen.mp4 import MP4, MP4Cover

class AudioTagger:
    def __init__(self, temp_dir='downloads'):
        self.temp_dir = temp_dir

    def fetch_lyrics(self, title, artist, album):
        """Busca letras en lrclib.net (gratuito) y devuelve la letra sincronizada o normal"""
        url = "https://lrclib.net/api/search"
        params = {
            'track_name': title,
            'artist_name': artist,
            'album_name': album
        }
        try:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 200:
                results = r.json()
                if results:
                    # Preferimos la letra sincronizada, si no, la normal
                    best_match = results[0]
                    return best_match.get('syncedLyrics') or best_match.get('plainLyrics')
        except Exception:
            # Fallback silencioso si no hay conexión o no se encuentran letras
            return None

    def tag_m4a(self, file_path, title, artist, album, image_url):
        """Aplica los metadatos al archivo M4A usando mutagen"""
        # Descargar carátula
        cover_data = None
        if image_url:
            try:
                r = requests.get(image_url, timeout=10)
                if r.status_code == 200:
                    cover_data = r.content
            except Exception:
                pass
                
        # Buscar letras
        lyrics = self.fetch_lyrics(title, artist, album)

        # Aplicar tags
        try:
            audio = MP4(file_path)
            
            # Mapeo de tags estándar para MP4/M4A (atom keys)
            audio['\xa9nam'] = title
            audio['\xa9ART'] = artist
            audio['\xa9alb'] = album
            
            if lyrics:
                audio['\xa9lyr'] = lyrics
                
            if cover_data:
                # covr es una lista de objetos MP4Cover
                audio['covr'] = [
                    MP4Cover(cover_data, imageformat=MP4Cover.FORMAT_JPEG)
                ]
                
            audio.save()
        except Exception as e:
            print(f"  [Aviso] No se pudieron aplicar metadatos al archivo (contenedor no MP4): {e}")
