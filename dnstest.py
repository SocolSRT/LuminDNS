import socket
import time
import struct

# IP-адрес вашего DNS-сервера
DNS_SERVER = '1.1.1.1'
# Список доменов для проверки
DOMAINS = ['google.com', 'chatgpt.com', 'github.com', 'example.com', 'python.org']
# Количество запросов для каждого домена
QUERY_COUNT = 5

def query_dns(domain, dns_server):
    # Формируем запрос для домена (A-запись)
    query = build_dns_query(domain)

    # Создаем сокет для связи с DNS-сервером
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(2)  # Устанавливаем тайм-аут для запроса
        s.sendto(query, (dns_server, 53))  # Отправляем запрос на порт 53 (DNS)

        # Получаем ответ
        response, _ = s.recvfrom(512)
        return parse_dns_response(response)

def build_dns_query(domain):
    # Создаем запрос DNS в формате бинарных данных
    transaction_id = b'\x12\x34'  # ID транзакции (можно использовать любой)
    flags = b'\x01\x00'  # Запрос
    questions = b'\x00\x01'  # Количество запросов
    answers = b'\x00\x00'  # Количество ответов
    authorities = b'\x00\x00'  # Количество авторитетных серверов
    additional = b'\x00\x00'  # Количество дополнительных записей

    # Формируем домен в формате, подходящем для DNS-запроса
    domain_parts = domain.split('.')
    question = b''.join([bytes([len(part)]) + part.encode('utf-8') for part in domain_parts])
    question += b'\x00'  # Завершающий байт
    question_type = b'\x00\x01'  # A-запись
    question_class = b'\x00\x01'  # IN (Internet)

    # Объединяем все части запроса
    return transaction_id + flags + questions + answers + authorities + additional + question + question_type + question_class

def parse_dns_response(response):
    # Парсим ответ от DNS-сервера
    # Ответ должен быть в виде бинарных данных
    answer_start = response.find(b'\xc0\x0c')  # Найдем начало ответа
    ip_parts = response[answer_start + 12:answer_start + 16]  # Извлекаем IP-адрес из ответа
    return '.'.join(str(b) for b in ip_parts)  # Преобразуем в строку

def check_dns_server(dns_server, domains, query_count):
    results = []

    for domain in domains:
        times = []
        for _ in range(query_count):
            try:
                start_time = time.time()
                ip = query_dns(domain, dns_server)  # Запрашиваем DNS-запись
                elapsed_time = (time.time() - start_time) * 1000  # Время в миллисекундах
                times.append(elapsed_time)
            except Exception as e:
                times.append(None)
                print(f"Ошибка при запросе домена {domain}: {e}")

        # Вычисляем среднее время ответа
        valid_times = [t for t in times if t is not None]
        avg_time = sum(valid_times) / len(valid_times) if valid_times else None

        results.append({
            'domain': domain,
            'times': times,
            'avg_time': avg_time
        })

    return results

def print_results(results):
    for result in results:
        print(f"Домен: {result['domain']}")
        print(f"  Время ответов: {result['times']}")
        if result['avg_time'] is not None:
            print(f"  Среднее время ответа: {result['avg_time']:.2f} ms")
        else:
            print("  Все запросы завершились ошибкой.")

if __name__ == "__main__":
    results = check_dns_server(DNS_SERVER, DOMAINS, QUERY_COUNT)
    print_results(results)
