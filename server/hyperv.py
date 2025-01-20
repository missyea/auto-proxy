import subprocess
import json


class HyperVSDK:
    def __init__(self):
        self._verify_hyperv_enabled()

    def _verify_hyperv_enabled(self):
        try:
            self._run_command("Get-VMHost")
        except Exception as e:
            raise Exception("Hyper-V is not enabled or not accessible") from e

    def _run_command(self, command):
        try:
            result = subprocess.run(
                ["powershell", "-Command", command],
                capture_output=True,
                text=True,
                encoding="gbk",
            )
            if result.returncode != 0:
                raise Exception(f"Command failed: {result.stderr}")
            return result.stdout.strip()
        except Exception:
            raise

    def start(self, vm_name):
        self._run_command("Start-VM -Name '" + vm_name + "'")

    def stop(self, vm_name, force=False):
        cmd = "Stop-VM -Name '" + vm_name + "'"
        if force:
            cmd += " -Force"
        self._run_command(cmd)

    def reset(self, vm_name):
        self._run_command(f"Restart-VM -Name '{vm_name}' -Force")

    def clone(self, template_name, new_name, path):
        template_vhdx = path + "\\" + template_name + ".vhdx"
        new_vhdx = path + "\\" + new_name + ".vhdx"

        # 克隆磁盘并创建VM
        vm_create = f"""
        Copy-Item -Path '{template_vhdx}' -Destination '{new_vhdx}'
        $vs = Get-VMSwitch
        New-VM -Name '{new_name}' -NoVHD -MemoryStartupBytes 2GB -Generation 2 -SwitchName $vs[0].Name
        Set-VM -Name '{new_name}' -ProcessorCount 4 -DynamicMemory -MemoryMinimumBytes 512MB -MemoryMaximumBytes 4GB
        Add-VMHardDiskDrive -VMName '{new_name}' -Path '{new_vhdx}'
        Set-VMFirmware -VMName '{new_name}' -FirstBootDevice (Get-VMHardDiskDrive -VMName '{new_name}')
        """
        self._run_command(vm_create)

    def delete(self, vm_name, path):
        if self.exists(vm_name):
            try:
                self.stop(vm_name, force=True)
            except Exception:
                pass

            self._run_command("Remove-VM -Name '" + vm_name + "' -Force")

            vhdx_path = path + "\\" + vm_name + ".vhdx"
            bak_path = vhdx_path + "_bak"
            try:
                self._run_command(
                    f"Move-Item -Path '{vhdx_path}' -Destination '{bak_path}' -Force"
                )
            except Exception:
                pass

    def exists(self, vm_name):
        cmd = f"(Get-VM -Name '{vm_name}' -ErrorAction SilentlyContinue) -ne $null"
        try:
            result = self._run_command(cmd)
            return result.lower() == "true"
        except Exception:
            return False

    def is_running(self, vm_name):
        cmd = f"(Get-VM -Name '{vm_name}').State -eq 2"
        try:
            result = self._run_command(cmd)
            return result.lower() == "true"
        except Exception:
            return False

    def get_ip_address(self, vm_name):
        try:
            cmd = (
                "(Get-VMNetworkAdapter -VMName '" + vm_name + "').IPAddresses "
                "| Where-Object { $_ -match '^\\d+\\.\\d+\\.\\d+\\.\\d+$' } "
                "| Select-Object -First 1"
            )
            result = self._run_command(cmd)
            return result if result else None
        except Exception:
            return None

    def get_vm_path(self, vm_name):
        try:
            return self._run_command(
                "(Get-VM -Name '" + vm_name + "').ConfigurationLocation"
            )
        except Exception:
            return None

    def list_vms(self, include_off=True):
        cmd = """
        Get-VM | ForEach-Object {
            $vm = $_
            @{
                Name = $vm.Name
                Running = $vm.State -eq 2
            }
        } | ConvertTo-Json
        """
        result = self._run_command(cmd)
        vms = json.loads(result)
        return vms

    def get_vm_by_ip(self, ip_address):
        vms = self.list_vms()
        for vm in vms:
            if vm.get("Running"):
                current_ip = self.get_ip_address(vm["Name"])
                if current_ip and current_ip == ip_address:
                    return vm
        return None

    def rename_vm(self, old_name, new_name):
        try:
            cmd = f"Rename-VM -Name '{old_name}' -NewName '{new_name}'"
            self._run_command(cmd)
        except Exception:
            raise

    def rename_vhdx(self, vm_name, old_path, new_path):
        try:
            cmd = f"""
            Move-Item -Path '{old_path}' -Destination '{new_path}' -Force
            Get-VM -Name '{vm_name}' | Get-VMHardDiskDrive | Set-VMHardDiskDrive -Path '{new_path}'
            """
            self._run_command(cmd)
        except Exception:
            raise

    def resolve_dns(self, host):
        try:
            cmd = f"(Resolve-DnsName -Name {host} -Type A).IPAddress"
            self._run_command(cmd)
        except Exception:
            return None
