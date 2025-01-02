import socket
import struct
import time
import select
from threading import Thread

DNS_SERVERS = ['208.67.222.222', '1.1.1.1', '8.8.8.8', '8.26.56.26', '9.9.9.9', '77.88.8.8', '94.140.14.14', '185.228.168.168', '213.186.33.99']
DNS_TIMEOUT = 0.1
CACHE_TTL = 60

server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(('', 53))

cache = {}

def handle_request(data, client):
    request_id = data[:2] 
    domain = data[-1]
    
    if (request_id, domain) in cache:
        cached_response, timestamp = cache[(request_id, domain)]
        if time.time() - timestamp < CACHE_TTL:
            server_socket.sendto(cached_response, client)
            return
    
    forward_sockets = []
    for dns_server in DNS_SERVERS:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(DNS_TIMEOUT)
        forward_sockets.append(sock)
        sock.sendto(data, (dns_server, 53))
    
    while forward_sockets:
        ready_to_read, _, _ = select.select(forward_sockets, [], [])
        for sock in ready_to_read:
            try:
                response, address = sock.recvfrom(1024)
                cache[(request_id, domain)] = (response, time.time())
                server_socket.sendto(response, client)
                for s in forward_sockets:
                    s.close()
                return
            except socket.timeout:
                continue
    
    response = struct.pack("!H", 0) + struct.pack("!H", 0) + struct.pack("!H", 3) + struct.pack("!H", 0) + struct.pack("!H", 1) + struct.pack("!H", 0) + struct.pack("!H", 0) + struct.pack("!H", 0) + struct.pack("!H", 0) + struct.pack("!H", 0)
    server_socket.sendto(response, client)
    for s in forward_sockets:
        s.close()

def listen_for_requests():
    while True:
        data, client = server_socket.recvfrom(1024)
        Thread(target=handle_request, args=(data, client)).start()

if __name__ == "__main__":
    listen_for_requests()
