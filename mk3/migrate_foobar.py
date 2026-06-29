import os
import paramiko
from dotenv import load_dotenv

load_dotenv()

ip = os.getenv('IPOD_IP')
port = int(os.getenv('IPOD_PORT', 22))
username = os.getenv('IPOD_USER', 'root')
password = os.getenv('IPOD_PASSWORD', 'alpine')

old_path = "/var/mobile/Containers/Data/Application/C13971A8-5E64-40CE-8451-AA8E0DAA41F5/Documents"
new_path = "/var/mobile/Containers/Data/Application/D9FF17D6-042F-45BA-83F4-96AE79CFE7C4/Documents"

print(f"Conectando al iPod en {ip}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(ip, port=port, username=username, password=password)
    
    print("Moviendo la música desde la carpeta antigua a la nueva...")
    comando = f'mv "{old_path}/Songs" "{new_path}/" && mv "{old_path}/Playlists" "{new_path}/"'
    stdin, stdout, stderr = ssh.exec_command(comando)
    print(stdout.read().decode())
    print(stderr.read().decode())
    
    print("¡Listo! Tu música de 10 GB ha sido inyectada en el nuevo Foobar2000.")
except Exception as e:
    print(f"Error: {e}")
finally:
    ssh.close()
