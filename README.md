# LuminDNS
LuminDNS is a Python script designed to provide a lightweight and efficient DNS caching server with support for asynchronous handling of DNS queries. By leveraging async DNS resolution, LuminDNS offers improved performance and responsiveness, making it an ideal choice for local DNS caching needs.

# How to Use

Follow these steps to set up and run LuminDNS:

Install Dependencies: Make sure you have Python installed on your system. You also need to install the required dependencies. Run the following command to install them:

    pip install aiocache dnspython async_dns

Clone the Repository: Clone the LuminDNS repository to your local machine.

Navigate to the Repository: Use the terminal to navigate to the cloned repository's directory.

Configure DNS Servers: Open the dns5.py file and locate the DNS_SERVERS list. Add or modify the IP addresses of DNS servers you want LuminDNS to forward queries to.

Run the Script: In the terminal, execute the following command to start the LuminDNS server:

    python dns5.py

Point Clients to LuminDNS: Configure your devices or network settings to use the IP address of the machine running LuminDNS as the preferred DNS server. This will direct DNS queries to your LuminDNS instance.

# Customization

LuminDNS can be customized to fit your requirements:

- Cache Size: Adjust the MAX_CACHE_SIZE variable to control the maximum number of cached DNS responses.
- Cache Expiration: Modify the cache expiration settings in the caches.set_config() section to determine how long DNS responses are retained in the cache.
- Packet Size Limit: You can set a limit for the size of DNS packets that LuminDNS will handle by modifying the PACKET_SIZE_LIMIT variable.

# OLD Old Version
> DNS_SERVERS - list of DNS servers that the script will access <br>
> DNS_TIMEOUT - Waiting time for a response from the DNS server

In private mode, you can restrict access by IP (dnsw.py)
> WHITELIST - IP addresses that can connect to the dns server

Download the file to a location of your choice and run it in the background
```
python3 dns.py &
```

# Would you like to support me financially?
* My Bitcoin wallet - *14AA4FAdUYnTVTx5pSQjq2h8UJoA8Na89R*
* My Litecoin wallet - *MSevKqUirTvQTkGxYechhNmBgAtDiZJq2x*
