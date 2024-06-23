import socket
import threading
import re
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

cache = {}

def handle_proxy_request(client_socket):
    try:
        request = client_socket.recv(4096).decode('utf-8')
        if not request:
            raise ValueError("Empty request received")
        
        headers = request.split('\n')
        if len(headers) < 1:
            raise ValueError("Malformed request received")
        
        try:
            method, full_url, version = headers[0].strip().split()
        except ValueError:
            raise ValueError("Malformed request received")

        if version not in ['HTTP/1.1', 'HTTP/1.0']:
            raise ValueError("Invalid HTTP version")

        match = re.match(r'http://([^/:]+)(?::(\d+))?(/.*)?', full_url)
        if not match:
            raise ValueError("Invalid URL format")

        host, port_str, path = match.groups()
        port = int(port_str) if port_str else 80

        if_modified_since = None
        for header in headers[1:]:
            if header.lower().startswith("if-modified-since"):
                if_modified_since = header.split(":", 1)[1].strip()
                break

        cache_key = (method, host, port, path)
        if cache_key in cache and not if_modified_since:
            cached_response, cached_time = cache[cache_key]
            if datetime.utcnow() - cached_time < timedelta(minutes=5):  
                print("cached response")
                client_socket.sendall(cached_response)
                client_socket.close()
                return

        forward_request = f"{method} {path} {version}\r\n"
        forward_request += '\r\n'.join(headers[1:])
        forward_request += '\r\n\r\n'

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as forward_socket:
            forward_socket.connect((host, port))
            forward_socket.sendall(forward_request.encode('utf-8'))

            response = b""
            while True:
                part = forward_socket.recv(4096)
                if not part:
                    break
                response += part

            if not if_modified_since:
                cache[cache_key] = (response, datetime.utcnow())

            client_socket.sendall(response)
    
    except ValueError as e:
        response = f'HTTP/1.1 400 Bad Request\n\n{str(e)}'
        client_socket.sendall(response.encode('utf-8'))
    except Exception as e:
        response = f'HTTP/1.1 500 Internal Server Error\n\n{str(e)}'
        client_socket.sendall(response.encode('utf-8'))
    
    client_socket.close()

def start_proxy_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', 8888))
    server_socket.listen(5)
    print('Proxy server started on port 8888')

    while True:
        client_socket, addr = server_socket.accept()
        print(f'Connection from {addr}')
        client_handler = threading.Thread(target=handle_proxy_request, args=(client_socket,))
        client_handler.start()

if __name__ == "__main__":
    start_proxy_server()
