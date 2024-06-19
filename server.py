import subprocess
import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clone_vm(ip):
    try:
        template_vm_name = "template"
        new_vm_name = ip
        
        # 检查虚拟机是否已存在
        status_code = subprocess.call(['prlctl', 'status', new_vm_name])
        if status_code == 255:  # 虚拟机不存在
            # 如果模板虚拟机在运行，则停止它
            template_status = subprocess.check_output(['prlctl', 'status', template_vm_name]).decode('ascii')
            if 'stopped' not in template_status:
                subprocess.call(['prlctl', 'stop', template_vm_name, "--drop-state"])
            
            # 克隆模板虚拟机
            subprocess.call(['prlctl', 'clone', template_vm_name, '--name', new_vm_name])
            logger.info(f"虚拟机 '{new_vm_name}' 克隆成功.")
        
        # 启动新的虚拟机
        subprocess.call(['prlctl', 'start', new_vm_name])
    except subprocess.CalledProcessError as e:
        logger.error(f"克隆或启动虚拟机时发生错误: {e}")
        raise  # 将异常向上抛出，以便更高层次的代码处理
    except Exception as e:
        logger.error(f"处理虚拟机操作时发生未知异常: {e}")
        raise  # 同样将异常向上抛出，以便更高层次的代码处理

def get_running_vm_name(ip):
    try:
        # 执行 prlctl list -f -j 命令获取虚拟机列表
        output = subprocess.check_output(['prlctl', 'list', '-f', '-j']).decode('utf-8')
        vm_list = json.loads(output)

        # 寻找与来源 IP 匹配的虚拟机名字
        for vm in vm_list:
            if 'ip_configured' in vm and vm['ip_configured'] == ip:
                return vm['name']
        
        logger.warning(f"未找到匹配 IP '{ip}' 的运行中虚拟机.")
        return None
    except subprocess.CalledProcessError as e:
        logger.error(f"执行 prlctl 命令时发生错误: {e}")
        raise  # 将异常向上抛出
    except json.JSONDecodeError as e:
        logger.error(f"解析 prlctl 输出为 JSON 时发生错误: {e}")
        raise  # 将异常向上抛出

def get_running_vm_ip(name):
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


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        if self.path == '/set_ip':
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
                response = {'status': '已接收到 IP'}
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
