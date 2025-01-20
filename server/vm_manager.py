from abc import ABC, abstractmethod
from vmrun import VMwareWorkstationSDK
from hyperv import HyperVSDK
from config import WORKDIR, TEMPLATE_VM_NAME
import os
import re


class VMManager(ABC):
    @abstractmethod
    def clone_vm(self, ip):
        pass

    @abstractmethod
    def reset_vm(self, ip):
        pass

    @abstractmethod
    def stop_vm(self, ip):
        pass

    @abstractmethod
    def delete_vm(self, ip):
        pass

    @abstractmethod
    def get_running_vm_name(self, ip):
        pass

    @abstractmethod
    def get_running_vm_ip(self, name):
        pass

    @abstractmethod
    def get_vm_list(self):
        pass


class VMwareManager(VMManager):
    def __init__(self):
        self.workdir = WORKDIR
        self.template_vm_name = TEMPLATE_VM_NAME
        self.template_vm_path = os.path.join(
            self.workdir, self.template_vm_name, f"{self.template_vm_name}.vmx"
        )
        self.vmrun = VMwareWorkstationSDK()

    def clone_vm(self, ip):
        new_vm_name = ip
        new_vm_path = os.path.join(self.workdir, new_vm_name, f"{new_vm_name}.vmx")

        try:
            try:
                self.vmrun.stop(self.template_vm_path, mode="hard")
            except Exception:
                pass

            try:
                tools_state = self.vmrun.check_tools_state(new_vm_path)
                if "installed" in tools_state.lower():
                    return
                elif "running" in tools_state.lower():
                    return
            except Exception:
                self.vmrun.clone(
                    self.template_vm_path,
                    new_vm_path,
                    full=True,
                    clone_name=new_vm_name,
                )

            self.vmrun.start(new_vm_path, gui=False)
        except Exception:
            raise

    def reset_vm(self, ip):
        vm_path = self._get_vm_path(ip)
        self.vmrun.stop(vm_path)
        self.vmrun.start(vm_path, gui=False)

    def stop_vm(self, ip):
        try:
            vm_path = self._get_vm_path(ip)
            self.vmrun.stop(vm_path)
        except Exception:
            pass

    def delete_vm(self, ip):
        try:
            vm_path = self._get_vm_path(ip)
            try:
                self.vmrun.stop(vm_path, mode="hard")
            except Exception:
                pass
            self.vmrun.delete_vm(vm_path)
        except Exception:
            pass

    def get_running_vm_name(self, ip):
        vm_list = self.vmrun.list().splitlines()[1:]
        for vm in vm_list:
            try:
                guest_ip = self.vmrun.get_guest_ip_address(vm)
                if guest_ip == ip:
                    vm_path = os.path.dirname(vm)
                    vm_name = os.path.basename(vm_path)
                    if vm_name != self.template_vm_name:
                        return vm_name
            except Exception:
                continue
        return None

    def get_running_vm_ip(self, name):
        vm_path = self._get_vm_path(name)
        try:
            guest_ip = self.vmrun.get_guest_ip_address(vm_path)
            return guest_ip if guest_ip != "unknown" else None
        except Exception:
            return None

    def get_vm_list(self):
        try:
            vm_directories = [
                d
                for d in os.listdir(self.workdir)
                if os.path.isdir(os.path.join(self.workdir, d))
                and re.match(r"^\d+\.\d+\.\d+\.\d+$", d)
            ]

            running_vms = self.vmrun.list().splitlines()[1:]
            running_ips = [
                os.path.basename(os.path.dirname(vm_path)) for vm_path in running_vms
            ]

            vm_list = []
            for vm_name in vm_directories:
                is_running = vm_name in running_ips
                vm_list.append({"ip": vm_name, "running": is_running})

            return vm_list
        except Exception:
            return []

    def _get_vm_path(self, name):
        return os.path.join(self.workdir, name, f"{name}.vmx")


class HyperVManager(VMManager):
    def __init__(self):
        self.workdir = WORKDIR
        self.template_vm_name = TEMPLATE_VM_NAME
        self.hyperv = HyperVSDK()

    def clone_vm(self, ip, last_ip=None):
        try:
            if last_ip and last_ip != ip:
                try:
                    if self.hyperv.exists(last_ip):
                        if self.hyperv.is_running(last_ip):
                            self.hyperv.stop(last_ip)

                        old_path = os.path.join(self.workdir, f"{last_ip}.vhdx")
                        new_path = os.path.join(self.workdir, f"{ip}.vhdx")

                        self.hyperv.rename_vhdx(last_ip, old_path, new_path)
                        self.hyperv.rename_vm(last_ip, ip)

                        self.hyperv.start(ip)
                        return
                except Exception:
                    raise

            vm_exists = self.hyperv.exists(ip)
            if vm_exists:
                if not self.hyperv.is_running(ip):
                    self.hyperv.start(ip)
                return

            self.hyperv.clone(
                template_name=self.template_vm_name,
                new_name=ip,
                path=self.workdir,
            )
            self.hyperv.start(ip)

        except Exception:
            raise

    def reset_vm(self, ip):
        try:
            self.hyperv.reset(ip)
        except Exception:
            raise

    def stop_vm(self, ip):
        try:
            if self.hyperv.is_running(ip):
                self.hyperv.stop(ip)
        except Exception:
            pass

    def delete_vm(self, ip):
        try:
            self.hyperv.delete(ip, path=self.workdir)
        except Exception:
            pass

    def get_running_vm_name(self, ip):
        try:
            vm = self.hyperv.get_vm_by_ip(ip)
            if vm and vm["Name"] != self.template_vm_name:
                return vm["Name"]
            return None
        except Exception:
            return None

    def get_running_vm_ip(self, name):
        try:
            return self.hyperv.get_ip_address(name)
        except Exception:
            return None

    def get_vm_list(self):
        try:
            vms = self.hyperv.list_vms()
            return [
                {"ip": vm["Name"], "running": vm["Running"]}
                for vm in vms
                if vm["Name"] != self.template_vm_name
            ]
        except Exception:
            return []
