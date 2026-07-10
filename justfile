app_env := "prod"
region := "us-east-2"
stack := "catdroool-shipping-" + app_env
ecr_repo := "catdroool-shipping-" + app_env

# Override these to run without side effects. address_validation_enabled=false is the only
# thing standing between a test run and several hundred Smarty verifications off a capped
# monthly allotment. See `deploy-dev`.
emails_enabled := "true"
address_validation_enabled := "true"

# Must agree with the stack's CpuArchitecture parameter, or the task dies on start with
# "exec format error".
platform := "linux/arm64"

test:
  pipenv run pytest -v

install:
  pipenv sync

build:
  just --justfile {{justfile()}} install
  just --justfile {{justfile()}} test

# Create or update the CloudFormation stack.
# Pass DISABLED on the very first deploy, before any image exists in ECR.
#   just deploy-infra vpc-0abc subnet-0aaa,subnet-0bbb DISABLED
deploy-infra vpc_id subnet_ids schedule_state="ENABLED":
  #!/usr/bin/env bash
  set -euo pipefail
  # `cloudformation deploy` parses parameter overrides with its own shorthand syntax, where
  # an unescaped comma separates one parameter from the next rather than one subnet from
  # the next. The list type needs its commas escaped to survive.
  subnets=$(printf '%s' '{{subnet_ids}}' | sed 's/,/\\,/g')
  aws cloudformation deploy \
    --region {{region}} \
    --stack-name {{stack}} \
    --template-file infra/catdroool-shipping.yaml \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides \
      AppEnv={{app_env}} \
      VpcId={{vpc_id}} \
      SubnetIds="$subnets" \
      ScheduleState={{schedule_state}} \
      EmailsEnabled={{emails_enabled}} \
      AddressValidationEnabled={{address_validation_enabled}}

# Real task role, real egress rules, real Stripe and the dev DynamoDB table -- but no Smarty
# lookups and no emails. The finished report goes to the dev bucket instead. The schedule is
# left disabled; trigger a run with `just app_env=dev run-now`.
#
# Deploy a dev stack: real Stripe, no Smarty, no email, report lands in S3.
deploy-dev vpc_id subnet_ids:
  just --justfile {{justfile()}} \
    app_env=dev \
    emails_enabled=false \
    address_validation_enabled=false \
    deploy-infra {{vpc_id}} {{subnet_ids}} DISABLED

# Build the image and push it to the stack's ECR repository.
push:
  #!/usr/bin/env bash
  set -euo pipefail
  account=$(aws sts get-caller-identity --query Account --output text)
  registry="${account}.dkr.ecr.{{region}}.amazonaws.com"
  aws ecr get-login-password --region {{region}} \
    | docker login --username AWS --password-stdin "$registry"
  docker build --platform {{platform}} -t {{ecr_repo}}:latest .
  docker tag {{ecr_repo}}:latest "$registry/{{ecr_repo}}:latest"
  docker push "$registry/{{ecr_repo}}:latest"

# Run the report immediately, off-schedule. This emails the real recipients.
run-now:
  #!/usr/bin/env bash
  set -euo pipefail
  out() {
    aws cloudformation describe-stacks --region {{region}} --stack-name {{stack}} \
      --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text
  }
  cluster=$(out ClusterName)
  taskdef=$(out TaskDefinitionArn)
  sg=$(out TaskSecurityGroupId)
  subnets=$(out TaskSubnetIds)
  aws ecs run-task \
    --region {{region}} \
    --cluster "$cluster" \
    --task-definition "$taskdef" \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$subnets],securityGroups=[$sg],assignPublicIp=ENABLED}"

# Follow the task's stdout.
logs:
  aws logs tail /ecs/catdroool-shipping-{{app_env}} --region {{region}} --follow

# List archived reports. `just app_env=dev reports` for the dev stack's bucket.
reports:
  #!/usr/bin/env bash
  set -euo pipefail
  bucket=$(aws cloudformation describe-stacks --region {{region}} --stack-name {{stack}} \
    --query "Stacks[0].Outputs[?OutputKey=='ReportBucketName'].OutputValue" --output text)
  aws s3 ls "s3://$bucket/" --recursive --human-readable

# Download one date's reports into ./output/<date>/.
fetch-reports date:
  #!/usr/bin/env bash
  set -euo pipefail
  bucket=$(aws cloudformation describe-stacks --region {{region}} --stack-name {{stack}} \
    --query "Stacks[0].Outputs[?OutputKey=='ReportBucketName'].OutputValue" --output text)
  aws s3 sync "s3://$bucket/{{date}}/" "output/{{date}}/"
  echo "Downloaded to output/{{date}}/"
