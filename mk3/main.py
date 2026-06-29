import os
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
from dotenv import load_dotenv
from tqdm import tqdm
from core.database import DatabaseManager
from core.spotify import SpotifyClient
from core.youtube import YouTubeDownloader
from core.tagger import AudioTagger
from core.sync import SyncManager

def main():
    print("\n" + "="*50)
    print("Iniciando Pipeline Musical al iPod (Foobar2000 OTA)")
    print("="*50)
    
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
    
    # 2. Bucle principal del Menú
    while True:
        print("\n" + "-"*40)
        print("¿Qué reproductor usarás en el iPod?")
        print("1. Foobar2000 (Música con playlists .m3u)")
        print("2. MImport / PwnTunes / iTunes nativo (Música, playlists por carpetas)")
        print("3. VLC (Música y Videos)")
        print("4. Salir del programa")
        
        target_player = input("Elige el destino (1-4): ").strip()
        
        if target_player == "4":
            print("\n¡Gracias por usar Antigravity Sync! Hasta pronto.")
            break
            
        if target_player not in ["1", "2", "3"]:
            print("Opción no válida.")
            continue
            
        print("\n¿Qué deseas hacer hoy?")
        print("1. Toda tu biblioteca de Spotify (descargar + sincronizar)")
        print("2. Solo tus canciones que te gustan (descargar + sincronizar)")
        print("3. Descargar desde un enlace directo (Spotify, YouTube, SoundCloud, etc.)")
        print("4. Sincronizar tus playlists de YouTube/YouTube Music")
        print("5. Solo descargar y etiquetar música (sin transferir al iPod)")
        print("6. Solo sincronizar música al iPod (sin descargar nada nuevo)")
        print("7. Forzar actualización completa de 'Me Gusta' de Spotify (Ignorar caché)")
        print("8. Generar y descargar 'Mix de Descubrimiento Semanal' con IA")
        
        if target_player == "3":
            print("9. Descargar Video y enviar a VLC")
            print("10. Descargar Podcast/Audio Largo")
            
        print("11. Restablecer estado de sincronización de BD")
        print("12. Volver a elegir reproductor")
        print("13. Forzar Sincronización Completa de Carpeta Local (Ignorar BD)")
        
        opcion = input("Elige una opción: ").strip()
        
        if opcion == "12":
            continue
        elif opcion == "11":
            print("\n--- Restableciendo estado de sincronización en la base de datos ---")
            db.reset_all_synced_status()
            print("¡Estado de sincronización restablecido con éxito!")
            continue
        elif opcion == "13":
            print("\n--- Iniciando Sincronización Forzada Local ---")
            if target_player == "1":
                remote_songs = os.getenv('IPOD_SONGS_PATH')
            elif target_player == "2":
                remote_songs = os.getenv('IPOD_PWNTUNES_PATH', '/var/mobile/Media/My Music')
            elif target_player == "3":
                remote_songs = os.getenv('IPOD_VLC_PATH', '/var/mobile/Containers/Data/Application/VLC/Documents')
                
            sync = SyncManager(
                ip=os.getenv('IPOD_IP'),
                username=os.getenv('IPOD_USER'),
                password=os.getenv('IPOD_PASSWORD'),
                remote_songs_path=remote_songs,
                remote_playlists_path=remote_songs
            )
            try:
                sync.connect()
                print("\n>>> Escaneando Ipod_mk3/downloads <<<")
                sync.sync_local_directory("downloads")
                
                backup_path = r"C:\Users\373r9\Documents\Ipod_backup\downloads"
                if os.path.exists(backup_path):
                    print("\n>>> Escaneando Ipod_backup/downloads <<<")
                    sync.sync_local_directory(backup_path)
            except Exception as e:
                print(f"Error en sincronización forzada: {e}")
            finally:
                sync.close()
            continue
            
        if target_player != "3" and opcion in ["9", "10"]:
            print("Esta opción es exclusiva para VLC.")
            continue
        
        # Configurar rutas según reproductor
        if target_player == "1":
            remote_songs = os.getenv('IPOD_SONGS_PATH')
            remote_playlists = os.getenv('IPOD_PLAYLISTS_PATH')
        elif target_player == "2":
            remote_songs = os.getenv('IPOD_PWNTUNES_PATH', '/var/mobile/Media/My Music')
            remote_playlists = remote_songs # PwnTunes no usa m3u
        elif target_player == "3":
            # Si no hay ruta específica de VLC en .env, usar default
            remote_songs = os.getenv('IPOD_VLC_PATH', '/var/mobile/Containers/Data/Application/VLC/Documents')
            remote_playlists = remote_songs
            
        # Flags de control
        run_download = True
        run_sync = True
        if opcion == "5":
    
            run_download = True
            run_sync = False
            print("\n¿Qué deseas descargar de fondo?")
            print("1. Toda tu biblioteca de Spotify")
            print("2. Solo tus canciones que te gustan ('Me gusta')")
            print("3. Descargar desde un enlace directo")
            print("4. Sincronizar tus playlists de YouTube/YouTube Music")
            opcion_descarga = input("Elige una opción (1-4): ").strip()
            opcion = opcion_descarga # Reutilizar lógica de inicialización
        elif opcion == "6":
            run_download = False
            run_sync = True
            
        playlists_to_process = []
    
        if run_download:
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
                    use_local_file = False
                    txt_path = "me gusta.txt"
                    if os.path.exists(txt_path):
                        print(f"  [Local] Se detectó '{txt_path}' con enlaces de tus 'Me gusta'.")
                        ans = input("  ¿Deseas cargar tus canciones desde este archivo local? (s/n, por defecto 's'): ").strip().lower()
                        if ans in ('s', 'si', 'y', 'yes', ''):
                            use_local_file = True
                        
                    if use_local_file:
                        print(f"  [Local] Cargando canciones desde '{txt_path}'...")
                        liked_tracks = spotify.get_liked_songs_from_txt(txt_path)
                    else:
                        liked_tracks = spotify.get_liked_songs()
                    
                    if liked_tracks:
                        playlists_to_process.append({
                            'id': 'liked_songs_special',
                            'name': 'Canciones que me gustan',
                            'url': 'https://open.spotify.com/collection/tracks',
                            'type': 'liked',
                            'tracks': liked_tracks
                        })
                        print(f"Se agregaron {len(liked_tracks)} canciones de tus 'Me gusta'.")
                    
                        # Extraer álbumes inteligentes separados
                        smart_albums = spotify.get_smart_albums_from_likes(liked_tracks)
                        for sa in smart_albums:
                            try:
                                album_id = sa['url'].split("/album/")[1].split("?")[0]
                                _, album_tracks = spotify.get_album_tracks(album_id)
                                playlists_to_process.append({
                                    'id': f"smart_album_{album_id}",
                                    'name': f"Álbum: {sa['name']}",
                                    'url': sa['url'],
                                    'type': 'album',
                                    'tracks': album_tracks
                                })
                            except Exception as e:
                                print(f"Error enfilando álbum inteligente {sa['name']}: {e}")
                except Exception as e:
                    print(f"No se pudieron obtener tus 'Me gusta': {str(e)}")
                
            elif opcion in ["2", "7"]:
                # Opción 2 o 7: Solo Me Gusta
                force_refresh = (opcion == "7")
                print("\n--- Obteniendo tus 'Me gusta' de Spotify ---")
            
                liked_tracks = []
                use_local_file = False
                txt_path = "me gusta.txt"
                if os.path.exists(txt_path) and not force_refresh:
                    print(f"  [Local] Se detectó '{txt_path}' con enlaces de tus 'Me gusta'.")
                    ans = input("  ¿Deseas cargar tus canciones desde este archivo local? (s/n, por defecto 's'): ").strip().lower()
                    if ans in ('s', 'si', 'y', 'yes', ''):
                        use_local_file = True
            
                try:
                    if use_local_file:
                        print(f"  [Local] Cargando canciones desde '{txt_path}'...")
                        liked_tracks = spotify.get_liked_songs_from_txt(txt_path)
                    else:
                        if force_refresh:
                            print(">>> MODO FORZAR ACTUALIZACIÓN (Ignorando caché y re-escaneando Spotify) <<<")
                        liked_tracks = spotify.get_liked_songs(force_refresh=force_refresh)
                    
                    if liked_tracks:
                        playlists_to_process.append({
                            'id': 'liked_songs_special',
                            'name': 'Canciones que me gustan',
                            'url': 'https://open.spotify.com/collection/tracks',
                            'type': 'liked',
                            'tracks': liked_tracks
                        })
                        print(f"Se encontraron {len(liked_tracks)} canciones en tus 'Me gusta'.")
                    
                        # Extraer álbumes inteligentes separados
                        smart_albums = spotify.get_smart_albums_from_likes(liked_tracks)
                        for sa in smart_albums:
                            try:
                                album_id = sa['url'].split("/album/")[1].split("?")[0]
                                _, album_tracks = spotify.get_album_tracks(album_id)
                                playlists_to_process.append({
                                    'id': f"smart_album_{album_id}",
                                    'name': f"Álbum: {sa['name']}",
                                    'url': sa['url'],
                                    'type': 'album',
                                    'tracks': album_tracks
                                })
                            except Exception as e:
                                print(f"Error enfilando álbum inteligente {sa['name']}: {e}")
                    else:
                        print("No se encontraron canciones en tus 'Me gusta'.")
                except Exception as e:
                    print(f"Error al obtener tus 'Me gusta': {str(e)}")
                
            elif opcion == "8":
                # Opción 8: Mix de Descubrimiento Semanal / Personalizado
                print("\n--- Generando Mix de Descubrimiento ---")
                print("¿Cómo deseas generar el mix hoy?")
                print("1. Descubrimiento Semanal automático (Usa tu playlist oficial o tus gustos generales)")
                print("2. Seleccionar un artista de tus Favoritos recientes")
                print("3. Escribir nombres de artistas manualmente (separados por comas)")
            
                sub_opc = input("Elige una opción (1-3): ").strip()
            
                artists_to_mix = []
                track_limit = None
            
                if sub_opc == "2":
                    print("\nObteniendo tus artistas favoritos recientes de Spotify...")
                    try:
                        top_artists = spotify.sp.current_user_top_artists(limit=15, time_range='short_term')['items']
                        if top_artists:
                            print("\nElige uno o más artistas (escribe sus números separados por comas, ej: 1,3,5):")
                            for idx, a in enumerate(top_artists):
                                print(f"{idx + 1}. {a['name']}")
                            choices = input("Elige artistas: ").strip()
                            if choices:
                                selected_indices = [int(x.strip()) - 1 for x in choices.split(",") if x.strip().isdigit()]
                                for idx in selected_indices:
                                    if 0 <= idx < len(top_artists):
                                        artists_to_mix.append(top_artists[idx]['name'])
                        else:
                            print("No se encontraron suficientes datos de escucha. Escribe los artistas manualmente.")
                            sub_opc = "3"
                    except Exception as e:
                        print(f"Error obteniendo favoritos: {e}. Pasando a modo manual.")
                        sub_opc = "3"
                    
                if sub_opc == "3":
                    ans = input("\nEscribe el o los artistas separados por comas (ej: Joji, Coldplay, Peso Pluma): ").strip()
                    if ans:
                        artists_to_mix = [x.strip() for x in ans.split(",") if x.strip()]
                    
                # Generar el mix correspondiente
                try:
                    if sub_opc in ["2", "3"] and artists_to_mix:
                        limit_input = input("\n¿Cuántas canciones deseas en total? (Ingresa un número, o Enter para obtener todas las disponibles): ").strip()
                        if limit_input.isdigit():
                            track_limit = int(limit_input)
                    
                        discovery_tracks = spotify.generate_custom_discovery_mix(artists_to_mix, track_limit=track_limit)
                    else:
                        # Opción 1: Automático
                        discovery_tracks = spotify.generate_discovery_mix()
                    
                    if discovery_tracks:
                        playlists_to_process.append({
                            'id': 'discovery_mix_special',
                            'name': 'Mix de Descubrimiento Semanal',
                            'url': 'https://open.spotify.com/',
                            'type': 'playlist',
                            'tracks': discovery_tracks
                        })
                        print(f"¡Mix generado con éxito! Se añadieron {len(discovery_tracks)} canciones nuevas.")
                    else:
                        print("No se pudo generar el mix de descubrimiento.")
                except Exception as e:
                    print(f"Error al generar el Mix de Descubrimiento: {str(e)}")

                
            elif opcion == "3":
                # Opción 3: Desde un enlace directo (Spotify o genérico por yt-dlp)
                url = input("\nIngresa el enlace (Spotify Album/Playlist, YouTube, SoundCloud, Bandcamp, etc.): ").strip()
            
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
                        continue
                    else:
                        print("Enlace de Spotify no reconocido. Debe ser un álbum o playlist.")
                        continue
                else:
                    # Descargador genérico usando yt-dlp para otras plataformas
                    print("\nObteniendo información de la plataforma usando yt-dlp...")
                    try:
                        import yt_dlp
                        ydl_opts = yt.get_ydl_opts({'extract_flat': True})
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            info = ydl.extract_info(url, download=False)
                        
                        if 'entries' in info:
                            playlist_name = info.get('title', 'Lista Descargada')
                            tracks = []
                            for entry in info['entries']:
                                if entry:
                                    tracks.append({
                                        'spotify_id': f"generic_{entry.get('id')}",
                                        'title': entry.get('title'),
                                        'artist': entry.get('uploader') or entry.get('artist') or 'Otros',
                                        'album': playlist_name,
                                        'image_url': None,
                                        'url': entry.get('url')
                                    })
                            playlists_to_process.append({
                                'id': f"generic_playlist_{info.get('id')}",
                                'name': playlist_name,
                                'url': url,
                                'type': 'generic_playlist',
                                'tracks': tracks
                            })
                        else:
                            video_id = info.get('id')
                            video_title = info.get('title')
                            uploader = info.get('uploader') or info.get('artist') or 'Otros'
                            playlists_to_process.append({
                                'id': 'generic_single_downloads',
                                'name': 'Descargas Genéricas',
                                'url': url,
                                'type': 'generic_single',
                                'tracks': [{
                                    'spotify_id': f"generic_{video_id}",
                                    'title': video_title,
                                    'artist': uploader,
                                    'album': 'Descargas Genéricas',
                                    'image_url': None,
                                    'url': url
                                }]
                            })
                    except Exception as e:
                        err_msg = str(e)
                        print(f"Error al obtener información de la plataforma: {err_msg}")
                        if "DPAPI" in err_msg or "Failed to decrypt" in err_msg or "cookie" in err_msg.lower():
                            yt.handle_cookie_error(err_msg)
                        continue
                    
            elif opcion == "4":
                # Opción 4: Playlists de YouTube del usuario
                print("\n--- Obteniendo tus Playlists de YouTube ---")
                playlists = yt.get_library_playlists()
                if not playlists:
                    print("No se encontraron playlists de YouTube o la sesión no está activa.")
                    continue
                
                print(f"\nSe encontraron {len(playlists)} playlists en tu cuenta:")
                for idx, pl in enumerate(playlists):
                    count_str = f" ({pl['count']} canciones)" if pl.get('count') else ""
                    print(f"{idx + 1}. {pl['name']}{count_str}")
                
                try:
                    choice = input(f"\nElige el número de la playlist a sincronizar (1-{len(playlists)}) o Enter para cancelar: ").strip()
                    if not choice:
                        continue
                    idx = int(choice) - 1
                    if idx < 0 or idx >= len(playlists):
                        print("Opción inválida.")
                        continue
                    
                    selected = playlists[idx]
                    print(f"\nObteniendo canciones de la playlist: {selected['name']}...")
                
                    # Extraer canciones usando yt-dlp
                    import yt_dlp
                    ydl_opts = yt.get_ydl_opts({
                        'extract_flat': True,
                        'remote_components': ['ejs:github'],
                    })
                    
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
                    err_msg = str(e)
                    print(f"Error procesando la playlist de YouTube: {err_msg}")
                    if "DPAPI" in err_msg or "Failed to decrypt" in err_msg or "cookie" in err_msg.lower():
                        yt.handle_cookie_error(err_msg)
                    continue
            elif opcion == "9":
                url = input("\nIngresa el enlace del Video (YouTube, TikTok, Twitter, etc.): ").strip()
                print("¿Dónde deseas guardar el video?")
                print("1. Enviar a VLC en el iPod")
                print("2. Guardar solo en el Disco Local (PC)")
                dest = input("Elige (1-2): ").strip()
            
                print("\n--- Descargando video en calidad optimizada para iOS 8 ---")
                import uuid
                vid_id = f"video_{uuid.uuid4().hex[:8]}"
                local_path = yt.download_video(url, vid_id)
                if local_path:
                    print(f"\n¡Video descargado exitosamente en: {local_path}!")
                    if dest == "1":
                        remote_vlc_path = os.getenv('IPOD_VLC_PATH')
                        if not remote_vlc_path:
                            print("Error: IPOD_VLC_PATH no está definido en el archivo .env. No se pudo enviar a VLC.")
                        else:
                            print("\n--- Iniciando Transferencia a VLC ---")
                            sync = SyncManager(
                                ip=os.getenv('IPOD_IP'),
                                port=os.getenv('IPOD_PORT', 22),
                                username=os.getenv('IPOD_USER', 'root'),
                                password=os.getenv('IPOD_PASSWORD', 'alpine'),
                                remote_songs_path=os.getenv('IPOD_SONGS_PATH'),
                                remote_playlists_path=os.getenv('IPOD_PLAYLISTS_PATH')
                            )
                            sync.sync_video_to_vlc(local_path, remote_vlc_path)
                            sync.close()
                continue
            
            elif opcion == "10":
                url = input("\nIngresa el enlace del Podcast/Audio Largo: ").strip()
                print("\n--- Descargando Podcast optimizado ---")
                import uuid
                pod_id = f"podcast_{uuid.uuid4().hex[:8]}"
                local_path = yt.download_podcast(url, pod_id)
                if local_path:
                    print(f"\n¡Podcast descargado exitosamente en: {local_path}!")
                    print("El archivo ha sido guardado localmente en tu carpeta de descargas.")
                continue
            
            else:
                print("Opción no válida.")
                continue

            if not playlists_to_process and run_download:
                print("No hay nada que procesar en este momento.")
                continue

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
            
                already_downloaded_count = len(tracks) - len(tracks_to_download)
            
                if not tracks_to_download:
                    print(f"  [✓] Todas las {len(tracks)} canciones ya están descargadas en tu PC.")
                else:
                    if already_downloaded_count > 0:
                        print(f"  [✓] {already_downloaded_count} canciones ya estaban descargadas (reutilizando archivos).")
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
                            elif spotify_id.startswith("generic_"):
                                video_id = track.get('url') or spotify_id
                            else:
                                video_id = yt.search_song(title, artist)
                            
                            if video_id:
                                local_path = yt.download_m4a(video_id, spotify_id)
                            
                                # Fallback a SoundCloud si falla YouTube (por restricción de edad +18 u otro error)
                                if not local_path and not spotify_id.startswith("youtube_") and not spotify_id.startswith("generic_"):
                                    search_title = title or "Audio"
                                    search_artist = artist or ""
                                    pbar.write(f"  [Rescate] Falló YouTube (posible restricción +18) para '{search_title}'. Buscando en SoundCloud...")
                                    sc_query = f"scsearch1:{search_title} {search_artist}".strip()
                                    local_path = yt.download_m4a(sc_query, spotify_id)

                                if local_path:
                                    tagger.tag_m4a(local_path, title, artist, album, track['image_url'])
                                    db.update_song_local_path(spotify_id, local_path)
                                else:
                                    pbar.write(f"  [Error] No se pudo descargar '{title}' ni en YouTube ni en SoundCloud.")
                            else:
                                pbar.write(f"  [Error] No se encontró resultado de búsqueda para {title}.")
                        except Exception as e:
                            pbar.write(f"  [Error Grave] Fallo procesando '{track.get('title', 'Desconocido')}': {str(e)}")

        # 4. Sincronización OTA al iPod
        if run_sync:
            print("\n--- Iniciando Transferencia al iPod ---")
            sync = SyncManager(
                ip=os.getenv('IPOD_IP'),
                username=os.getenv('IPOD_USER'),
                password=os.getenv('IPOD_PASSWORD'),
                remote_songs_path=remote_songs,
                remote_playlists_path=remote_playlists
            )
            
            try:
                sync.connect()
            
                # Subir canciones pendientes (Delta Sync)
                unsynced = db.get_unsynced_songs()
                if unsynced:
                    print(f"\nSincronizando {len(unsynced)} canciones nuevas al iPod Touch...")
                    pbar_sync = tqdm(unsynced, desc="Subiendo al iPod", unit="trk", dynamic_ncols=True)
                    for song in pbar_sync:
                        local_path = song['local_path']
                        filename = f"{song['spotify_id']}.m4a"
                        pbar_sync.set_postfix_str(f"{song['artist'][:15]} - {song['title'][:15]}")
                    
                        remote_path = sync.upload_song(local_path, filename, silent=True)
                        db.update_song_synced_status(song['spotify_id'], remote_path)
                else:
                    print("\nTodas las canciones están actualizadas en el iPod.")
                
                # Generar y subir Playlists
                print("\nActualizando Playlists...")
                all_db_playlists = db.get_all_playlists()
                for pl in all_db_playlists:
                    playlist_songs = db.get_playlist_songs(pl['playlist_id'])
                    if playlist_songs:
                        if target_player == "2":
                            # PwnTunes: crear carpetas
                            sync.upload_pwntunes_playlist(pl['name'], playlist_songs)
                        else:
                            # Foobar/VLC: crear .m3u
                            sync.upload_playlist_m3u(pl['name'], playlist_songs)
                    
                print("\n¡Sincronización Completada con Éxito!")
            
            except Exception as e:
                print(f"\nError en la sincronización: {str(e)}")
            finally:
                sync.close()
            
            # Volver al inicio del bucle para preguntar de nuevo
            print("\n--- Operación finalizada ---")

if __name__ == "__main__":
    main()
