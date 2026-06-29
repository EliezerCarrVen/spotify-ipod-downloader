import sqlite3
import os

class DatabaseManager:
    def __init__(self, db_path='sync_state.db'):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        """Retorna una conexión a base de datos segura para concurrencia en paralelo (WAL Mode)"""
        conn = sqlite3.connect(self.db_path, timeout=60.0)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')
        return conn

    def _init_db(self):
        conn = self._get_connection()
        c = conn.cursor()
        
        # Tabla para las canciones (deduplicación)
        c.execute('''
            CREATE TABLE IF NOT EXISTS songs (
                spotify_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                artist TEXT NOT NULL,
                album TEXT,
                local_path TEXT,
                remote_path TEXT,
                downloaded INTEGER DEFAULT 0,
                synced INTEGER DEFAULT 0
            )
        ''')
        
        # Tabla para las playlists
        c.execute('''
            CREATE TABLE IF NOT EXISTS playlists (
                playlist_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                spotify_url TEXT
            )
        ''')
        
        # Tabla de mapeo para las canciones de las playlists
        c.execute('''
            CREATE TABLE IF NOT EXISTS playlist_songs (
                playlist_id TEXT,
                spotify_id TEXT,
                position INTEGER,
                PRIMARY KEY (playlist_id, spotify_id, position),
                FOREIGN KEY (playlist_id) REFERENCES playlists(playlist_id),
                FOREIGN KEY (spotify_id) REFERENCES songs(spotify_id)
            )
        ''')
        
        conn.commit()
        conn.close()

    def add_song(self, spotify_id, title, artist, album):
        conn = self._get_connection()
        c = conn.cursor()
        c.execute('''
            INSERT OR IGNORE INTO songs (spotify_id, title, artist, album)
            VALUES (?, ?, ?, ?)
        ''', (spotify_id, title, artist, album))
        conn.commit()
        conn.close()

    def update_song_local_path(self, spotify_id, local_path):
        conn = self._get_connection()
        c = conn.cursor()
        c.execute('''
            UPDATE songs SET local_path = ?, downloaded = 1, synced = 0 WHERE spotify_id = ?
        ''', (local_path, spotify_id))
        conn.commit()
        conn.close()

    def update_song_synced_status(self, spotify_id, remote_path):
        conn = self._get_connection()
        c = conn.cursor()
        c.execute('''
            UPDATE songs SET remote_path = ?, synced = 1 WHERE spotify_id = ?
        ''', (remote_path, spotify_id))
        conn.commit()
        conn.close()

    def get_song(self, spotify_id):
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM songs WHERE spotify_id = ?', (spotify_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def add_playlist(self, playlist_id, name, spotify_url):
        conn = self._get_connection()
        c = conn.cursor()
        c.execute('''
            INSERT OR REPLACE INTO playlists (playlist_id, name, spotify_url)
            VALUES (?, ?, ?)
        ''', (playlist_id, name, spotify_url))
        conn.commit()
        conn.close()

    def clear_playlist_songs(self, playlist_id):
        """Limpia las canciones anteriores de una playlist para resincronizarla fresca"""
        conn = self._get_connection()
        c = conn.cursor()
        c.execute('DELETE FROM playlist_songs WHERE playlist_id = ?', (playlist_id,))
        conn.commit()
        conn.close()

    def add_song_to_playlist(self, playlist_id, spotify_id, position):
        conn = self._get_connection()
        c = conn.cursor()
        c.execute('''
            INSERT OR REPLACE INTO playlist_songs (playlist_id, spotify_id, position)
            VALUES (?, ?, ?)
        ''', (playlist_id, spotify_id, position))
        conn.commit()
        conn.close()

    def get_playlist_songs(self, playlist_id):
        """Retorna todas las canciones de una playlist en orden"""
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('''
            SELECT s.* FROM songs s
            JOIN playlist_songs ps ON s.spotify_id = ps.spotify_id
            WHERE ps.playlist_id = ?
            ORDER BY ps.position ASC
        ''', (playlist_id,))
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]
        
    def get_unsynced_songs(self):
        """Obtiene las canciones descargadas que aún no han sido sincronizadas al iPod"""
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM songs WHERE downloaded = 1 AND synced = 0')
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_all_playlists(self):
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM playlists')
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def find_downloaded_song_by_title_artist(self, title, artist):
        """Busca una canción ya descargada que coincida exactamente en título y artista"""
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Búsqueda insensible a mayúsculas/minúsculas
        c.execute('''
            SELECT * FROM songs 
            WHERE downloaded = 1 
              AND LOWER(title) = LOWER(?) 
              AND LOWER(artist) = LOWER(?)
            LIMIT 1
        ''', (title, artist))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def reset_all_synced_status(self):
        """Restablece el estado de sincronización de todas las canciones a 0 para forzar la resubida al iPod"""
        conn = self._get_connection()
        c = conn.cursor()
        c.execute('UPDATE songs SET synced = 0')
        conn.commit()
        conn.close()

