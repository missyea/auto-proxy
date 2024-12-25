from abc import ABC, abstractmethod
from typing import Optional, Dict, List
from vmrun import VMwareWorkstationSDK
from config import WORKDIR, TEMPLATE_VM_NAME, USER, PASSWORD

import logging
import subprocess
import json
import base64
import os
import re

logger = logging.getLogger(__name__)

vmrun = VMwareWorkstationSDK()


class VMManager(ABC):
    @abstractmethod
    def clone_vm(self, ip: str) -> None:
        pass

    @abstractmethod
    def reset_vm(self, ip: str) -> None:
        pass

    @abstractmethod
    def stop_vm(self, ip: str) -> None:
        pass

    @abstractmethod
    def delete_vm(self, ip: str) -> None:
        pass

    @abstractmethod
    def get_running_vm_name(self, ip: str) -> Optional[str]:
        pass

    @abstractmethod
    def get_running_vm_ip(self, name: str) -> Optional[str]:
        pass

    @abstractmethod
    def get_vm_list(self) -> List[str]:
        pass


class VMwareManager(VMManager):
    def __init__(self):
        self.workdir = WORKDIR
        self.template_vm_name = TEMPLATE_VM_NAME
        self.template_vm_path = os.path.join(
            self.workdir, self.template_vm_name, f"{self.template_vm_name}.vmx"
        )
        self.headers = self._get_headers()

    def _get_headers(self) -> Dict[str, str]:
        auth_string = base64.b64encode(f"{USER}:{PASSWORD}".encode("ascii"))
        return {
            "Authorization": f"Basic {auth_string.decode('ascii')}",
            "Content-type": "application/vnd.vmware.vmw.rest-v1+json",
            "Accept": "application/vnd.vmware.vmw.rest-v1+json",
        }

    def _run_vmware_command(
        self, command: str, *args: str, check: bool = True
    ) -> subprocess.CompletedProcess:
        full_command = ["vmrun", command, *args]
        return subprocess.run(
            full_command,
            shell=True,
            check=check,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def clone_vm(self, ip: str) -> None:
        new_vm_name = ip
        new_vm_path = os.path.join(self.workdir, new_vm_name, f"{new_vm_name}.vmx")

        try:
            self._run_vmware_command("stop", self.template_vm_path, "hard")
            logger.info(f"Template VM '{self.template_vm_name}' stopped successfully")
        except subprocess.CalledProcessError:
            logger.info(f"Template VM '{self.template_vm_name}' was not running")

        tools_state = self._run_vmware_command(
            "checkToolsState", new_vm_path, check=False
        ).stdout.strip()
        if "installed" in tools_state.lower():
            logger.info(f"VM {new_vm_name} already exists")
        elif "running" in tools_state.lower():
            logger.info(f"VM {new_vm_name} is already running")
            return
        else:
            clone_cmd = [
                "clone",
                self.template_vm_path,
                new_vm_path,
                "full",
                f"-cloneName={new_vm_name}",
            ]
            self._run_vmware_command(*clone_cmd)
            logger.info(f"VM {new_vm_name} cloned successfully")

        # self._run_vmware_command("start", new_vm_path)
        vmrun.start(new_vm_path, False)
        logger.info(f"VM {new_vm_name} started successfully")

    def reset_vm(self, ip: str) -> None:
        vm_path = self._get_vm_path(ip)
        vmrun.stop(vm_path)
        vmrun.start(vm_path, False)
        logger.info(f"VM {ip} has been reset")

    def stop_vm(self, ip: str) -> None:
        try:
            vm_path = self._get_vm_path(ip)
            vmrun.stop(vm_path)
            logger.info(f"VM {ip} has been stop")
        except Exception:
            logger.info(f"VM '{ip}' was not running")

    def delete_vm(self, ip: str) -> None:
        vm_path = self._get_vm_path(ip)
        self._run_vmware_command("stop", vm_path, "hard", check=False)
        self._run_vmware_command("deleteVM", vm_path, check=False)
        logger.info(f"VM {ip} has been deleted")

    def get_running_vm_name(self, ip: str) -> Optional[str]:
        vm_list = self._run_vmware_command("list").stdout.splitlines()[1:]
        for vm in vm_list:
            try:
                guest_ip = self._run_vmware_command(
                    "getGuestIPAddress", vm
                ).stdout.strip()
                if guest_ip == ip:
                    vm_path = os.path.dirname(vm)
                    vm_name = os.path.basename(vm_path)
                    if vm_name != self.template_vm_name:
                        logger.info(f"VM {vm_name} is ready")
                        return vm_name
            except subprocess.CalledProcessError:
                continue
        return None

    def get_running_vm_ip(self, name: str) -> Optional[str]:
        vm_path = self._get_vm_path(name)
        try:
            guest_ip = vmrun.get_guest_ip_address(vm_path)
            return guest_ip if guest_ip != "unknown" else None
        except subprocess.CalledProcessError:
            return None
        except Exception as e:
            return None

    def get_vm_list(self) -> List[str]:
        try:

            vm_directories = [
                d
                for d in os.listdir(self.workdir)
                if os.path.isdir(os.path.join(self.workdir, d))
                and re.match(r"^\d+\.\d+\.\d+\.\d+$", d)
            ]

            running_vms = vmrun.list().splitlines()[1:]
            running_ips = [
                os.path.basename(os.path.dirname(vm_path)) for vm_path in running_vms
            ]

            vm_list = []
            for vm_name in vm_directories:
                is_running = vm_name in running_ips
                vm_list.append({"ip": vm_name, "running": is_running})

            return vm_list

        except Exception as e:
            print(f"An error occurred: {e}")
            return []

    def _get_vm_path(self, name: str) -> str:
        return os.path.join(self.workdir, name, f"{name}.vmx")


class ParallelsManager(VMManager):
    def __init__(self):
        self.template_vm_name = TEMPLATE_VM_NAME

    def _run_parallels_command(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["prlctl", *args],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def clone_vm(self, ip: str) -> None:
        new_vm_name = ip
        status = subprocess.call(["prlctl", "status", new_vm_name])

        if status == 255:
            template_status = self._run_parallels_command(
                "status", self.template_vm_name
            ).stdout
            if "stopped" not in template_status:
                self._run_parallels_command(
                    "stop", self.template_vm_name, "--drop-state"
                )

            self._run_parallels_command(
                "clone", self.template_vm_name, "--name", new_vm_name
            )
            logger.info(f"VM {new_vm_name} cloned successfully")

        self._run_parallels_command("start", new_vm_name)

    def reset_vm(self, ip: str) -> None:
        self._run_parallels_command("reset", ip)
        logger.info(f"VM {ip} has been reset")

    def delete_vm(self, ip: str) -> None:
        self._run_parallels_command("delete", ip)
        logger.info(f"VM {ip} has been deleted")

    def get_running_vm_name(self, ip: str) -> Optional[str]:
        output = self._run_parallels_command("list", "-f", "-j").stdout
        vm_list = json.loads(output)

        for vm in vm_list:
            if "ip_configured" in vm and vm["ip_configured"] == ip:
                return vm["name"]

        logger.warning(f"No running VM found matching IP '{ip}'.")
        return None

    def get_running_vm_ip(self, name: str) -> Optional[str]:
        output = self._run_parallels_command("list", "-f", "-j").stdout
        vm_list = json.loads(output)

        for vm in vm_list:
            if "name" in vm and vm["name"] == name:
                return vm["ip_configured"]

        logger.warning(f"No running VM found matching NAME '{name}'.")
        return None
