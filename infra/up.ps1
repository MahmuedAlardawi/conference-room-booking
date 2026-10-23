# Recreate the ALB (if deleted) and start the services.  Usage: .\infra\up.ps1 [-Count 1]
param([int]$Count = 1)
& $PSScriptRoot\create-alb.ps1
& $PSScriptRoot\deploy.ps1 -Count $Count