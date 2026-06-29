import socket

ip = '192.168.1.74'
ports_to_try = [80, 8080, 8888, 8000]

print(f"Escaneando puertos HTTP en {ip}...")
for port in ports_to_try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    result = s.connect_ex((ip, port))
    if result == 0:
        print(f"Puerto {port} abierto!")
    s.close()
