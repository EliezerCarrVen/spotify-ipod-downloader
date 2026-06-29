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
global_music = "/var/mobile/Media/GlobalMusic"

print(f"Conectando al iPod en {ip}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(ip, port=port, username=username, password=password)
    
    print("1. Creando la Carpeta Global Maestra...")
    ssh.exec_command(f'mkdir -p "{global_music}"')
    
    # Mover lo que haya en My Music a GlobalMusic para no perder la subida actual
    print("2. Rescatando archivos subidos y moviéndolos a la Carpeta Global...")
    ssh.exec_command(f'mv /var/mobile/Media/My\\ Music/*.m4a "{global_music}/" 2>/dev/null')
    
    print("3. Creando enlace simbólico para Foobar2000...")
    # Borrar si existe la carpeta Songs para poder crear el acceso directo con el mismo nombre
    ssh.exec_command(f'rm -rf "{foobar_docs}/Songs"')
    # Crear el enlace simbólico
    ssh.exec_command(f'ln -s "{global_music}" "{foobar_docs}/Songs"')
    
    print("4. Buscando VLC para crear su enlace simbólico...")
    # Buscamos la carpeta de VLC
    stdin, stdout, stderr = ssh.exec_command('find /var/mobile/Containers/Data/Application -name "VLC" -type d')
    vlc_path = stdout.read().decode().strip()
    
    if vlc_path:
        vlc_docs = vlc_path.replace("/VLC", "/Documents")
        ssh.exec_command(f'rm -rf "{vlc_docs}/GlobalMusic"')
        ssh.exec_command(f'ln -s "{global_music}" "{vlc_docs}/GlobalMusic"')
        print("¡Enlace para VLC creado con éxito!")
    else:
        print("VLC no está instalado aún, se saltó este paso.")
        
    print("\n¡MAGIA COMPLETADA! Foobar2000 y VLC ahora leen de la misma carpeta maestra.")

except Exception as e:
    print(f"Error: {e}")
finally:
    ssh.close()
