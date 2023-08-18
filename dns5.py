import asyncio
import dns.message
import async_dns.resolver
from collections import OrderedDict
from typing import List, Tuple
from aiocache import caches, SimpleMemoryCache
import socket
import time
DNS_SERVERS = ['208.67.222.222', '1.1.1.1', '9.9.9.9', '185.228.168.168', '213.186.33.99']
DNS_TIMEOUT = 0.3
MAX_CACHE_SIZE = 500000
PACKET_SIZE_LIMIT = 512
class Cache:
    def __init__(self):
        self.cache = OrderedDict()
        self.lock = asyncio.RWLock()
    async def __contains__(self, query_name: str) -> bool:
        async with self.lock:
            return query_name in self.cache
    async def get(self, query_name: str) -> dns.message.Message:
        async with self.lock.read_lock():
            response = self.cache[query_name]
            if not response:
                raise KeyError(f"Cache entry for {query_name} does not exist")
            return dns.message.from_wire(response)
    async def add(self, query_name: str, response: dns.message.Message, max_age: int) -> None:
        async with self.lock.write_lock():
            self.cache[query_name] = response.to_wire()
            if len(self.cache) > MAX_CACHE_SIZE:
                self.cache.popitem(last=False)
async def resolve_async(resolver: async_dns.resolver.Resolver, request: dns.message.Message) -> dns.message.Message:
    try:
        response = await resolver.resolve_async(request)
    except dns.exception.DNSException as e:
        print(f"DNS error: {e}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None
    return response
async def handle_request(data: bytes, client: Tuple[str, int], resolver: async_dns.resolver.Resolver, cache: Cache) -> None:
    if len(data) > PACKET_SIZE_LIMIT:
        return b''
    try:
        request = await asyncio.wait_for(asyncio.to_thread(dns.message.from_wire, data), timeout=DNS_TIMEOUT)
    except (dns.exception.FormError, asyncio.TimeoutError):
        server_socket.close()
        return
    queries = request.question
    responses = []
    for query in queries:
        query_name = query.name.to_text()
        try:
            response = await cache.get(query_name)
        except KeyError:
            pass
        else:
            if response.answer:
                responses.append(response)
            continue
        response = await resolve_async(resolver, request)
        if not response:
            return
        if not response.answer:
            return
        await cache.add(query_name, response, max_age=response.ttl)
        responses.append(response)
    response = dns.message.make_response(request)
    response.answer = [rr for res in responses for rr in res.answer]
    response = response.to_wire()
    await asyncio.current_event_loop().sock_sendto(server_socket, response, client)
async def run_server() -> None:
    resolver = async_dns.resolver.Resolver(nameservers=DNS_SERVERS, timeout=DNS_TIMEOUT)
    cache = Cache()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(('0.0.0.0', 53))
    try:
        while True:
            data, client = await server_socket.recvfrom(PACKET_SIZE_LIMIT)
            asyncio.create_task(handle_request(data, client, resolver, cache))
    except OSError as e:
        if e.errno != socket.ECONNRESET:
            raise
    finally:
        resolver.close()
        server_socket.close()
if __name__ == "__main__":
    try:
        caches.set_config({
            'default': {
                'cache': 'aiocache.SimpleMemoryCache',
                'serializer': {
                    'class': 'aiocache.serializers.PickleSerializer'
                }
            },
            'lru': {
                'cache': 'aiocache.LRUCache',
                'max_size': MAX_CACHE_SIZE,
                'ttl': 300
            }
        })
        loop = asyncio.get_event_loop()
        server_task = loop.create_task(run_server())
        loop.run_until_complete(server_task)
    except Exception as e:
        print(f"An error occurred: {e}")