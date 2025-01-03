# Check administrator privileges
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Warning "Please run as administrator!"
    break
}

# Get all VMs
$vms = Get-VM

foreach ($vm in $vms) {
    try {
        Write-Host "Processing: $($vm.Name)"
        
        # Store original state
        $wasRunning = $vm.State -eq 'Running'
        
        if ($wasRunning) {
            Stop-VM -Name $vm.Name
            while ((Get-VM -Name $vm.Name).State -ne 'Off') {
                Start-Sleep -Seconds 1
            }
        }
        
        Set-VMProcessor -VMName $vm.Name -Count 2
        
        if ($wasRunning) {
            Start-VM -Name $vm.Name
        }
        
        Write-Host "Done" -ForegroundColor Green
        
    } catch {
        Write-Host "Error processing $($vm.Name): $($_.Exception.Message)" -ForegroundColor Red
        continue
    }
}