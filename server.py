import subprocess
import sys
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

received_ip = None

def clone_vm(ip):
    template_vm_name = "template"
    new_vm_name = ip
    if subprocess.call(['prlctl', 'status', new_vm_name]) == 255:
        if 'stopped' not in subprocess.check_output(['prlctl', 'status', template_vm_name]).decode('ascii'):
            subprocess.call(['prlctl', 'stop', template_vm_name, "--drop-state"])
        subprocess.call(['prlctl', 'clone', template_vm_name, '--name', new_vm_name])
        print(f"虚拟机 '{new_vm_name}' 克隆成功.")
    subprocess.call(['prlctl', 'start', new_vm_name])

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        global received_ip
        if self.path == '/set_ip':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            received_ip = data.get('ip', None)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {'status': 'IP received'}
            self.wfile.write(json.dumps(response).encode('utf-8'))

            if received_ip:
                clone_vm(received_ip)
        else:
            self.send_error(404, "Not Found")

    def do_GET(self):
        if self.path == '/get_ip':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {'received_ip': received_ip} if received_ip else {'error': 'No IP received yet'}
            self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            self.send_error(404, "Not Found")

def run(server_class=HTTPServer, handler_class=SimpleHTTPRequestHandler, port=5000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting server on port {port}...')
    httpd.serve_forever()

if __name__ == '__main__':
    run()
