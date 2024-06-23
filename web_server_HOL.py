import asyncio
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

async def handle_request(reader, writer):
    try:
        request = b""
        while True:
            data = await asyncio.wait_for(reader.read(1024), timeout=10)  
            if not data:
                break
            request += data
            if b"\r\n\r\n" in request:
                break

        if not request:
            raise ValueError("Empty request received")

        request_str = request.decode('utf-8')
        headers = request_str.split('\r\n')

        try:
            method, path, version = headers[0].strip().split()
        except ValueError:
            raise ValueError("Malformed request received")

        if path == '/':
            path = '/test.html'

        if version not in ['HTTP/1.1', 'HTTP/1.0']:
            raise ValueError("Invalid HTTP version")

        if method not in ['GET', 'HEAD']:
            raise ValueError("Invalid HTTP method")

        if_modified_since = None
        for header in headers[1:]:
            if header:
                header_name, header_value = header.split(":", 1)
                header_name = header_name.strip().lower()
                if header_name not in ALLOWED_HEADERS:
                    raise ValueError(f"Unknown header: {header_name}")

                if header_name == "if-modified-since":
                    try:
                        if_modified_since = parsedate_to_datetime(header_value.strip()).replace(tzinfo=timezone.utc)
                        print(f"If-Modified-Since header parsed: {if_modified_since}")
                    except (TypeError, ValueError) as e:
                        print(f"Invalid If-Modified-Since date: {header_value.strip()}")
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
                    writer.write(response.encode('utf-8'))
                    await writer.drain()
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

    writer.write(response.encode('utf-8'))
    await writer.drain()
    writer.close()

async def start_server():
    server = await asyncio.start_server(handle_request, '0.0.0.0', 8080)
    addr = server.sockets[0].getsockname()
    print(f'Server started on {addr}')

    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(start_server())
