# Stop all containers and delete the ALB. Keeps DynamoDB data, images, cluster, secret.
. $PSScriptRoot\vars.ps1
foreach ($s in "frontend","booking","weather","auth","rooms") {
  aws ecs update-service --cluster crb-cluster --service "crb-$s" --desired-count 0 | Out-Null
  Write-Host "scaled crb-$s to 0"
}
$alb = aws elbv2 describe-load-balancers --names crb-alb --query "LoadBalancers[0].LoadBalancerArn" --output text 2>$null
if ($alb) { aws elbv2 delete-load-balancer --load-balancer-arn $alb; Write-Host "deleted crb-alb" }
Write-Host "Down. Run .\infra\up.ps1 to bring it back."