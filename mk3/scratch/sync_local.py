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
            
        print(f"--- Escaneando directorio local: {local_base_dir} ---")
        m4a_files = []
        for root, dirs, files in os.walk(local_base_dir):
            for file in files:
                if file.lower().endswith(".m4a"):
                    m4a_files.append(os.path.join(root, file))
                    
        print(f"  [Info] Se encontraron {len(m4a_files)} canciones físicas para subir forzosamente.")
        
        uploaded = 0
        skipped = 0
        for local_file in m4a_files:
            filename = os.path.basename(local_file)
            remote_file = f"{self.remote_songs_path}/{filename}"
            
            # Comprobar si existe
            try:
                self.sftp.stat(remote_file)
                # print(f"  [Saltando] '{filename}' ya existe.")
                skipped += 1
            except IOError:
                # No existe
                print(f"  [Subiendo] {filename}...")
                try:
                    self.sftp.put(local_file, remote_file)
                    uploaded += 1
                except Exception as e:
                    print(f"  [Error] Fallo al subir '{filename}': {e}")
                    
        print(f"--- Resumen Sincronización Forzada ---")
        print(f"  Total encontradas: {len(m4a_files)}")
        print(f"  Subidas nuevas: {uploaded}")
        print(f"  Saltadas (ya existían): {skipped}")
