# Copy current AWS lab credentials into GitHub repo secrets (run each lab session).
foreach ($k in "aws_access_key_id", "aws_secret_access_key", "aws_session_token") {
  aws configure get $k | gh secret set $k.ToUpper()
}
gh secret list