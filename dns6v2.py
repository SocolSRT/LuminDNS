import socket
import struct
import time
import selectors
from concurrent.futures import ThreadPoolExecutor
from threading import Thread

DNS_SERVERS = ['208.67.222.222', '77.88.8.8', '8.8.8.8', '1.1.1.1', '9.9.9.9']
DNS_TIMEOUT = 0.5
CACHE_TTL = 3600
CACHE_CLEANUP_INTERVAL = 600
MAX_WORKERS = 50

server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(('', 53))

cache = {}
selector = selectors.DefaultSelector()

ERROR_RESPONSE = struct.pack("!6H", 0, 0, 3, 0, 1, 0) + struct.pack("!4H", 0, 0, 0, 0)

def extract_domain(data):
    """Извлечение домена из DNS-запроса."""
    try:
        domain_parts = []
        i = 12
        while data[i] != 0:
            length = data[i]
            domain_parts.append(data[i + 1:i + 1 + length].decode())
            i += length + 1
        return '.'.join(domain_parts), data[:2]
    except (IndexError, UnicodeDecodeError):
        return None, None

def resolve_with_servers(data, servers):
    """Параллельный запрос к нескольким DNS-серверам с использованием selectors."""
    responses = {}
    sockets = {}
    try:
        # Создаем сокеты для всех серверов и регистрируем их в селекторе
        for server in servers:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setblocking(False)
            sock.sendto(data, (server, 53))
            selector.register(sock, selectors.EVENT_READ, server)
            sockets[server] = sock

        start_time = time.time()
        while time.time() - start_time < DNS_TIMEOUT:
            events = selector.select(timeout=DNS_TIMEOUT)
            for key, _ in events:
                sock = key.fileobj
                server = key.data
                try:
                    response, _ = sock.recvfrom(1024)
                    responses[server] = response
                    # Достаточно первого успешного ответа
                    return response
                except socket.error:
                    continue
    finally:
        # Освобождаем ресурсы
        for sock in sockets.values():
            selector.unregister(sock)
            sock.close()
    return None

def handle_request(data, client_address):
    """Обработка входящего DNS-запроса."""
    domain, request_id = extract_domain(data)

    if not domain or not request_id:
        server_socket.sendto(ERROR_RESPONSE, client_address)
        return

    # Проверка кеша
    if domain in cache:
        cached_response, timestamp = cache[domain]
        if time.time() - timestamp < CACHE_TTL:
            server_socket.sendto(request_id + cached_response[2:], client_address)
            return

    # Параллельный запрос к DNS-серверам
    response = resolve_with_servers(data, DNS_SERVERS)
    if response:
        cache[domain] = (response, time.time())
        server_socket.sendto(response, client_address)
    else:
        # Если ни один сервер не ответил
        server_socket.sendto(ERROR_RESPONSE, client_address)

def cleanup_cache():
    """Очистка устаревших записей кеша."""
    while True:
        time.sleep(CACHE_CLEANUP_INTERVAL)
        now = time.time()
        to_delete = [domain for domain, (_, timestamp) in cache.items() if now - timestamp > CACHE_TTL]
        for domain in to_delete:
            del cache[domain]

def listen_for_requests():
    """Слушаем входящие запросы и передаем их в пул потоков."""
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        while True:
            try:
                data, client_address = server_socket.recvfrom(1024)
                executor.submit(handle_request, data, client_address)
            except Exception as e:
                print(f"Ошибка: {e}")

if __name__ == "__main__":
    # Запускаем поток для очистки кеша
    Thread(target=cleanup_cache, daemon=True).start()
    listen_for_requests()
