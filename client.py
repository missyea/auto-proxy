import http.client
import json
import subprocess

def get_received_ip(api_host, api_path):
    try:
        conn = http.client.HTTPConnection(api_host)
        conn.request("GET", api_path)
        response = conn.getresponse()

        if response.status == 200:
            data = response.read()
            json_data = json.loads(data)
            received_ip = json_data.get('received_ip')
            conn.close()
            return received_ip
        else:
            print(f"请求失败，状态码：{response.status}")
            print(response.read())
            conn.close()
            return None
    except Exception as e:
        print(f"请求过程中发生错误: {e}")
        return None

def update_json_file(file_path, new_ip):
    try:
        with open(file_path, 'r') as file:
            config_data = json.load(file)

        for outbound in config_data.get('outbounds', []):
            for server in outbound.get('settings', {}).get('servers', []):
                if 'address' in server:
                    server['address'] = new_ip

        with open(file_path, 'w') as file:
            json.dump(config_data, file, indent=4)

        print(f"数据已成功写回到 {file_path}")
    except Exception as e:
        print(f"更新JSON文件时发生错误: {e}")

def is_address_empty(file_path):
    try:
        with open(file_path, 'r') as file:
            config_data = json.load(file)

        for outbound in config_data.get('outbounds', []):
            for server in outbound.get('settings', {}).get('servers', []):
                if 'address' in server and (server['address'] == '' or server['address'] is None):
                    return True
        return False
    except Exception as e:
        print(f"检查地址时发生错误: {e}")
        return False

def restart_service(service_name):
    try:
        result = subprocess.run(['systemctl', 'restart', service_name], check=True, text=True, capture_output=True)
        print(f"成功重启服务: {service_name}")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"重启服务 {service_name} 时发生错误:")
        print(e.stderr)

def main():
    api_host = '10.211.55.2:5000'
    api_path = '/get_ip'
    file_path = '/usr/local/etc/xray/config.json'
    service_name = 'xray'

    if is_address_empty(file_path):
        print("address 为空，需要更新。")
        received_ip = get_received_ip(api_host, api_path)

        if received_ip:
            print(f"成功获取 received_ip: {received_ip}")
            update_json_file(file_path, received_ip)
            restart_service(service_name)
        else:
            print("未能获取到有效的 received_ip")
    else:
        print("address 已有值，无需更新。")

if __name__ == '__main__':
    main()
