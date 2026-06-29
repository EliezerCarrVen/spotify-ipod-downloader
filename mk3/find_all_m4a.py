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
    print("Buscando dónde están escondidos los archivos .m4a (10GB) en el iPod...")
    
    # Buscar en todo el directorio del usuario
    comando = 'find /var/mobile -type f -name "*.m4a" | head -n 20'
    stdin, stdout, stderr = ssh.exec_command(comando)
    print(stdout.read().decode())
    
    # Ver cuánto pesa la carpeta de medios
    print("\nPeso de /var/mobile/Media:")
    stdin, stdout, stderr = ssh.exec_command('du -sh /var/mobile/Media')
    print(stdout.read().decode())

except Exception as e:
    print(f"Ocurrió un error: {e}")
finally:
    ssh.close()
