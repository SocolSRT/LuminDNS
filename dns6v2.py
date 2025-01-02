import socket
import struct
import time
import select
from threading import Thread

DNS_SERVERS = ['9.9.9.9', '1.1.1.1', '8.8.8.8', '77.88.8.8', '208.67.222.222']
DNS_TIMEOUT = 0.1
CACHE_TTL = 3600

server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(('', 53))

cache = {}

def extract_domain(data):
    domain = []
    i = 12
    while data[i] != 0:
        length = data[i]
        domain.append(data[i+1:i+1+length].decode())
        i += length + 1
    return '.'.join(domain)

def handle_request(data, client_address):
    request_id = data[:2]
    domain = extract_domain(data)
    
    if (request_id, domain) in cache:
        cached_response, timestamp = cache[(request_id, domain)]
        if time.time() - timestamp < CACHE_TTL:
            server_socket.sendto(cached_response, client_address)
            return
    
    forward_sockets = []
    for dns_server in DNS_SERVERS:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(DNS_TIMEOUT)
        forward_sockets.append(sock)
        sock.sendto(data, (dns_server, 53))
    
    response = None
    while forward_sockets:
        ready_to_read, _, _ = select.select(forward_sockets, [], [])
        for sock in ready_to_read:
            try:
                response, address = sock.recvfrom(1024)
                cache[(request_id, domain)] = (response, time.time())
                server_socket.sendto(response, client_address)
                sock.close()
                forward_sockets.remove(sock)
                return
            except socket.timeout:
                continue
    
    response = struct.pack("!H", 0) + struct.pack("!H", 0) + struct.pack("!H", 3) + struct.pack("!H", 0) + struct.pack("!H", 1) + struct.pack("!H", 0) + struct.pack("!H", 0) + struct.pack("!H", 0) + struct.pack("!H", 0) + struct.pack("!H", 0)
    server_socket.sendto(response, client_address)
    for s in forward_sockets:
        s.close()

def listen_for_requests():
    while True:
        data, client_address = server_socket.recvfrom(1024)
        Thread(target=handle_request, args=(data, client_address)).start()

if __name__ == "__main__":
    listen_for_requests()
