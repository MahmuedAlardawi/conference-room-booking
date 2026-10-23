# Register task definitions and create/update ECS services.
# Usage: .\infra\deploy.ps1 [-Count 1] [-Tag latest]
param([int]$Count = 1, [string]$Tag = "latest")
. $PSScriptRoot\vars.ps1

$secretArn = "arn:aws:ssm:${region}:${acct}:parameter/crb/jwt-secret"
$services = [ordered]@{
  rooms    = @{ port = 5000; secret = $false }
  auth     = @{ port = 5000; secret = $true  }
  weather  = @{ port = 5000; secret = $false }
  booking  = @{ port = 5000; secret = $true  }
  frontend = @{ port = 80;   secret = $false }
}
$tmp = Join-Path $env:TEMP "crb"; New-Item -ItemType Directory -Force $tmp | Out-Null
$net = "awsvpcConfiguration={subnets=[$($sub -join ',')],securityGroups=[$svcSg],assignPublicIp=ENABLED}"

foreach ($name in $services.Keys) {
  $s = $services[$name]

  # --- Task definition ---
  $container = [ordered]@{
    name         = $name
    image        = "$reg/crb-${name}:$Tag"
    essential    = $true
    portMappings = @(@{ containerPort = $s.port; name = "http"; appProtocol = "http" })
    environment  = @(
      @{ name = "AWS_REGION";   value = $region },
      @{ name = "TABLE_PREFIX"; value = "crb-" },
      @{ name = "ROOMS_URL";    value = "http://rooms:5000" },
      @{ name = "WEATHER_URL";  value = "http://weather:5000" }
    )
    logConfiguration = @{ logDriver = "awslogs"; options = @{
      "awslogs-group" = "/ecs/crb"; "awslogs-region" = $region; "awslogs-stream-prefix" = $name } }
  }
  if ($s.secret) { $container.secrets = @(@{ name = "JWT_SECRET"; valueFrom = $secretArn }) }

  $taskDef = [ordered]@{
    family = "crb-$name"; networkMode = "awsvpc"; requiresCompatibilities = @("FARGATE")
    cpu = "256"; memory = "512"; executionRoleArn = $role; taskRoleArn = $role
    runtimePlatform = @{ cpuArchitecture = "X86_64"; operatingSystemFamily = "LINUX" }
    containerDefinitions = @($container)
  }
  [IO.File]::WriteAllText("$tmp\td-$name.json", ($taskDef | ConvertTo-Json -Depth 10))
  $tdArn = aws ecs register-task-definition --cli-input-json "file://$tmp\td-$name.json" `
             --query "taskDefinition.taskDefinitionArn" --output text

  # --- Service Connect: every service is a client; backends also publish their name ---
  $sc = @{ enabled = $true; namespace = "crb.local" }
  if ($name -ne "frontend") {
    $sc.services = @(@{ portName = "http"; discoveryName = $name; clientAliases = @(@{ port = 5000; dnsName = $name }) })
  }
  [IO.File]::WriteAllText("$tmp\sc-$name.json", ($sc | ConvertTo-Json -Depth 10))

  # --- Create or update the service ---
  $tgArn  = aws elbv2 describe-target-groups --names "crb-$name-tg" --query "TargetGroups[0].TargetGroupArn" --output text
  $exists = aws ecs describe-services --cluster crb-cluster --services "crb-$name" `
              --query "length(services[?status=='ACTIVE'])" --output text
  if ($exists -eq "0") {
    aws ecs create-service --cluster crb-cluster --service-name "crb-$name" --task-definition $tdArn `
      --desired-count $Count --launch-type FARGATE --network-configuration $net `
      --load-balancers "targetGroupArn=$tgArn,containerName=$name,containerPort=$($s.port)" `
      --health-check-grace-period-seconds 60 `
      --deployment-configuration "minimumHealthyPercent=100,maximumPercent=200,deploymentCircuitBreaker={enable=true,rollback=true}" `
      --service-connect-configuration "file://$tmp\sc-$name.json" | Out-Null
    Write-Host "created  crb-$name  ($tdArn)"
  } else {
    aws ecs update-service --cluster crb-cluster --service "crb-$name" --task-definition $tdArn `
      --desired-count $Count --service-connect-configuration "file://$tmp\sc-$name.json" `
      --force-new-deployment | Out-Null
    Write-Host "updated  crb-$name  ($tdArn)"
  }
}

Write-Host "`nWaiting for services to become stable (3-6 min)..."
aws ecs wait services-stable --cluster crb-cluster --services crb-rooms crb-auth crb-weather crb-booking crb-frontend
if ($LASTEXITCODE -eq 0) { Write-Host "All services stable." } else { Write-Host "Not stable yet - check the ECS console." }
$dns = aws elbv2 describe-load-balancers --names crb-alb --query "LoadBalancers[0].DNSName" --output text
Write-Host "App: http://$dns"