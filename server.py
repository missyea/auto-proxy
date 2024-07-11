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

# vm = 'VMware Workstation Pro'
vm = 'Parallels Desktop'

class VMwareServerParams():
    def __init__(self):
        self.server_ip = "10.10.10.132"
        self.server_port = 8697
        self.host = ("%s:%s" % (self.server_ip, self.server_port))
        self.workdir = "D:/Virtual Machines/"

        user = "admin"
        password = "Aa12345."
        authentication_string = base64.b64encode((user + ":" + password).encode('ascii'))

        self.headers = {
            "Authorization": ("Basic %s" % authentication_string.decode('ascii')),
            "Content-type": "application/vnd.vmware.vmw.rest-v1+json",
            "Accept": "application/vnd.vmware.vmw.rest-v1+json"
        }

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
        logger.info(f"虚拟机 '{new_vm_name}' 克隆成功")

    subprocess.call(['prlctl', 'start', new_vm_name])

def _clone_vm_2(ip):
    vmsp = VMwareServerParams()
    new_vm_name = ip
    template_vm_name = "template"
    template_vmx_path = os.path.join(vmsp.workdir, template_vm_name, f"{template_vm_name}.vmx")
    new_vm_path = os.path.join(vmsp.workdir, new_vm_name, f"{new_vm_name}.vmx")

    try:
        tools_state_output = subprocess.check_output(['vmrun', 'checkToolsState', new_vm_path]).decode('ascii')
        if 'installed' in tools_state_output.lower():
            logger.info(f"虚拟机 '{new_vm_name}' 已存在，直接启动")
            subprocess.call(['vmrun', 'start', new_vm_path])
            logger.info(f"虚拟机 '{new_vm_name}' 启动成功")
            return
    except subprocess.CalledProcessError:
        pass

    try:
        subprocess.call(['vmrun', 'stop', template_vmx_path, 'hard'])
        logger.info(f"模板虚拟机 '{template_vm_name}' 停止成功")
    except subprocess.CalledProcessError:
        pass

    clone_cmd = [
        'vmrun',
        'clone',
        template_vmx_path,
        new_vm_path,
        'full'
    ]
    subprocess.call(clone_cmd)
    logger.info(f"虚拟机 '{new_vm_name}' 克隆成功")

    subprocess.call(['vmrun', 'start', new_vm_path])
    logger.info(f"虚拟机 '{new_vm_name}' 启动成功")

def clone_vm(ip):
    if vm == "Parallels Desktop":
        _clone_vm_1(ip)
    elif vm == "VMware Workstation Pro":
        _clone_vm_2(ip)

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
        output = subprocess.check_output(['vmrun', 'list']).decode('utf-8')
        vm_list = output.strip().split('\n')

        for vm in vm_list:
            try:
                guest_ip_output = subprocess.check_output(['vmrun', 'getGuestIPAddress', vm]).decode('utf-8')
                guest_ip = guest_ip_output.strip()
                if guest_ip == ip:
                    vm_path = os.path.dirname(vm)
                    vm_name = os.path.basename(vm_path)
                    ip_address = vm_name[:-4]
                    return ip_address
            except subprocess.CalledProcessError:
                continue
        
        logger.warning(f"未找到匹配 IP '{ip}' 的运行中虚拟机.")
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
        
        guest_ip_output = subprocess.check_output(['vmrun', 'getGuestIPAddress', vm_path]).decode('utf-8')
        guest_ip = guest_ip_output.strip()
        
        return guest_ip
    except subprocess.CalledProcessError as e:
        logger.error(f"执行 vmrun 命令时发生错误: {e}")
        raise
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
        if self.path == '/set_vm':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data)
                received_ip = data.get('ip', None)

                if received_ip is None:
                    raise ValueError("未收到有效的 IP 地址")

                # 响应客户端
                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.end_headers()
                response = {'status': 200}
                self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))

                # 如果接收到 IP，则克隆并启动虚拟机
                clone_vm(received_ip)
            except ValueError as e:
                logger.error(f"解析 JSON 数据时发生错误: {e}")
                self.send_error(400, "无效的 JSON 数据")
            except Exception as e:
                logger.error(f"处理 POST 请求时发生异常: {e}")
                self.send_error(500, "服务器内部错误")
        else:
            self.send_error(404, "未找到".encode('utf-8'))

    def do_GET(self):
        if self.path == '/get_ip':
            try:
                # 获取客户端 IP 地址
                client_ip = self.client_address[0]

                # 查询与客户端 IP 匹配的运行中虚拟机名字
                vm_name = get_running_vm_name(client_ip)

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()

                if vm_name:
                    response = {'ip': vm_name}
                else:
                    response = {'error': '未找到匹配 IP 的运行中虚拟机'}

                self.wfile.write(json.dumps(response,ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                logger.error(f"处理 GET 请求时发生异常: {e}")
                self.send_error(500, "服务器内部错误".encode('utf-8'))

        elif self.path.startswith('/get_vm_ip'):
            try:
                # 获取客户端 NAME
                parsed_path = urlparse(self.path)
                query_params = parse_qs(parsed_path.query)
                client_name = query_params.get('ip', [None])[0]

                # 查询与客户端 NAME 匹配的运行中虚拟机 IP
                vm_ip = get_running_vm_ip(client_name)

                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.end_headers()

                if vm_ip:
                    response = {'ip': vm_ip}
                else:
                    response = {'error': '未找到匹配 NAME 的运行中虚拟机'}

                self.wfile.write(json.dumps(response,ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                logger.error(f"处理 GET 请求时发生异常: {e}")
                self.send_error(500, "服务器内部错误".encode('utf-8'))

        else:
            self.send_error(404, "未找到".encode('utf-8'))

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
