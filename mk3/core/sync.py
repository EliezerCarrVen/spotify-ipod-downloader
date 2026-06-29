import paramiko
import os
import stat

class SyncManager:
    def __init__(self, ip, username, password, remote_songs_path, remote_playlists_path, port=22):
        self.ip = ip
        self.username = username
        self.password = password
        self.port = int(port)
        self.remote_songs_path = remote_songs_path.rstrip('/')
        self.remote_playlists_path = remote_playlists_path.rstrip('/')
        
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.sftp = None

    def connect(self):
        print(f"Conectando al iPod en {self.ip}:{self.port} por SSH...")
        self.ssh.connect(self.ip, port=self.port, username=self.username, password=self.password)
        self.sftp = self.ssh.open_sftp()
        
        # Asegurar que los directorios remotos existen
        self._ensure_remote_dir(self.remote_songs_path)
        self._ensure_remote_dir(self.remote_playlists_path)
        
        # Listar archivos remotos una sola vez para evitar miles de consultas stat individuales
        try:
            self.remote_files = set(self.sftp.listdir(self.remote_songs_path))
            print(f"  [iPod] Detectados {len(self.remote_files)} archivos de música en el iPod.")
        except Exception as e:
            print(f"  [iPod] No se pudo listar el directorio remoto: {e}")
            self.remote_files = None

    def _ensure_remote_dir(self, remote_dir):
        """Crea el directorio remoto si no existe"""
        try:
            self.sftp.stat(remote_dir)
        except (FileNotFoundError, IOError):
            # Intenta crear los directorios padres recursivamente
            parent = os.path.dirname(remote_dir)
            if parent != '/':
                self._ensure_remote_dir(parent)
            self.sftp.mkdir(remote_dir)

    def upload_song(self, local_path, filename, silent=False):
        """Sube un archivo de canción a la carpeta única de canciones en el iPod"""
        remote_path = f"{self.remote_songs_path}/{filename}"
        
        if self.remote_files is not None:
            exists = filename in self.remote_files
        else:
            try:
                self.sftp.stat(remote_path)
                exists = True
            except (FileNotFoundError, IOError):
                exists = False
                
        if exists:
            if not silent:
                print(f"  El archivo {filename} ya existe en el iPod, saltando subida.")
        else:
            if not silent:
                print(f"  Subiendo {filename} al iPod...")
            self.sftp.put(local_path, remote_path)
            if self.remote_files is not None:
                self.remote_files.add(filename)
            
        return remote_path


    def upload_playlist_m3u(self, playlist_name, songs):
        """Genera y sube un archivo .m3u usando rutas relativas hacia la carpeta de canciones"""
        # Normalizar el nombre de la playlist para evitar caracteres inválidos en el filename
        safe_name = "".join(c for c in playlist_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        m3u_filename = f"{safe_name}.m3u"
        local_m3u_path = f"downloads/{m3u_filename}"
        
        print(f"Generando playlist: {m3u_filename} con {len(songs)} canciones...")
        
        with open(local_m3u_path, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            for song in songs:
                # Escribimos metadatos básicos
                f.write(f"#EXTINF:-1,{song['artist']} - {song['title']}\n")
                
                # Asumiendo que Playlists/ y Songs/ están en el mismo directorio base (ej. Documents/)
                # La ruta relativa desde Documents/Playlists/ hacia Documents/Songs/ es:
                # ../Songs/archivo.m4a
                
                # Formateamos el nombre del archivo de la canción como se guardó
                song_filename = f"{song['spotify_id']}.m4a"
                relative_path = f"../Songs/{song_filename}"
                f.write(f"{relative_path}\n")

        # Subir el archivo .m3u generado
        remote_path = f"{self.remote_playlists_path}/{m3u_filename}"
        print(f"Subiendo {m3u_filename} al iPod...")
        self.sftp.put(local_m3u_path, remote_path)

    def upload_pwntunes_playlist(self, playlist_name, songs):
        """Genera una playlist estilo PwnTunes creando una carpeta y symlinks/copias de los archivos"""
        # Limpiar nombre de playlist
        safe_name = "".join(c for c in playlist_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        playlist_dir = f"{self.remote_songs_path}/{safe_name}"
        
        print(f"Generando playlist PwnTunes: Carpeta '{safe_name}' con {len(songs)} canciones...")
        self._ensure_remote_dir(playlist_dir)
        
        for song in songs:
            song_filename = f"{song['spotify_id']}.m4a"
            target_path = f"{self.remote_songs_path}/{song_filename}"
            link_path = f"{playlist_dir}/{song_filename}"
            local_path = f"downloads/{song_filename}"
            
            try:
                # Primero, si el archivo/symlink ya existe, lo saltamos
                self.sftp.stat(link_path)
                continue
            except IOError:
                pass
                
            try:
                # Intentar crear symlink (Ahorra muchísimo espacio)
                self.sftp.symlink(target_path, link_path)
            except Exception as e:
                # Fallback: Copiar físicamente si el symlink falla
                if os.path.exists(local_path):
                    try:
                        self.sftp.put(local_path, link_path)
                    except Exception as ex:
                        print(f"    [Error] No se pudo copiar '{song['title']}' a la playlist PwnTunes: {ex}")

    def sync_video_to_vlc(self, local_video_path, remote_vlc_path):
        """Sube un archivo de video local a la bóveda de VLC en el iPod."""
        if not self.sftp:
            self.connect()
            
        try:
            # Asegurarse de que el directorio existe
            self.sftp.stat(remote_vlc_path)
        except IOError:
            print(f"  [Sincronización] El directorio de VLC no existe: {remote_vlc_path}")
            print(f"  [Sincronización] Creando directorio...")
            # Simple mkdir, asumiendo que el padre existe
            self.sftp.mkdir(remote_vlc_path)
            
        filename = os.path.basename(local_video_path)
        remote_path = f"{remote_vlc_path}/{filename}"
        
        try:
            self.sftp.stat(remote_path)
            print(f"  [Sincronización] El video '{filename}' ya existe en VLC. Saltando...")
            return True
        except IOError:
            pass # No existe, procedemos a subir
            
        print(f"  [Sincronización] Transfiriendo video '{filename}' a VLC...")
        self.sftp.put(local_video_path, remote_path)
        print(f"  [Sincronización] Video transferido exitosamente.")
        return True

    def sync_local_directory(self, local_base_dir="downloads"):
        """Busca recursivamente todos los .m4a en el directorio local y los sube a la carpeta de canciones remotas (PwnTunes/MImport)"""
        if not self.sftp:
            print("  [Error] No hay conexión SFTP.")
            return

        # Asegurar directorio remoto
        try:
            self.sftp.stat(self.remote_songs_path)
        except IOError:
            self.sftp.mkdir(self.remote_songs_path)
            
        print(f"\n--- Escaneando directorio local: {local_base_dir} ---")
        m4a_files = []
        for root, dirs, files in os.walk(local_base_dir):
            for file in files:
                if file.lower().endswith(".m4a"):
                    m4a_files.append(os.path.join(root, file))
                    
        print(f"  [Info] Se encontraron {len(m4a_files)} canciones físicas para subir forzosamente.")
        
        uploaded = 0
        skipped = 0
        
        for i, local_file in enumerate(m4a_files):
            filename = os.path.basename(local_file)
            remote_file = f"{self.remote_songs_path}/{filename}"
            
            # Print de progreso simple
            if i % 100 == 0:
                print(f"  [Progreso] Procesando {i}/{len(m4a_files)}...")
            
            # Comprobar si existe
            try:
                self.sftp.stat(remote_file)
                skipped += 1
            except IOError:
                # No existe
                try:
                    print(f"  [Subiendo] {filename}")
                    self.sftp.put(local_file, remote_file)
                    uploaded += 1
                except Exception as e:
                    print(f"  [Error] Fallo al subir '{filename}': {e}")
                    
        print(f"\n--- Resumen Sincronización Forzada ---")
        print(f"  Total encontradas en PC: {len(m4a_files)}")
        print(f"  Subidas nuevas al iPod: {uploaded}")
        print(f"  Saltadas (ya existían): {skipped}")

    def close(self):
        if self.sftp:
            self.sftp.close()
        self.ssh.close()
