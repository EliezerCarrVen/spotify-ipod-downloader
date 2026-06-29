import spotipy
from spotipy.oauth2 import SpotifyOAuth
import re
import os
import json

class SpotifyClient:
    def __init__(self, client_id, client_secret, redirect_uri):
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope="playlist-read-private playlist-read-collaborative user-library-read user-top-read user-read-recently-played",
            open_browser=False
        ))

    def get_all_playlists(self):
        """Extrae todas las playlists del usuario iterando a través de la paginación"""
        playlists = []
        results = self.sp.current_user_playlists(limit=50)
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
        results = self.sp.playlist_items(playlist_id, additional_types=['track'], limit=100)
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

    def generate_discovery_mix(self):
        """Genera un mix de 50 canciones basadas en el 'Discovery Weekly' o en búsqueda catalogada de sus artistas Top."""
        print("  [Spotify API] Buscando tu playlist oficial de Descubrimiento Semanal...")
        
        # 1. Intentar buscar la playlist oficial "Discovery Weekly" o "Descubrimiento Semanal"
        try:
            results = self.sp.current_user_playlists(limit=50)
            found_playlist_id = None
            found_playlist_name = None
            while results:
                for item in results['items']:
                    if item:
                        name = item['name'].lower()
                        if "discover weekly" in name or "descubrimiento semanal" in name:
                            found_playlist_id = item['id']
                            found_playlist_name = item['name']
                            break
                if found_playlist_id or not results['next']:
                    break
                results = self.sp.next(results)
                
            if found_playlist_id:
                print(f"  [Spotify API] ¡Encontrada playlist oficial: '{found_playlist_name}'! Obteniendo canciones...")
                return self.get_playlist_tracks(found_playlist_id)
        except Exception as e:
            print(f"  [Spotify API] No se pudo escanear tus playlists: {e}")

        # 2. Fallback: Generación personalizada usando Búsqueda catalogada de sus Top Artistas (Bypass de restricción recommendations)
        print("  [Spotify API] Generando Mix personalizado basado en tus Artistas Favoritos (Bypass)...")
        try:
            # Obtener top artistas recientes
            top_artists_items = []
            try:
                top_artists_items = self.sp.current_user_top_artists(limit=10, time_range='short_term')['items']
            except Exception:
                pass
                
            # Si no hay suficientes, extraer de top tracks
            if len(top_artists_items) < 5:
                try:
                    top_tracks = self.sp.current_user_top_tracks(limit=20, time_range='short_term')['items']
                    seen_artists = set()
                    for t in top_tracks:
                        for a in t['artists']:
                            if a['id'] not in seen_artists:
                                seen_artists.add(a['id'])
                                top_artists_items.append({'name': a['name'], 'id': a['id']})
                except Exception:
                    pass

            if not top_artists_items:
                print("  [Spotify API] No hay suficientes datos de escucha para generar recomendaciones.")
                return []

            import random
            random.shuffle(top_artists_items)
            
            # Usar la función mejorada de custom mix que tiene paginación
            artists_to_mix = [a['name'] for a in top_artists_items[:10]]
            return self.generate_custom_discovery_mix(artists=artists_to_mix, track_limit=50)
            
        except Exception as e:
            print(f"  [Error] Falló la generación del mix alternativo: {e}")
            return []


    def get_smart_albums_from_likes(self, liked_tracks):
        """Devuelve una lista de diccionarios con la URL de los álbumes que cumplen los criterios."""
        print("  [Inteligencia] Analizando Álbumes en tus 'Me gusta'...")
        
        try:
            top_artists_req = self.sp.current_user_top_artists(limit=50, time_range='long_term')['items']
            top_artist_names = {a['name'].lower() for a in top_artists_req}
        except Exception:
            top_artist_names = set()
            
        album_counts = {}
        for t in liked_tracks:
            key = (t['album'], t['artist'])
            if key not in album_counts:
                album_counts[key] = 0
            album_counts[key] += 1
            
        albums_to_fetch = []
        for (album_name, artist_name), count in album_counts.items():
            if count >= 3 and artist_name.lower() in top_artist_names:
                for t in liked_tracks:
                    if t['album'] == album_name and t['artist'] == artist_name:
                        albums_to_fetch.append((album_name, artist_name))
                        break
        
        smart_albums = []
        if not albums_to_fetch:
            print("  [Inteligencia] No se detectaron álbumes que cumplan los criterios.")
            return smart_albums
            
        print(f"  [Inteligencia] Se detectaron {len(albums_to_fetch)} álbumes favoritos para descargar por separado.")
        
        for album_name, artist_name in albums_to_fetch:
            try:
                query = f"album:{album_name} artist:{artist_name}"
                res = self.sp.search(q=query, type='album', limit=1)
                if res['albums']['items']:
                    album_id = res['albums']['items'][0]['id']
                    smart_albums.append({
                        'name': f"{album_name} de {artist_name}",
                        'url': f"https://open.spotify.com/album/{album_id}"
                    })
            except Exception as e:
                print(f"      [Error] No se pudo buscar el álbum {album_name}: {e}")
                
        return smart_albums

    def get_liked_songs(self, force_refresh=False):
        """Obtiene todas las canciones que le gustan al usuario (Caché + Delta Sync)"""
        cache_file = 'liked_songs_cache.json'
        cache_data = {'run_count': 0, 'tracks': []}
        
        if os.path.exists(cache_file) and not force_refresh:
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
            except Exception:
                pass
                
        # Si no forzamos refresh, y tenemos caché, revisamos el contador
        if not force_refresh and cache_data.get('tracks'):
            if cache_data['run_count'] < 2:
                cache_data['run_count'] += 1
                print(f"  [Caché] Cargando {len(cache_data['tracks'])} canciones desde la caché local (Ahorrando peticiones a Spotify). Ejecución {cache_data['run_count']}/2 antes del próximo chequeo.")
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, indent=4)
                return cache_data['tracks']
        
        print(f"  [Spotify API] Buscando canciones nuevas en tus 'Me gusta'...")
        new_tracks = []
        cached_ids = {t['spotify_id'] for t in cache_data.get('tracks', [])}
        
        results = self.sp.current_user_saved_tracks(limit=50)
        found_existing = False
        
        while results and not found_existing:
            for item in results['items']:
                track = item.get('track')
                if track and track.get('id'):
                    if track['id'] in cached_ids and not force_refresh:
                        found_existing = True
                        print(f"  [Delta Sync] Se encontró la última canción conocida. Deteniendo búsqueda en Spotify.")
                        break
                        
                    images = track['album']['images']
                    image_url = images[0]['url'] if images else None
                    new_tracks.append({
                        'spotify_id': track['id'],
                        'title': track['name'],
                        'artist': track['artists'][0]['name'],
                        'album': track['album']['name'],
                        'image_url': image_url
                    })
                    
            if results['next'] and not found_existing:
                results = self.sp.next(results)
            else:
                break
                
        # Unir nuevas con viejas
        if found_existing or not force_refresh:
            final_tracks = new_tracks + cache_data.get('tracks', [])
        else:
            final_tracks = new_tracks # Si forzamos refresh completo y no cortamos, sobreescribimos
            
        print(f"  [Caché] Se encontraron {len(new_tracks)} canciones nuevas. Total en 'Me gusta': {len(final_tracks)}.")
        
        # Guardar caché renovada
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump({'run_count': 0, 'tracks': final_tracks}, f, indent=4)
            
        return final_tracks

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

    def generate_custom_discovery_mix(self, artists=None, track_limit=None):
        """
        Genera un mix de descubrimiento basado en una lista de nombres de artistas.
        Si track_limit es None, no hay límite.
        """
        if not artists:
            return []
            
        print(f"  [Spotify API] Generando Mix personalizado para {len(artists)} artistas...")
        
        # Obtener IDs de canciones que ya le gustan al usuario para no recomendarlas
        liked_ids = set()
        try:
            liked = self.get_liked_songs()
            liked_ids = {t['spotify_id'] for t in liked}
        except Exception:
            pass

        discovery_tracks = []
        seen_track_ids = set()
        
        # Si hay límite por artista, podemos calcularlo.
        # Por ejemplo, si el límite es 100 y hay 2 artistas, sacamos 50 de cada uno.
        # Si no hay límite, sacamos hasta 100 de cada uno para no saturar.
        max_per_artist = 100
        if track_limit is not None:
            max_per_artist = max(track_limit // len(artists), 20)

        for artist_name in artists:
            print(f"    - Buscando canciones de: {artist_name}...")
            offset = 0
            artist_tracks_found = 0
            empty_searches = 0
            
            # Buscaremos en bloques de 10 (límite máximo permitido en Dev Mode)
            while True:
                try:
                    query = f"artist:{artist_name}"
                    res = self.sp.search(q=query, type='track', limit=10, offset=offset)
                    search_tracks = res['tracks']['items'] if res and 'tracks' in res else []
                    
                    if not search_tracks:
                        break
                        
                    tracks_added = 0
                    for track in search_tracks:
                        if track and track.get('id'):
                            t_id = track['id']
                            if t_id not in liked_ids and t_id not in seen_track_ids:
                                seen_track_ids.add(t_id)
                                images = track['album']['images']
                                image_url = images[0]['url'] if images else None
                                discovery_tracks.append({
                                    'spotify_id': t_id,
                                    'title': track['name'],
                                    'artist': track['artists'][0]['name'],
                                    'album': track['album']['name'],
                                    'image_url': image_url
                                })
                                tracks_added += 1
                                artist_tracks_found += 1
                                
                    # Romper si conseguimos suficientes o si no hay temas nuevos en esta página
                    if artist_tracks_found >= max_per_artist:
                        break
                    if tracks_added == 0:
                        empty_searches += 1
                        if empty_searches >= 3:
                            break
                            
                    offset += 10
                except Exception as e:
                    print(f"      [Aviso] Error en búsqueda de {artist_name} con offset {offset}: {e}")
                    break
                    
        import random
        random.shuffle(discovery_tracks)
        
        if track_limit is not None:
            return discovery_tracks[:track_limit]
        return discovery_tracks

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
                
        if len(ordered_tracks) < len(track_ids):
            diff = len(track_ids) - len(ordered_tracks)
            print(f"  [Aviso] Se ignoraron {diff} enlaces que eran inválidos, locales o fueron eliminados de Spotify.")
                
        return ordered_tracks


