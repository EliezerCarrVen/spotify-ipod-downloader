import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import re

class SpotifyClient:
    def __init__(self, client_id, client_secret, redirect_uri):
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope="playlist-read-private playlist-read-collaborative user-library-read",
            open_browser=False
        ))

    def get_all_playlists(self):
        """Extrae todas las playlists del usuario iterando a través de la paginación"""
        playlists = []
        results = self.sp.current_user_playlists()
        while results:
            for item in results['items']:
                if item:
                    playlists.append(item)
            if results['next']:
                results = self.sp.next(results)
            else:
                break
        return playlists

    def get_target_playlists(self):
        """Devuelve todas las playlists de la biblioteca. Detecta e identifica los Daily Mixes"""
        all_playlists = self.get_all_playlists()
        
        target_playlists = []
        for pl in all_playlists:
            # Detectar automáticamente si es un Daily Mix
            is_daily_mix = bool(re.search(r'daily mix', pl['name'], re.IGNORECASE))
            target_playlists.append({
                'id': pl['id'],
                'name': pl['name'],
                'url': pl['external_urls']['spotify'],
                'is_daily_mix': is_daily_mix
            })
            
        return target_playlists

    def get_playlist_tracks(self, playlist_id):
        """Obtiene todas las canciones de una playlist determinada"""
        tracks = []
        results = self.sp.playlist_items(playlist_id, additional_types=['track'])
        while results:
            for item in results['items']:
                track = item.get('track')
                # Ignorar episodios de podcast o canciones locales sin ID válido
                if track and track.get('id'):
                    # Obtener la imagen de mayor resolución disponible
                    images = track['album']['images']
                    image_url = images[0]['url'] if images else None
                    
                    tracks.append({
                        'spotify_id': track['id'],
                        'title': track['name'],
                        'artist': track['artists'][0]['name'],
                        'album': track['album']['name'],
                        'image_url': image_url
                    })
            if results['next']:
                results = self.sp.next(results)
            else:
                break
        return tracks

    def get_liked_songs(self):
        """Obtiene todas las canciones que le gustan al usuario (Saved Tracks)"""
        tracks = []
        results = self.sp.current_user_saved_tracks()
        while results:
            for item in results['items']:
                track = item.get('track')
                if track and track.get('id'):
                    images = track['album']['images']
                    image_url = images[0]['url'] if images else None
                    tracks.append({
                        'spotify_id': track['id'],
                        'title': track['name'],
                        'artist': track['artists'][0]['name'],
                        'album': track['album']['name'],
                        'image_url': image_url
                    })
            if results['next']:
                results = self.sp.next(results)
            else:
                break
        return tracks

    def get_album_tracks(self, album_id):
        """Obtiene las canciones de un álbum por su ID"""
        album = self.sp.album(album_id)
        album_name = album['name']
        images = album['images']
        image_url = images[0]['url'] if images else None
        
        tracks = []
        results = self.sp.album_tracks(album_id)
        while results:
            for track in results['items']:
                if track and track.get('id'):
                    tracks.append({
                        'spotify_id': track['id'],
                        'title': track['name'],
                        'artist': track['artists'][0]['name'],
                        'album': album_name,
                        'image_url': image_url
                    })
            if results['next']:
                results = self.sp.next(results)
            else:
                break
        return album_name, tracks

    def get_playlist_details(self, playlist_id):
        """Obtiene el nombre y las canciones de una playlist por su ID"""
        pl = self.sp.playlist(playlist_id)
        pl_name = pl['name']
        tracks = self.get_playlist_tracks(playlist_id)
        return pl_name, tracks

    def get_liked_songs_from_txt(self, txt_path):
        """Carga y mapea canciones de Spotify desde un archivo de texto con enlaces"""
        import json
        import re
        
        cache_file = 'liked_songs_cache.json'
        cache_data = {'run_count': 0, 'tracks': []}
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
            except Exception:
                pass
                
        # Guardar caché en un dict de ID -> track
        cache_dict = {t['spotify_id']: t for t in cache_data.get('tracks', [])}
        
        # Leer el archivo de texto y extraer los IDs
        track_ids = []
        if not os.path.exists(txt_path):
            print(f"  [Error] El archivo {txt_path} no existe.")
            return list(cache_dict.values())
            
        with open(txt_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                # Extraer ID de la URL
                match = re.search(r'/track/([a-zA-Z0-9]{22})', line)
                if match:
                    track_ids.append(match.group(1))
                else:
                    # Si la línea es directamente el ID
                    if len(line) == 22 and line.isalnum():
                        track_ids.append(line)
                        
        print(f"  [Local] Se encontraron {len(track_ids)} enlaces de canciones en '{txt_path}'.")
        
        final_tracks = []
        missing_ids = []
        
        # Mapear con la caché
        for t_id in track_ids:
            if t_id in cache_dict:
                final_tracks.append(cache_dict[t_id])
            else:
                missing_ids.append(t_id)
                
        # Si faltan canciones en la caché, consultarlas a Spotify en bloques de 50 (muy eficiente)
        if missing_ids:
            print(f"  [Spotify API] Consultando metadatos para {len(missing_ids)} canciones nuevas...")
            new_fetched_tracks = []
            
            # Procesar en bloques de 50
            for i in range(0, len(missing_ids), 50):
                chunk = missing_ids[i:i+50]
                try:
                    res = self.sp.tracks(chunk)
                    for track in res['tracks']:
                        if track and track.get('id'):
                            images = track['album']['images']
                            image_url = images[0]['url'] if images else None
                            track_info = {
                                'spotify_id': track['id'],
                                'title': track['name'],
                                'artist': track['artists'][0]['name'],
                                'album': track['album']['name'],
                                'image_url': image_url
                            }
                            new_fetched_tracks.append(track_info)
                            cache_dict[track['id']] = track_info
                except Exception as e:
                    print(f"    [Aviso] Error al consultar metadatos para bloque {i}-{i+50}: {e}")
                    
            print(f"  [Local] Se obtuvieron {len(new_fetched_tracks)} nuevas canciones desde Spotify.")
            
            # Actualizar la caché local
            cache_data['tracks'] = list(cache_dict.values())
            try:
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, indent=4)
            except Exception:
                pass
                
        # Re-armar la lista de canciones en el orden en que venían en el archivo txt
        ordered_tracks = []
        for t_id in track_ids:
            if t_id in cache_dict:
                ordered_tracks.append(cache_dict[t_id])
                
        return ordered_tracks

    def update_liked_songs_file(self, txt_path='spotify_liked_links.txt'):
        """Actualiza el archivo local de 'Me gusta' con canciones nuevas desde Spotify API (incremental)"""
        import re as _re
        
        # Leer IDs existentes del archivo
        existing_ids = set()
        existing_lines = []
        if os.path.exists(txt_path):
            with open(txt_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line_stripped = line.strip()
                    if not line_stripped or line_stripped.startswith('#'):
                        continue
                    existing_lines.append(line.rstrip('\r\n'))
                    match = _re.search(r'/track/([a-zA-Z0-9]{22})', line_stripped)
                    if match:
                        existing_ids.add(match.group(1))
        
        print(f"  [Local] El archivo tiene {len(existing_ids)} canciones registradas.")
        
        # Obtener canciones nuevas desde Spotify (las más recientes primero)
        new_tracks = []
        results = self.sp.current_user_saved_tracks(limit=50)
        found_existing = False
        
        while results and not found_existing:
            for item in results['items']:
                track = item.get('track')
                if track and track.get('id'):
                    if track['id'] in existing_ids:
                        found_existing = True
                        break
                    new_tracks.append(track)
            
            if not found_existing and results['next']:
                results = self.sp.next(results)
            else:
                break
        
        if not new_tracks:
            print(f"  [✓] No hay canciones nuevas. El archivo está actualizado.")
            return len(existing_ids)
        
        print(f"  [Spotify API] Se encontraron {len(new_tracks)} canciones nuevas.")
        
        # Generar líneas para las nuevas canciones
        new_lines = []
        for track in new_tracks:
            artist = track['artists'][0]['name']
            title = track['name']
            url = f"https://open.spotify.com/track/{track['id']}"
            new_lines.append(f"{url} - {artist} - {title}")
        
        total_count = len(existing_ids) + len(new_tracks)
        
        # Reescribir el archivo con las nuevas canciones al inicio
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(f"# Lista de Enlaces de Spotify - {total_count} canciones en 'Me gusta'\n")
            f.write("# Formato: Enlace - Artista - Título\n\n")
            for line in new_lines:
                f.write(f"{line}\n")
            for line in existing_lines:
                f.write(f"{line}\n")
        
        print(f"  [✓] Archivo actualizado: {total_count} canciones ({len(new_tracks)} nuevas agregadas).")
        return total_count

    def create_liked_songs_file(self, txt_path='spotify_liked_links.txt'):
        """Crea el archivo local de 'Me gusta' descargando toda la biblioteca desde Spotify API"""
        print(f"  [Spotify API] Descargando toda tu biblioteca de 'Me gusta'...")
        tracks = self.get_liked_songs()
        
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(f"# Lista de Enlaces de Spotify - {len(tracks)} canciones en 'Me gusta'\n")
            f.write("# Formato: Enlace - Artista - Título\n\n")
            for track in tracks:
                url = f"https://open.spotify.com/track/{track['spotify_id']}"
                f.write(f"{url} - {track['artist']} - {track['title']}\n")
        
        print(f"  [✓] Archivo '{txt_path}' creado con {len(tracks)} canciones.")

