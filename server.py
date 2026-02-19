import socket
import sys
import os
import mimetypes
import urllib.parse


class Server(object):
    address_family = socket.AF_INET
    socket_type = socket.SOCK_STREAM
    request_queue_size = 5
    top_directory_path = os.path.dirname(os.path.abspath(__file__))
    response = []

    def __init__(self, host='', port=8000):
        self.HOST = host
        self.PORT = port
        self.listen_socket = listen_socket = socket.socket(
            self.address_family,
            self.socket_type
        )
        self.listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listen_socket.bind((self.HOST, self.PORT))
        self.listen_socket.listen(self.request_queue_size)

        self.headers = b"""\
HTTP/1.1 200 OK
Content-Type: text/html

"""
        print('Serving HTTP on port {}'.format(self.PORT))

    def serve_forever(self):
        while 1:
            connection, adress = self.listen_socket.accept()
            request_headers = connection.recv(1024)
            request = request_headers.decode().split('\n\r')[0].split('\r')[0]
            print(request)
            try:
                response = self.handle_request(request)
            except:
                break

            connection.sendall(response)
            connection.close()

    def handle_request(self, request):
        try:
            request_path = request.split(' ')[1]
        except:
            pass

        request_path = urllib.parse.unquote(request_path)
        response = ''
        if os.path.isdir('.' + request_path):
            for index in 'index.html', 'index.htm':
                index_path = os.path.join('.' + request_path, index)
                if os.path.exists(index_path):
                    file = open(index_path, 'rb').read()
                    response = self.headers + file
                    break
            else:
                response = self.headers + self.get_directory(request_path).encode()
        else:
            file_path = os.path.join(self.top_directory_path, request_path[1:])
            if os.path.exists(file_path):
                content_type, content_encoding = self.find_type(request_path)
                if content_type is None:
                    content_type = 'application/octet-stream'

                file = open(file_path, 'rb')

                response = """\
HTTP/1.1 200 OK
Content-Type: {}
Content-encoding: {}

""".format(content_type, content_encoding)
                response = response.encode() + file.read()
            else:
                response = b'<h1>Sorry, no such file</h1>\n<a href="/">Go Back</a>'

        return response

    def get_directory(self, request_path):
        directory_html_list = """
<!DOCTYPE html>
<html>
<head>
<title>Listing of {0}</title>
<h1>Listing of  {0}</h1>
<hr>
<body>
<ul>
""".format(request_path)

        if request_path.startswith('/'):
            request_path = request_path[1:]
        print("Request ", request_path)

        current_path = os.path.join(self.top_directory_path, request_path)
        print("CURRENT PATH IS ", current_path)
        directory_items = os.listdir(current_path)
        for name in directory_items:

            path_to_name = os.path.join(current_path, name)
            rel_path = path_to_name.split(self.top_directory_path)[1]
            print('path to name', path_to_name)
            print(rel_path)

            if os.path.isfile(name) and '.' not in name:
                print("File without and extention")
                item = "<li><a href='{}' download>{}</a></li>\n".format(rel_path, name)
            else:
                item = "<li><a href='{}'>{}</a></li>\n".format(rel_path, name)
            directory_html_list += item

        return directory_html_list + '</ul><hr></body></html>'

    def find_type(self, path):
        content_type = mimetypes.guess_type(path)
        return content_type


if __name__ == '__main__':
    # Determine the port number
    if len(sys.argv) > 1:
        HOST, PORT = '', sys.argv[1]
    else:
        HOST, PORT = '', 8000
    # Create server instanse
    server = Server(HOST, PORT)
    server.serve_forever()