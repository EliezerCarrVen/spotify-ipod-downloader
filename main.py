import os
import time
import random
from dotenv import load_dotenv
from tqdm import tqdm
from core.database import DatabaseManager
from core.spotify import SpotifyClient
from core.youtube import YouTubeDownloader
from core.tagger import AudioTagger
from core.sync import SyncManager

def _obtener_canciones_me_gusta(spotify):
    """Obtiene las canciones de 'Me gusta' usando caché local o la API de Spotify"""
    txt_path = "spotify_liked_links.txt"
    
    if os.path.exists(txt_path):
        print(f"  [Local] Se detectó '{txt_path}' con tus canciones de 'Me gusta'.")
        print(f"    1. Usar el archivo local tal cual")
        print(f"    2. Actualizar el archivo con nuevos 'Me gusta' desde Spotify (recomendado)")
        print(f"    3. Ignorar archivo y consultar todo desde Spotify API")
        sub_opcion = input("    Elige (1-3, por defecto '2'): ").strip()
        
        if sub_opcion == '3':
            return spotify.get_liked_songs()
        elif sub_opcion == '2' or sub_opcion == '':
            spotify.update_liked_songs_file(txt_path)
            return spotify.get_liked_songs_from_txt(txt_path)
        else:
            return spotify.get_liked_songs_from_txt(txt_path)
    else:
        print(f"  [Info] No se encontró archivo local '{txt_path}'.")
        ans = input("  ¿Crear archivo local para futuras ejecuciones? (s/n, por defecto 's'): ").strip().lower()
        if ans in ('n', 'no'):
            return spotify.get_liked_songs()
        else:
            spotify.create_liked_songs_file(txt_path)
            return spotify.get_liked_songs_from_txt(txt_path)

def main():
    print("Iniciando Pipeline de Spotify a iPod (VLC OTA)")
    
    # Cargar configuración
    load_dotenv()
    
    # 1. Inicializar Módulos
    db = DatabaseManager()
    
    spotify = SpotifyClient(
        client_id=os.getenv('SPOTIPY_CLIENT_ID'),
        client_secret=os.getenv('SPOTIPY_CLIENT_SECRET'),
        redirect_uri=os.getenv('SPOTIPY_REDIRECT_URI')
    )
    
    yt = YouTubeDownloader(download_dir='downloads')
    tagger = AudioTagger(temp_dir='downloads')
    
    # 2. Menú de opciones
    print("\n¿Qué deseas sincronizar hoy?")
    print("1. Toda tu biblioteca de Spotify (Playlists + Canciones que te gustan)")
    print("2. Solo tus canciones que te gustan ('Me gusta')")
    print("3. Descargar desde un enlace directo (Álbum o Playlist de Spotify, o Video/Lista de YouTube)")
    print("4. Sincronizar tus playlists de YouTube/YouTube Music")
    print("5. Restablecer estado de sincronización (Fuerza la resubida de toda tu música al iPod)")
    
    opcion = input("Elige una opción (1-5): ").strip()
    
    if opcion == "5":
        print("\n--- Restableciendo estado de sincronización en la base de datos ---")
        db.reset_all_synced_status()
        print("¡Estado de sincronización restablecido con éxito!")
        print("Ahora puedes ejecutar la sincronización de música para resubir tus canciones al iPod.")
        return
        
    playlists_to_process = []

    
    if opcion == "1":
        # Opción 1: Toda la biblioteca
        print("\n--- Obteniendo Playlists de Spotify ---")
        playlists = spotify.get_target_playlists()
        print(f"Se encontraron {len(playlists)} playlists en tu biblioteca.")
        
        # Procesar playlists estándar
        for pl in playlists:
            playlists_to_process.append({
                'id': pl['id'],
                'name': pl['name'],
                'url': pl['url'],
                'type': 'playlist'
            })
            
        # Obtener y agregar "Canciones que te gustan"
        print("\n--- Obteniendo tus 'Me gusta' de Spotify ---")
        try:
            liked_tracks = _obtener_canciones_me_gusta(spotify)
                
            if liked_tracks:
                playlists_to_process.append({
                    'id': 'liked_songs_special',
                    'name': 'Canciones que me gustan',
                    'url': 'https://open.spotify.com/collection/tracks',
                    'type': 'liked',
                    'tracks': liked_tracks
                })
                print(f"Se agregaron {len(liked_tracks)} canciones de tus 'Me gusta'.")
        except Exception as e:
            print(f"No se pudieron obtener tus 'Me gusta': {str(e)}")
            
    elif opcion == "2":
        # Opción 2: Solo Me Gusta
        print("\n--- Obteniendo tus 'Me gusta' de Spotify ---")
        
        try:
            liked_tracks = _obtener_canciones_me_gusta(spotify)
                
            if liked_tracks:
                playlists_to_process.append({
                    'id': 'liked_songs_special',
                    'name': 'Canciones que me gustan',
                    'url': 'https://open.spotify.com/collection/tracks',
                    'type': 'liked',
                    'tracks': liked_tracks
                })
                print(f"Se encontraron {len(liked_tracks)} canciones en tus 'Me gusta'.")
            else:
                print("No se encontraron canciones en tus 'Me gusta'.")
        except Exception as e:
            print(f"Error al obtener tus 'Me gusta': {str(e)}")
            
    elif opcion == "3":
        # Opción 3: Desde un enlace
        url = input("\nIngresa el enlace (Spotify Album/Playlist o YouTube Video/Lista): ").strip()
        
        if "spotify.com" in url:
            if "/album/" in url:
                album_id = url.split("/album/")[1].split("?")[0]
                print(f"\nObteniendo información del Álbum de Spotify...")
                try:
                    album_name, tracks = spotify.get_album_tracks(album_id)
                    playlists_to_process.append({
                        'id': f"spotify_album_{album_id}",
                        'name': album_name,
                        'url': url,
                        'type': 'album',
                        'tracks': tracks
                    })
                except Exception as e:
                    print(f"Error al obtener el álbum: {str(e)}")
            elif "/playlist/" in url:
                playlist_id = url.split("/playlist/")[1].split("?")[0]
                print(f"\nObteniendo información de la Playlist de Spotify...")
                try:
                    playlist_name, tracks = spotify.get_playlist_details(playlist_id)
                    playlists_to_process.append({
                        'id': playlist_id,
                        'name': playlist_name,
                        'url': url,
                        'type': 'playlist_url',
                        'tracks': tracks
                    })
                except Exception as e:
                    print(f"Error al obtener la playlist: {str(e)}")
            else:
                print("Enlace de Spotify no reconocido. Debe ser un álbum o playlist.")
                return
                
        elif "youtube.com" in url or "youtu.be" in url:
            print("\nObteniendo información de YouTube...")
            try:
                import yt_dlp
                ydl_opts = {'quiet': True, 'extract_flat': True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                if 'entries' in info:
                    playlist_name = info.get('title', 'YouTube Playlist')
                    tracks = []
                    for entry in info['entries']:
                        if entry:
                            # Mapeamos a canciones simuladas
                            tracks.append({
                                'spotify_id': f"youtube_{entry.get('id')}",
                                'title': entry.get('title'),
                                'artist': entry.get('uploader', 'YouTube'),
                                'album': playlist_name,
                                'image_url': None
                            })
                    playlists_to_process.append({
                        'id': f"youtube_playlist_{info.get('id')}",
                        'name': playlist_name,
                        'url': url,
                        'type': 'youtube_playlist',
                        'tracks': tracks
                    })
                else:
                    video_id = info.get('id')
                    video_title = info.get('title')
                    uploader = info.get('uploader', 'YouTube')
                    playlists_to_process.append({
                        'id': 'youtube_single_downloads',
                        'name': 'Descargas de YouTube',
                        'url': 'https://youtube.com',
                        'type': 'youtube_single',
                        'tracks': [{
                            'spotify_id': f"youtube_{video_id}",
                            'title': video_title,
                            'artist': uploader,
                            'album': 'Descargas de YouTube',
                            'image_url': None
                        }]
                    })
            except Exception as e:
                print(f"Error al obtener información de YouTube: {str(e)}")
                return
        else:
            print("Enlace no reconocido. Debe ser de Spotify o YouTube.")
            return
            
    elif opcion == "4":
        # Opción 4: Playlists de YouTube
        print("\n--- Obteniendo tus Playlists de YouTube ---")
        playlists = yt.get_library_playlists()
        if not playlists:
            print("No se encontraron playlists de YouTube o la sesión no está activa.")
            return
            
        print(f"\nSe encontraron {len(playlists)} playlists en tu cuenta:")
        for idx, pl in enumerate(playlists):
            print(f"{idx + 1}. {pl['name']} ({pl['count']} canciones)")
            
        try:
            choice = input(f"\nElige el número de la playlist a sincronizar (1-{len(playlists)}) o Enter para cancelar: ").strip()
            if not choice:
                return
            idx = int(choice) - 1
            if idx < 0 or idx >= len(playlists):
                print("Opción inválida.")
                return
                
            selected = playlists[idx]
            print(f"\nObteniendo canciones de la playlist: {selected['name']}...")
            
            # Extraer las canciones usando yt-dlp
            ydl_opts = {
                'quiet': True,
                'extract_flat': True,
                'remote_components': ['ejs:github'],
            }
            if os.path.exists('cookies.txt'):
                import shutil
                temp_cookie_path = os.path.join(yt.download_dir, 'cookies_temp.txt')
                try:
                    shutil.copy('cookies.txt', temp_cookie_path)
                    ydl_opts['cookiefile'] = temp_cookie_path
                except Exception:
                    ydl_opts['cookiefile'] = 'cookies.txt'
            else:
                cookies_browser = os.getenv('YT_DLP_COOKIES_FROM_BROWSER')
                if cookies_browser:
                    ydl_opts['cookiesfrombrowser'] = (cookies_browser, None, None, None)
                    
            import yt_dlp
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                playlist_info = ydl.extract_info(selected['url'], download=False)
                
            tracks = []
            if 'entries' in playlist_info:
                for entry in playlist_info['entries']:
                    if entry:
                        tracks.append({
                            'spotify_id': f"youtube_{entry.get('id')}",
                            'title': entry.get('title'),
                            'artist': entry.get('uploader', 'YouTube'),
                            'album': selected['name'],
                            'image_url': None
                        })
                        
            playlists_to_process.append({
                'id': f"youtube_playlist_{selected['id']}",
                'name': selected['name'],
                'url': selected['url'],
                'type': 'youtube_playlist',
                'tracks': tracks
            })
            print(f"Se agregaron {len(tracks)} canciones de la playlist '{selected['name']}'.")
        except Exception as e:
            print(f"Error procesando la playlist de YouTube: {str(e)}")
            return
            
    else:
        print("Opción no válida.")
        return
        
    if not playlists_to_process:
        print("No hay nada que procesar. Fin.")
        return

    # 3. Descargar y Procesar Canciones
    for pl in playlists_to_process:
        print(f"\n--- Procesando: {pl['name']} ---")
        db.add_playlist(pl['id'], pl['name'], pl['url'])
        db.clear_playlist_songs(pl['id'])
        
        if 'tracks' in pl:
            tracks = pl['tracks']
        else:
            try:
                tracks = spotify.get_playlist_tracks(pl['id'])
            except Exception as e:
                if "403" in str(e) or (hasattr(e, 'http_status') and e.http_status == 403):
                    print(f"  [Aviso] No tienes permisos para leer '{pl['name']}' (Error 403).")
                    print(f"    * Solución: Duplícala en tu cuenta de Spotify para poder sincronizarla.")
                else:
                    print(f"  [Aviso] No se pudo procesar: {str(e)}")
                continue
                
        print(f"  {len(tracks)} canciones en la lista.")
        
        # Registrar y mapear rápidamente en la base de datos
        for pos, track in enumerate(tracks):
            db.add_song(track['spotify_id'], track['title'], track['artist'], track['album'])
            db.add_song_to_playlist(pl['id'], track['spotify_id'], pos)
            
        # Filtrar canciones que realmente necesitan ser descargadas o resueltas por deduplicación
        tracks_to_download = []
        for track in tracks:
            spotify_id = track['spotify_id']
            song_record = db.get_song(spotify_id)
            file_exists = os.path.exists(song_record['local_path']) if song_record and song_record['local_path'] else False
            
            if not song_record or not song_record['downloaded'] or not file_exists:
                # Deduplicación cruzada por nombre y artista
                existing_download = db.find_downloaded_song_by_title_artist(track['title'], track['artist'])
                existing_exists = os.path.exists(existing_download['local_path']) if existing_download and existing_download['local_path'] else False
                
                if existing_download and existing_exists:
                    db.update_song_local_path(spotify_id, existing_download['local_path'])
                else:
                    tracks_to_download.append(track)
        
        if not tracks_to_download:
            print("  [✓] Todas las canciones ya están descargadas en tu PC.")
        else:
            print(f"  Descargando {len(tracks_to_download)} canciones nuevas...")
            pbar = tqdm(tracks_to_download, desc=f"Descargando [{pl['name'][:20]}]", unit="trk", dynamic_ncols=True)
            
            for track in pbar:
                try:
                    spotify_id = track['spotify_id']
                    title = track['title']
                    artist = track['artist']
                    album = track['album']
                    
                    # Actualizar barra visual
                    pbar.set_postfix_str(f"{artist[:15]} - {title[:20]}")
                    
                    if spotify_id.startswith("youtube_"):
                        video_id = spotify_id.replace("youtube_", "")
                    else:
                        video_id = yt.search_song(title, artist)
                        
                    if video_id:
                        local_path = yt.download_m4a(video_id, spotify_id)
                        if local_path:
                            tagger.tag_m4a(local_path, title, artist, album, track['image_url'])
                            db.update_song_local_path(spotify_id, local_path)
                        else:
                            pbar.write(f"  [Error] No se pudo descargar '{title}' de YouTube Music.")
                    else:
                        pbar.write(f"  [Error] No se encontró resultado de búsqueda para {title}.")
                except Exception as e:
                    pbar.write(f"  [Error Grave] Fallo procesando '{track.get('title', 'Desconocido')}': {str(e)}")
                
                # Anti-bot: pausa aleatoria entre descargas para evitar detección
                time.sleep(random.uniform(1.0, 3.0))
                    
    # 4. Sincronización OTA al iPod
    print("\n--- Iniciando Sincronización OTA (Wi-Fi) al iPod ---")
    sync = SyncManager(
        ip=os.getenv('IPOD_IP'),
        port=os.getenv('IPOD_PORT', 22),
        username=os.getenv('IPOD_USER', 'root'),
        password=os.getenv('IPOD_PASSWORD', 'alpine'),
        remote_songs_path=os.getenv('IPOD_SONGS_PATH'),
        remote_playlists_path=os.getenv('IPOD_PLAYLISTS_PATH')
    )
    
    try:
        sync.connect()
        
        # Subir canciones pendientes (Delta Sync)
        unsynced = db.get_unsynced_songs()
        if unsynced:
            print(f"\nSincronizando {len(unsynced)} canciones nuevas al iPod Touch...")
            pbar_sync = tqdm(unsynced, desc="Subiendo al iPod", unit="trk", dynamic_ncols=True)
            for song in pbar_sync:
                try:
                    local_path = song['local_path']
                    filename = f"{song['spotify_id']}.m4a"
                    pbar_sync.set_postfix_str(f"{song['artist'][:15]} - {song['title'][:15]}")
                    
                    remote_path = sync.upload_song(local_path, filename, silent=True)
                    db.update_song_synced_status(song['spotify_id'], remote_path)
                except Exception as e:
                    pbar_sync.write(f"  [Error SFTP] No se pudo subir '{song.get('title', '?')}': {str(e)}")
        else:
            print("\nTodas las canciones están actualizadas en el iPod.")
            
        # Generar y subir Playlists (.m3u)
        print("\nActualizando archivos de Playlists (.m3u)...")
        all_db_playlists = db.get_all_playlists()
        for pl in all_db_playlists:
            playlist_songs = db.get_playlist_songs(pl['playlist_id'])
            if playlist_songs:
                sync.upload_playlist_m3u(pl['name'], playlist_songs)
                
        print("\n¡Sincronización Completada con Éxito!")
        
    except Exception as e:
        print(f"\nError en la sincronización: {str(e)}")
    finally:
        sync.close()

if __name__ == "__main__":
    main()
