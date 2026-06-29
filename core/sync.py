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

    def close(self):
        if self.sftp:
            self.sftp.close()
        self.ssh.close()
