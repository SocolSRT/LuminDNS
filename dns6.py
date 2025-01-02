import socket
import struct
import time
import select
from threading import Thread

DNS_SERVERS = ['208.67.222.222', '77.88.8.8', '8.8.8.8', '1.1.1.1', '9.9.9.9']
DNS_TIMEOUT = 0.5
CACHE_TTL = 3600
CACHE_CLEANUP_INTERVAL = 600

server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(('', 53))

cache = {}

ERROR_RESPONSE = struct.pack("!H", 0) + struct.pack("!H", 0) + struct.pack("!H", 3) + struct.pack("!H", 0) + struct.pack("!H", 1) + struct.pack("!H", 0) + struct.pack("!H", 0) + struct.pack("!H", 0) + struct.pack("!H", 0) + struct.pack("!H", 0)

def extract_domain(data):
    try:
        domain = []
        i = 12
        while data[i] != 0:
            length = data[i]
            domain.append(data[i+1:i+1+length].decode())
            i += length + 1
        return '.'.join(domain), data[:2]
    except IndexError:
        return None, None

def resolve_with_server(data, server):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(DNS_TIMEOUT)
    try:
        sock.sendto(data, (server, 53))
        ready = select.select([sock], [], [], DNS_TIMEOUT)[0]
        if ready:
            response, _ = sock.recvfrom(1024)
            return response
        else:
          return None
    except socket.error:
        return None
    finally:
        sock.close()

def handle_request(data, client_address):
    domain, request_id = extract_domain(data)

    if not domain or not request_id:
        server_socket.sendto(ERROR_RESPONSE, client_address)
        return

    if domain in cache and time.time() - cache[domain][1] < CACHE_TTL:
        cached_response = cache[domain][0]
        server_socket.sendto(request_id + cached_response[2:], client_address)
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
                cache[domain] = (response, time.time())
                server_socket.sendto(response, client_address)
                sock.close()
                forward_sockets.remove(sock)
                return
            except socket.timeout:
                continue

def cleanup_cache():
    while True:
        time.sleep(CACHE_CLEANUP_INTERVAL)
        now = time.time()
        to_delete = [domain for domain, (response, timestamp) in cache.items() if now - timestamp > CACHE_TTL]
        for domain in to_delete:
            del cache[domain]

def listen_for_requests():
    while True:
        data, client_address = server_socket.recvfrom(1024)
        Thread(target=handle_request, args=(data, client_address)).start()

if __name__ == "__main__":
    import threading
    cache_thread = threading.Thread(target=cleanup_cache, daemon=True)
    cache_thread.start()
    listen_for_requests()
