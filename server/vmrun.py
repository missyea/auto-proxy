import subprocess


class VMwareWorkstationSDK:
    def __init__(self, vmrun_path="vmrun"):
        self.vmrun_path = vmrun_path

    def _run_command(self, command, *args):
        full_command = [self.vmrun_path, command] + list(args)
        result = subprocess.run(
            full_command, capture_output=True, text=True, encoding="utf-8"
        )
        if result.returncode != 0:
            raise Exception(f"Command failed: {result.stderr}")
        return result.stdout.strip()

    # Power Commands
    def start(self, vmx_path, gui=True):
        return self._run_command("start", vmx_path, "gui" if gui else "nogui")

    def stop(self, vmx_path, mode="soft"):
        return self._run_command("stop", vmx_path, mode)

    def reset(self, vmx_path, mode="soft"):
        return self._run_command("reset", vmx_path, mode)

    def suspend(self, vmx_path, mode="soft"):
        return self._run_command("suspend", vmx_path, mode)

    def pause(self, vmx_path):
        return self._run_command("pause", vmx_path)

    def unpause(self, vmx_path):
        return self._run_command("unpause", vmx_path)

    # Snapshot Commands
    def list_snapshots(self, vmx_path, show_tree=False):
        args = ["listSnapshots", vmx_path]
        if show_tree:
            args.append("showtree")
        return self._run_command(*args)

    def snapshot(self, vmx_path, snapshot_name):
        return self._run_command("snapshot", vmx_path, snapshot_name)

    def delete_snapshot(self, vmx_path, snapshot_name, delete_children=False):
        args = ["deleteSnapshot", vmx_path, snapshot_name]
        if delete_children:
            args.append("andDeleteChildren")
        return self._run_command(*args)

    def revert_to_snapshot(self, vmx_path, snapshot_name):
        return self._run_command("revertToSnapshot", vmx_path, snapshot_name)

    # Guest OS Commands
    def run_program_in_guest(
        self,
        vmx_path,
        program_path,
        *args,
        wait=True,
        active_window=False,
        interactive=False,
    ):
        cmd_args = ["runProgramInGuest", vmx_path]
        if not wait:
            cmd_args.append("-noWait")
        if active_window:
            cmd_args.append("-activeWindow")
        if interactive:
            cmd_args.append("-interactive")
        cmd_args.append(program_path)
        cmd_args.extend(args)
        return self._run_command(*cmd_args)

    def file_exists_in_guest(self, vmx_path, file_path):
        return self._run_command("fileExistsInGuest", vmx_path, file_path)

    def directory_exists_in_guest(self, vmx_path, dir_path):
        return self._run_command("directoryExistsInGuest", vmx_path, dir_path)

    def list_processes_in_guest(self, vmx_path):
        return self._run_command("listProcessesInGuest", vmx_path)

    def kill_process_in_guest(self, vmx_path, pid):
        return self._run_command("killProcessInGuest", vmx_path, str(pid))

    def run_script_in_guest(
        self,
        vmx_path,
        interpreter_path,
        script_text,
        wait=True,
        active_window=False,
        interactive=False,
    ):
        cmd_args = ["runScriptInGuest", vmx_path]
        if not wait:
            cmd_args.append("-noWait")
        if active_window:
            cmd_args.append("-activeWindow")
        if interactive:
            cmd_args.append("-interactive")
        cmd_args.extend([interpreter_path, script_text])
        return self._run_command(*cmd_args)

    def get_guest_ip_address(self, vmx_path, wait=False):
        args = ["getGuestIPAddress", vmx_path]
        if wait:
            args.append("-wait")
        return self._run_command(*args)

    # General Commands
    def list(self):
        return self._run_command("list")

    def upgrade_vm(self, vmx_path):
        return self._run_command("upgradevm", vmx_path)

    def install_tools(self, vmx_path):
        return self._run_command("installTools", vmx_path)

    def check_tools_state(self, vmx_path):
        return self._run_command("checkToolsState", vmx_path)

    def delete_vm(self, vmx_path):
        return self._run_command("deleteVM", vmx_path)

    def clone(
        self, vmx_path, destination_path, full=True, clone_name=None, snapshot_name=None
    ):
        args = ["clone", vmx_path, destination_path, "full" if full else "linked"]
        if clone_name:
            args.append(f"-cloneName={clone_name}")
        if snapshot_name:
            args.append(f"-snapshot={snapshot_name}")
        return self._run_command(*args)