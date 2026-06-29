import os
import paramiko
from dotenv import load_dotenv

load_dotenv()

ip = os.getenv('IPOD_IP')
port = int(os.getenv('IPOD_PORT', 22))
username = os.getenv('IPOD_USER', 'root')
password = os.getenv('IPOD_PASSWORD', 'alpine')

foobar_uuid = "D9FF17D6-042F-45BA-83F4-96AE79CFE7C4"
foobar_docs = f"/var/mobile/Containers/Data/Application/{foobar_uuid}/Documents"
my_music = "/var/mobile/Media/My Music"
global_music = "/var/mobile/Media/GlobalMusic"

print(f"Conectando al iPod en {ip} para revertir a My Music...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(ip, port=port, username=username, password=password)
    
    # 1. Asegurarnos que My Music existe
    ssh.exec_command(f'mkdir -p "{my_music}"')
    
    # 2. Devolver los archivos de GlobalMusic a My Music
    ssh.exec_command(f'mv "{global_music}"/*.m4a "{my_music}/" 2>/dev/null')
    
    # 3. Borrar la carpeta GlobalMusic
    ssh.exec_command(f'rm -rf "{global_music}"')
    
    # 4. Rehacer el enlace de Foobar2000 hacia My Music
    ssh.exec_command(f'rm -rf "{foobar_docs}/Songs"')
    ssh.exec_command(f'ln -s "{my_music}" "{foobar_docs}/Songs"')
    
    # 5. Rehacer el enlace de VLC (si existe)
    stdin, stdout, stderr = ssh.exec_command('find /var/mobile/Containers/Data/Application -name "VLC" -type d')
    vlc_path = stdout.read().decode().strip()
    if vlc_path:
        vlc_docs = vlc_path.replace("/VLC", "/Documents")
        ssh.exec_command(f'rm -rf "{vlc_docs}/GlobalMusic"')
        ssh.exec_command(f'rm -rf "{vlc_docs}/Songs"')
        ssh.exec_command(f'ln -s "{my_music}" "{vlc_docs}/Songs"')
        
    print("¡Listo! Todo ha vuelto a /var/mobile/Media/My Music")

except Exception as e:
    print(f"Error: {e}")
finally:
    ssh.close()
