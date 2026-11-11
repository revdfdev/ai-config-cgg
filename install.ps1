# Windows PowerShell: runs the Python installer. Same flags as install.py.
Set-Location $PSScriptRoot
if (Get-Command py -ErrorAction SilentlyContinue) { py -3 install.py @args } else { python install.py @args }
exit $LASTEXITCODE
