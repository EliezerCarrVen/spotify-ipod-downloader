import os
import paramiko
from dotenv import load_dotenv

load_dotenv()

ip = os.getenv('IPOD_IP')
port = int(os.getenv('IPOD_PORT', 22))
username = os.getenv('IPOD_USER', 'root')
password = os.getenv('IPOD_PASSWORD', 'alpine')
foobar_path = os.getenv('IPOD_SONGS_PATH') # La antigua ruta de Foobar

print(f"Conectando al iPod en {ip}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(ip, port=port, username=username, password=password)
    print("Conexión exitosa. Rescatando tus canciones huérfanas...")
    
    # Asegurarnos de que exista la carpeta PwnTunes
    ssh.exec_command('mkdir -p "/var/mobile/Media/My Music"')
    
    # Mover todas las canciones de la antigua ruta a PwnTunes
    comando = f'find "{foobar_path}" -type f -name "*.m4a" -exec mv -v {{}} "/var/mobile/Media/My Music/" \\;'
    print(f"Ejecutando movimiento interno... (Esto será instantáneo y no consumirá internet)")
    
    stdin, stdout, stderr = ssh.exec_command(comando)
    archivos_movidos = stdout.readlines()
    
    print(f"¡Se rescataron {len(archivos_movidos)} canciones y se movieron a PwnTunes!")
    
except Exception as e:
    print(f"Ocurrió un error: {e}")
finally:
    ssh.close()
    print("Proceso terminado. Ya puedes usar PwnTunes sin tener que volver a bajar nada.")
