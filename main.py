import socket

def handle_request(request):
    headers = request.split('\r\n')
    method, path, version = headers[0].split(' ')
    
    if method == 'GET':
        if path == '/test.html':
            return version + " 200 OK\r\nContent-Type: text/html\r\n\r\n" + open('test.html').read()
        elif path == '/forbidden.html':
            return version + " 403 Forbidden\r\n\r\n"
        else:
            return version + " 404 Not Found\r\n\r\n"
    else:
        return version + " 400 Bad Request\r\n\r\n"

def start_server(port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('', port))
    server_socket.listen(1)
    print(f"Server started on port {port}...")

    while True:
        client_socket, client_address = server_socket.accept()
        request = client_socket.recv(1024).decode()
        response = handle_request(request)
        client_socket.sendall(response.encode())
        client_socket.close()

if __name__ == "__main__":
    start_server(8080)

