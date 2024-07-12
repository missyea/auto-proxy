import logging
import subprocess
import http.client
import json
import base64
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

vm = 'VMware Workstation Pro'
# vm = 'Parallels Desktop'

class VMwareServerParams():
    def __init__(self):
        self.server_ip = "localhost"
        self.server_port = 8697
        self.host = ("%s:%s" % (self.server_ip, self.server_port))

        user = "admin"
        password = "Aa12345."
        authentication_string = base64.b64encode((user + ":" + password).encode('ascii'))

        self.headers = {
            "Authorization": ("Basic %s" % authentication_string.decode('ascii')),
            "Content-type": "application/vnd.vmware.vmw.rest-v1+json",
            "Accept": "application/vnd.vmware.vmw.rest-v1+json"
        }

        self.workdir = "D:\\Virtual Machines"
        self.template_vm_name = "template"
        self.template_vm_path = os.path.join(self.workdir, self.template_vm_name, f"{self.template_vm_name}.vmx")

    def check_response(self,response):
        if response.status == 401:
            logging.warning("Server returned unauthenticated error")
        elif response.status == 200:
            logging.info("Request successful.")
        elif response.status == 204:
            logging.info("Request successful, no output")
            return {}
        elif response.status == 404:
            logging.info("Request returned 404")
            return response.read().decode("utf-8")
        else:
            logging.warning("Unknown status %d for request" % response.status)

        data = response.read()
        if data:
            return json.loads(data)
        else:
            return {}

if vm == 'VMware Workstation Pro':
    global vmsp
    vmsp = VMwareServerParams()
    conn = http.client.HTTPConnection(vmsp.host)
    # conn.request("GET", "/api/vms",headers=vmsp.headers)
    # response = conn.getresponse()
    # print(vmsp.check_response(response))
    print(f"使用 VMware Workstation Pro，工作目录为: {vmsp.workdir}")

def _clone_vm_1(ip):
    new_vm_name = ip
    template_vm_name = "template"

    status = subprocess.call(['prlctl', 'status', new_vm_name])

    if status == 255: 
        template_status = subprocess.check_output(['prlctl', 'status', template_vm_name]).decode('ascii')

        if 'stopped' not in template_status:
            subprocess.call(['prlctl', 'stop', template_vm_name, "--drop-state"])
        
        subprocess.call(['prlctl', 'clone', template_vm_name, '--name', new_vm_name])
        logger.info(f"虚拟机 {new_vm_name} 克隆成功")

    subprocess.call(['prlctl', 'start', new_vm_name])

def _clone_vm_2(ip):
    new_vm_name = ip
    new_vm_path = os.path.join(vmsp.workdir, new_vm_name, f"{new_vm_name}.vmx")

    try:
        subprocess.run(['vmrun', 'getGuestIPAddress', vmsp.template_vm_path], shell=True, check=True, capture_output=True, text=True, encoding="utf-8")
        subprocess.run(['vmrun', 'stop', vmsp.template_vm_path, 'hard'], shell=True, check=True, capture_output=True, text=True, encoding="utf-8")
        logger.info(f"模板虚拟机 '{vmsp.template_vm_name}' 停止成功")
    except subprocess.CalledProcessError:
        pass

    tools_state_output = subprocess.run(['vmrun', 'checkToolsState', new_vm_path], shell=True, check=False, capture_output=True, text=True, encoding="utf-8").stdout.strip()
    if 'installed' in tools_state_output.lower():
        pass
    elif 'running' in tools_state_output.lower():
        logger.info(f"虚拟机 {new_vm_name} 正在运行")
        return
    elif '找不到该虚拟机' in tools_state_output.lower():
        clone_cmd = [
            'vmrun',
            'clone',
            vmsp.template_vm_path,
            new_vm_path,
            'full',
            f'-cloneName={new_vm_name}'
        ]
        subprocess.run(clone_cmd, shell=True, check=True, capture_output=True, text=True, encoding="utf-8")
        logger.info(f"虚拟机 {new_vm_name} 克隆成功")

    subprocess.run(['vmrun', 'start', new_vm_path, 'nogui'], shell=True, check=True, capture_output=True, text=True, encoding="utf-8")
    logger.info(f"虚拟机 {new_vm_name} 启动成功")

def clone_vm(ip):
    if vm == "Parallels Desktop":
        _clone_vm_1(ip)
    elif vm == "VMware Workstation Pro":
        _clone_vm_2(ip)

def reset_vm(ip):
    vm_name = ip
    vm_path = os.path.join(vmsp.workdir, vm_name, f"{vm_name}.vmx")

    subprocess.run(['vmrun', 'reset', vm_path, 'hard'], shell=True, check=False, capture_output=True, text=True, encoding="utf-8")
    logger.info(f"虚拟机 {vm_name} 已重置")

def delete_vm(ip):
    vm_name = ip
    vm_path = os.path.join(vmsp.workdir, vm_name, f"{vm_name}.vmx")

    subprocess.run(['vmrun', 'stop', vm_path, 'hard'], shell=True, check=False, capture_output=True, text=True, encoding="utf-8")
    subprocess.run(['vmrun', 'deleteVM', vm_path], shell=True, check=False, capture_output=True, text=True, encoding="utf-8")
    logger.info(f"虚拟机 {vm_name} 已删除")

def _get_running_vm_name_1(ip):
    try:
        output = subprocess.check_output(['prlctl', 'list', '-f', '-j']).decode('utf-8')
        vm_list = json.loads(output)

        for vm in vm_list:
            if 'ip_configured' in vm and vm['ip_configured'] == ip:
                return vm['name']
        
        logger.warning(f"未找到匹配 IP '{ip}' 的运行中虚拟机.")
        return None
    except subprocess.CalledProcessError as e:
        logger.error(f"执行 prlctl 命令时发生错误: {e}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"解析 prlctl 输出为 JSON 时发生错误: {e}")
        raise

def _get_running_vm_name_2(ip):
    try:
        vm_list = subprocess.run(['vmrun', 'list'], shell=True, check=True, capture_output=True, text=True, encoding="utf-8").stdout.splitlines()[1:]

        for vm in vm_list:
            try:
                guest_ip = subprocess.run(['vmrun', 'getGuestIPAddress', vm], shell=True, check=True, capture_output=True, text=True, encoding="utf-8").stdout.strip()
                if guest_ip == ip:
                    vm_path = os.path.dirname(vm)
                    vm_name = os.path.basename(vm_path)
                    logger.info(f"虚拟机 {vm_name} 已就绪")
                    if vm_name == 'template':
                        continue
                    ip_address = vm_name
                    return ip_address
            except subprocess.CalledProcessError:
                continue
        
        return None
    except subprocess.CalledProcessError as e:
        logger.error(f"执行 vmrun 命令时发生错误: {e}")
        raise

def get_running_vm_name(ip):
    if vm == "Parallels Desktop":
        return _get_running_vm_name_1(ip)
    elif vm == "VMware Workstation Pro":
        return _get_running_vm_name_2(ip)

def _get_running_vm_ip_1(name):
    try:
        # 执行 prlctl list -f -j 命令获取虚拟机列表
        output = subprocess.check_output(['prlctl', 'list', '-f', '-j']).decode('utf-8')
        vm_list = json.loads(output)

        # 寻找与虚拟机 NAME 匹配的虚拟机 IP
        for vm in vm_list:
            if 'name' in vm and vm['name'] == name:
                return vm['ip_configured']
        
        logger.warning(f"未找到匹配 NAME '{name}' 的运行中虚拟机.")
        return None
    except subprocess.CalledProcessError as e:
        logger.error(f"执行 prlctl 命令时发生错误: {e}")
        raise  # 将异常向上抛出
    except json.JSONDecodeError as e:
        logger.error(f"解析 prlctl 输出为 JSON 时发生错误: {e}")
        raise  # 将异常向上抛出

def _get_running_vm_ip_2(name):
    try:
        vm_path = os.path.join(vmsp.workdir, name, f"{name}.vmx")
        guest_ip = subprocess.run(['vmrun', 'getGuestIPAddress', vm_path], shell=True, check=True, capture_output=True, text=True, encoding="utf-8").stdout.strip()
        return guest_ip
    except subprocess.CalledProcessError as e:
        return None
    except Exception as e:
        logger.error(f"获取虚拟机 IP 地址时发生错误: {e}")
        raise

def get_running_vm_ip(name):
    if vm == "Parallels Desktop":
        return _get_running_vm_ip_1(name)
    elif vm == "VMware Workstation Pro":
        return _get_running_vm_ip_2(name)

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
                    
        def respond_with_success():
            self.send_response(204)
            self.end_headers()

        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            received_ip = data.get('ip', None)

            if received_ip is None:
                self.send_error(422)
                logger.warning(f"解析 JSON 数据时发生错误: 未收到有效的 IP 地址")
                return

            if self.path == '/set_vm':
                respond_with_success()
                clone_vm(received_ip)

            elif self.path == '/reset_vm':
                respond_with_success()
                reset_vm(received_ip)

            elif self.path == '/delete_vm':
                respond_with_success()
                delete_vm(received_ip)

            else:
                self.send_error(404)

        except Exception as e:
            logger.error(f"处理 POST 请求时发生异常: {e}")
            self.send_error(500)

    def do_GET(self):
                    
        def respond_with_success():
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode())

        try:
            if self.path == '/get_ip':
                client_ip = self.client_address[0]

                vm_name = get_running_vm_name(client_ip)

                if vm_name:
                    response = {'ip': vm_name}
                else:
                    response = {'error': '未找到匹配 IP 的运行中虚拟机'}

                respond_with_success()

            elif self.path.startswith('/get_vm_ip'):
                parsed_path = urlparse(self.path)
                query_params = parse_qs(parsed_path.query)
                client_name = query_params.get('ip', [None])[0]

                vm_ip = get_running_vm_ip(client_name)

                if vm_ip:
                    response = {'ip': vm_ip}
                else:
                    response = {'error': '未找到匹配 NAME 的运行中虚拟机'}

                respond_with_success()

            else:
                self.send_error(404)

        except Exception as e:
            logger.error(f"处理 GET 请求时发生异常: {e}")
            self.send_error(500)

def run(server_class=HTTPServer, handler_class=SimpleHTTPRequestHandler, port=5000):
    try:
        server_address = ('', port)
        httpd = server_class(server_address, handler_class)
        logger.info(f'正在启动服务器，端口号 {port}...')
        httpd.serve_forever()
    except OSError as e:
        logger.error(f"启动服务器时发生错误: {e}")

if __name__ == '__main__':
    run()
