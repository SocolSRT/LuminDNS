import socket
import struct
import time
import selectors
from concurrent.futures import ThreadPoolExecutor
from threading import Thread

# DNS серверы для использования
DNS_SERVERS = ['1.1.1.1', '8.8.8.8', '8.8.4.4', '208.67.222.222', '77.88.8.8']
DNS_TIMEOUT = 1.0  # Тайм-аут для запроса к серверу
CACHE_TTL = 3600  # TTL для кэша (в секундах)
CACHE_CLEANUP_INTERVAL = 600  # Интервал очистки кэша (в секундах)
MAX_WORKERS = 50  # Максимальное количество потоков

# Сокет сервера
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(('', 53))

# Кэш запросов
cache = {}
selector = selectors.DefaultSelector()

# Ответ при ошибке
ERROR_RESPONSE = struct.pack("!6H", 0, 0, 3, 0, 1, 0) + struct.pack("!4H", 0, 0, 0, 0)

# Извлечение домена из DNS-запроса
def extract_domain(data):
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

# Запрос к нескольким DNS-серверам с использованием селектора
def resolve_with_servers(data, servers):
    responses = {}
    sockets = {}
    try:
        # Создание сокетов для каждого сервера
        for server in servers:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setblocking(False)
            sock.sendto(data, (server, 53))  # Отправка запроса на DNS сервер
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
                    
                    # Проверка, что ответ соответствует запросу (ID)
                    if response[:2] == data[:2]:  
                        # Проверка минимальной длины ответа (12 байтов - базовый размер DNS-запроса/ответа)
                        if len(response) > 12:
                            # Дополнительные проверки, например, на правильность формата DNS-ответа
                            # Проверим наличие записей в ответе (например, для A-записей)
                            answer_count = struct.unpack('!H', response[6:8])[0]
                            if answer_count > 0:
                                return response
                            else:
                                print(f"Ответ от {server} не содержит записей")
                        else:
                            print(f"Некорректный ответ от {server}: данные слишком короткие")
                    else:
                        print(f"Ответ от {server} не совпадает с запросом: {response[:2]} != {data[:2]}")
                
                except socket.timeout:
                    print(f"Тайм-аут при ожидании ответа от {server}")
                    continue
                except socket.error as e:
                    print(f"Ошибка сокета от {server}: {e}")
                    continue
                except Exception as e:
                    print(f"Неизвестная ошибка при обработке ответа от {server}: {e}")
                    continue

    except Exception as e:
        print(f"Ошибка при запросе к серверам: {e}")
    
    finally:
        # Закрытие всех сокетов
        for sock in sockets.values():
            try:
                selector.unregister(sock)
                sock.close()
            except socket.error as e:
                print(f"Ошибка при закрытии сокета: {e}")

    print("Не удалось получить корректный ответ от серверов.")
    return None

# Обработка входящего DNS-запроса
def handle_request(data, client_address):
    domain, request_id = extract_domain(data)

    if not domain or not request_id:
        server_socket.sendto(ERROR_RESPONSE, client_address)
        return

    # Проверяем кэш
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

# Очистка устаревших записей в кэше
def cleanup_cache():
    while True:
        time.sleep(CACHE_CLEANUP_INTERVAL)
        now = time.time()
        to_delete = [domain for domain, (_, timestamp) in cache.items() if now - timestamp > CACHE_TTL]
        for domain in to_delete:
            del cache[domain]

# Основной цикл обработки запросов
def listen_for_requests():
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        while True:
            try:
                data, client_address = server_socket.recvfrom(1024)
                executor.submit(handle_request, data, client_address)
            except Exception as e:
                print(f"Ошибка: {e}")

if __name__ == "__main__":
    # Увеличение лимита открытых файловых дескрипторов (для *nix систем)
    try:
        import resource
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        resource.setrlimit(resource.RLIMIT_NOFILE, (65536, hard))
        print(f"Лимит файловых дескрипторов увеличен до 65536")
    except ImportError:
        print("Не удалось увеличить лимит файловых дескрипторов. Продолжаем с текущим лимитом.")

    # Запуск потока для очистки кэша
    Thread(target=cleanup_cache, daemon=True).start()

    # Запуск основного цикла
    listen_for_requests()
