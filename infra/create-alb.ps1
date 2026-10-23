# Create target groups, the ALB, listener and path rules (safe to re-run).
. $PSScriptRoot\vars.ps1

$targets = [ordered]@{
  frontend = @(80,   "/health")
  auth     = @(5000, "/api/auth/health")
  rooms    = @(5000, "/api/rooms/health")
  weather  = @(5000, "/api/weather/health")
  booking  = @(5000, "/api/bookings/health")
}

# 1. Target groups (type "ip" is required for Fargate)
$tg = @{}
foreach ($name in $targets.Keys) {
  $port, $hc = $targets[$name]
  $arn = aws elbv2 describe-target-groups --names "crb-$name-tg" --query "TargetGroups[0].TargetGroupArn" --output text 2>$null
  if (-not $arn) {
    $arn = aws elbv2 create-target-group --name "crb-$name-tg" --protocol HTTP --port $port --vpc-id $vpc `
      --target-type ip --health-check-path $hc --health-check-interval-seconds 15 `
      --healthy-threshold-count 2 --unhealthy-threshold-count 3 `
      --query "TargetGroups[0].TargetGroupArn" --output text
    # Drain old tasks in 30s instead of 300s -> faster rolling deploys
    aws elbv2 modify-target-group-attributes --target-group-arn $arn `
      --attributes Key=deregistration_delay.timeout_seconds,Value=30 | Out-Null
  }
  $tg[$name] = $arn
  Write-Host "target group  crb-$name-tg  (health: $hc)"
}

# 2. Load balancer
$alb = aws elbv2 describe-load-balancers --names crb-alb --query "LoadBalancers[0].LoadBalancerArn" --output text 2>$null
if (-not $alb) {
  $alb = aws elbv2 create-load-balancer --name crb-alb --type application --scheme internet-facing `
    --subnets $sub --security-groups $albSg --query "LoadBalancers[0].LoadBalancerArn" --output text
  Write-Host "created load balancer crb-alb"
}

# 3. Listener on port 80 (default -> frontend) + path rules
$listener = aws elbv2 describe-listeners --load-balancer-arn $alb --query "Listeners[0].ListenerArn" --output text
if (-not $listener -or $listener -eq "None") {
  $listener = aws elbv2 create-listener --load-balancer-arn $alb --protocol HTTP --port 80 `
    --default-actions "Type=forward,TargetGroupArn=$($tg.frontend)" --query "Listeners[0].ListenerArn" --output text
  $prio = 10
  foreach ($r in @(@("auth", "/api/auth*"), @("rooms", "/api/rooms*"), @("weather", "/api/weather*"), @("booking", "/api/bookings*"))) {
    aws elbv2 create-rule --listener-arn $listener --priority $prio `
      --conditions "Field=path-pattern,Values=$($r[1])" `
      --actions "Type=forward,TargetGroupArn=$($tg[$r[0]])" | Out-Null
    Write-Host "rule          $($r[1]) -> crb-$($r[0])-tg"
    $prio += 10
  }
}

$dns = aws elbv2 describe-load-balancers --load-balancer-arns $alb --query "LoadBalancers[0].DNSName" --output text
Write-Host "`nALB URL: http://$dns"