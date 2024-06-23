import socket
import threading
import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

ALLOWED_HEADERS = {
    "",
    " ",
    "host",
    "user-agent",
    "accept",
    "accept-language",
    "accept-encoding",
    "connection",
    "proxy-connection",
    "if-modified-since"
}

def handle_request(client_socket):
    try:
        request = b""
        while True:
            part = client_socket.recv(1024)
            request += part
            if b"\r\n\r\n" in part or not part:
                break
        request = request.decode('utf-8')
        
        if not request:
            raise ValueError("Empty request received")

        headers = request.split('\r\n')
        print(len(headers))
        print(headers)

        try:
            method, path, version = headers[0].strip().split()
        except ValueError:
            raise ValueError("Malformed request received")

        if path == '/':
            path = '/test.html'

        if version not in ['HTTP/1.1', 'HTTP/1.0']:
            raise ValueError("Invalid HTTP version")

        if method not in ['GET', 'HEAD']:
            print(method)
            raise ValueError("Invalid HTTP method")

        if_modified_since = None
        for header in headers[1:]:
            if header:
                header_name = header.split(":", 1)[0].strip().lower()
                if header_name not in ALLOWED_HEADERS:
                    raise ValueError(f"Unknown header: {header_name}")

                if header_name == "if-modified-since":
                    if_modified_since_header = header.split(":", 1)[1].strip()
                    try:
                        if_modified_since = parsedate_to_datetime(if_modified_since_header).replace(tzinfo=timezone.utc)
                        print(f"If-Modified-Since header parsed: {if_modified_since}")
                    except (TypeError, ValueError) as e:
                        print(f"Invalid If-Modified-Since date: {if_modified_since_header}")
                        raise ValueError("Invalid If-Modified-Since date format")

        if path == '/forbidden.html':
            response = 'HTTP/1.1 403 Forbidden\r\n\r\nForbidden'
        else:
            try:
                file_path = 'test' + path
                last_modified_time = os.path.getmtime(file_path)
                last_modified_date = datetime.utcfromtimestamp(last_modified_time).replace(tzinfo=timezone.utc)
                print(f"Last-Modified date: {last_modified_date.strftime('%a, %d %b %Y %H:%M:%S GMT')}")

                if if_modified_since and if_modified_since >= last_modified_date:
                    response = 'HTTP/1.1 304 Not Modified\r\n\r\n'
                    client_socket.sendall(response.encode('utf-8'))
                    client_socket.close()
                    return

                with open(file_path, 'r') as fin:
                    content = fin.read()

                response = f'HTTP/1.1 200 OK\r\nLast-Modified: {last_modified_date.strftime("%a, %d %b %Y %H:%M:%S GMT")}\r\n\r\n'
                if method == 'GET':
                    response += content
            except FileNotFoundError:
                response = 'HTTP/1.1 404 Not Found\r\n\r\nNot Found'
        
    except ValueError as e:
        response = f'HTTP/1.1 400 Bad Request\r\n\r\n{str(e)}'
        print(e)
    except Exception as e:
        response = f'HTTP/1.1 500 Internal Server Error\r\n\r\n{str(e)}'
        print(f"Exception occurred: {str(e)}")
    
    client_socket.sendall(response.encode('utf-8'))
    client_socket.close()

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', 8080))
    server_socket.listen(5)
    print('Server started on port 8080')

    while True:
        client_socket, addr = server_socket.accept()
        print(f'Connection from {addr}')
        client_handler = threading.Thread(target=handle_request, args=(client_socket,))
        client_handler.start()

if __name__ == "__main__":
    start_server()
