import os
import paramiko
from dotenv import load_dotenv

load_dotenv()

ip = os.getenv('IPOD_IP')
port = int(os.getenv('IPOD_PORT', 22))
username = os.getenv('IPOD_USER', 'root')
password = os.getenv('IPOD_PASSWORD', 'alpine')

print(f"Conectando al iPod en {ip}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(ip, port=port, username=username, password=password)
    
    print("\n--- Espacio en Discos (df -h) ---")
    stdin, stdout, stderr = ssh.exec_command('df -h')
    print(stdout.read().decode())
    
    print("\n--- Carpetas más pesadas en /var/mobile (du -sh) ---")
    stdin, stdout, stderr = ssh.exec_command('du -sh /var/mobile/* | sort -rh | head -n 10')
    print(stdout.read().decode())

    print("\n--- Buscando si hay archivos grandes en .Trash ---")
    stdin, stdout, stderr = ssh.exec_command('du -sh /var/mobile/Library/iFile/Trash* 2>/dev/null; du -sh /var/mobile/Media/.Trash* 2>/dev/null')
    print(stdout.read().decode())
    
except Exception as e:
    print(f"Ocurrió un error: {e}")
finally:
    ssh.close()
