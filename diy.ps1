# Check administrator privileges
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Warning "Please run as administrator!"
    break
}

function Show-Menu {
    Clear-Host
    Write-Host "================ Hyper-V Batch Management ================"
    Write-Host "1: Set all VMs to 2 CPU cores"
    Write-Host "2: Resize all VM disks to 60GB"
    Write-Host "Q: Quit"
    Write-Host "====================================================="
}

function Process-VMs {
    param (
        [Parameter(Mandatory=$true)]
        [string]$operationType,
        [Parameter(Mandatory=$true)]
        [scriptblock]$operation
    )
    
    $vms = Get-VM
    foreach ($vm in $vms) {
        try {
            Write-Host "Processing $operationType for: $($vm.Name)"
            $wasRunning = $vm.State -eq 'Running'
            
            if ($wasRunning) {
                Stop-VM -Name $vm.Name
                while ((Get-VM -Name $vm.Name).State -ne 'Off') {
                    Start-Sleep -Seconds 1
                }
            }
            
            & $operation $vm
            
            if ($wasRunning) {
                Start-VM -Name $vm.Name
            }
            
            Write-Host "Done" -ForegroundColor Green
            
        } catch {
            Write-Host "Error processing $($vm.Name): $($_.Exception.Message)" -ForegroundColor Red
            continue
        }
    }
    Write-Host "`nPress any key to return to menu..."
    $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
}

function Set-VMsCPU {
    Process-VMs -operationType "CPU cores" -operation { 
        param($vm)
        Set-VMProcessor -VMName $vm.Name -Count 2
    }
}

function Set-VMsDiskSize {
    Process-VMs -operationType "disk" -operation { 
        param($vm)
        $vhdPath = $vm.HardDrives.Path
        Write-Host "Resizing disk: $vhdPath"
        Resize-VHD -Path $vhdPath -SizeBytes 60GB
    }
}

do {
    Show-Menu
    $selection = Read-Host "Please make a selection"
    switch ($selection) {
        '1' { Set-VMsCPU }
        '2' { Set-VMsDiskSize }
    }
} until ($selection -eq 'q')