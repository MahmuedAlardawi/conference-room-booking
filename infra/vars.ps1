# Load AWS IDs for this project. Usage:  . .\infra\vars.ps1
$region = "us-east-1"
$acct   = aws sts get-caller-identity --query Account --output text
$reg    = "$acct.dkr.ecr.$region.amazonaws.com"
$role   = "arn:aws:iam::${acct}:role/LabRole"
$vpc    = aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query "Vpcs[0].VpcId" --output text
$sub    = (aws ec2 describe-subnets --filters Name=vpc-id,Values=$vpc Name=availability-zone,Values=us-east-1a,us-east-1b `
            --query "Subnets[].SubnetId" --output text) -split "\s+"
$albSg  = aws ec2 describe-security-groups --filters Name=vpc-id,Values=$vpc Name=group-name,Values=crb-alb-sg `
            --query "SecurityGroups[0].GroupId" --output text
$svcSg  = aws ec2 describe-security-groups --filters Name=vpc-id,Values=$vpc Name=group-name,Values=crb-svc-sg `
            --query "SecurityGroups[0].GroupId" --output text
Write-Host "Account $acct | VPC $vpc | Subnets $($sub -join ',') | ALB SG $albSg | Service SG $svcSg"