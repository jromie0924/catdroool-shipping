app_env := "prod"
region := "us-east-2"
stack := "catdroool-shipping-" + app_env
ecr_repo := "catdroool-shipping-" + app_env

# The Catdroool AWS account. Every aws call below passes this explicitly -- without it they fall
# through to the *default* profile, which is a personal account holding unrelated
# infrastructure, and the client's stack would quietly build there. `--profile` also beats
# AWS_ACCESS_KEY_ID in the environment, which a bare AWS_PROFILE would not.
profile := "catdroool"

# Optional guard. Set it to the Catdroool account id and every deploy asserts the profile
# really resolves there before touching anything:
#   just expected_account=123456789012 deploy-dev
# Left empty, deploys still print the account they are about to build in. Verify with `just whoami`.
expected_account := ""

# Override these to run without side effects. address_validation_enabled=false is the only
# thing standing between a test run and several hundred Smarty verifications off a capped
# monthly allotment. See `deploy-dev`.
emails_enabled := "true"
address_validation_enabled := "true"

# Must agree with the stack's CpuArchitecture parameter, or the task dies on start with
# "exec format error".
platform := "linux/arm64"

# Left empty, the deploy recipes discover the default VPC and the subnets in it that reach an
# Internet Gateway. Pin them to deploy somewhere else:
#   just vpc_id=vpc-0abc subnet_ids=subnet-0aaa,subnet-0bbb deploy-infra
vpc_id := ""
subnet_ids := ""

test:
  pipenv run pytest -v

install:
  pipenv sync

build:
  just --justfile {{justfile()}} install
  just --justfile {{justfile()}} test

# Show which AWS account these recipes act on. Run it before anything destructive.
whoami:
  @aws --profile {{profile}} sts get-caller-identity --output table

# Show the VPC and public subnets a deploy would use.
network:
  #!/usr/bin/env bash
  set -euo pipefail
  # Honors vpc_id/subnet_ids when set, otherwise discovers them. Prints "<vpc> <subnet,subnet>",
  # which deploy-infra reads back.
  vpc='{{vpc_id}}'
  subnets='{{subnet_ids}}'

  if [ -z "$vpc" ]; then
    vpc=$(aws --profile {{profile}} ec2 describe-vpcs --region {{region}} \
      --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)
    if [ "$vpc" = "None" ] || [ -z "$vpc" ]; then
      echo "No default VPC in {{region}}. Pass vpc_id=... and subnet_ids=..." >&2
      exit 1
    fi
  fi

  if [ -z "$subnets" ]; then
    # Only IGW-routed subnets work: the task carries a public IP and there is no NAT, so a
    # private subnet strands it -- it fails the image pull with CannotPullContainerError.
    # A subnet with no explicit route-table association inherits the VPC's main table, which
    # is how default-VPC subnets are wired, so the main table has to be resolved separately
    # rather than read off Associations[].
    default_route() {
      aws --profile {{profile}} ec2 describe-route-tables --region {{region}} --filters "$@" \
        --query 'RouteTables[0].Routes[?DestinationCidrBlock==`0.0.0.0/0`]|[0].GatewayId' \
        --output text
    }
    main_gw=$(default_route Name=vpc-id,Values="$vpc" Name=association.main,Values=true)

    public=()
    for s in $(aws --profile {{profile}} ec2 describe-subnets --region {{region}} \
                 --filters Name=vpc-id,Values="$vpc" \
                 --query 'Subnets[].SubnetId' --output text); do
      gw=$(default_route Name=association.subnet-id,Values="$s")
      if [ -z "$gw" ] || [ "$gw" = "None" ]; then gw="$main_gw"; fi
      case "$gw" in igw-*) public+=("$s") ;; esac
    done

    if [ ${#public[@]} -eq 0 ]; then
      echo "No IGW-routed subnets in $vpc. Pass subnet_ids=... explicitly." >&2
      exit 1
    fi
    subnets=$(IFS=,; echo "${public[*]}")
  fi

  echo "$vpc $subnets"

# Shared implementation behind deploy-dev and deploy-prod. Private, because its defaults are
# the prod ones: a bare `just deploy-infra` would deploy production with real emails and real
# Smarty lookups, which is not something anyone should be able to do by accident.
[private]
deploy-infra schedule_state="ENABLED":
  #!/usr/bin/env bash
  set -euo pipefail
  # Network comes from `just network`: the default VPC and its IGW-routed subnets, unless
  # vpc_id/subnet_ids pin them.
  # A nested `just` starts with the justfile's defaults, so every variable this depends on has
  # to be forwarded explicitly -- an omission here silently reverts to the default.
  read -r vpc subnet_list < <(just --justfile {{justfile()}} \
    profile='{{profile}}' vpc_id='{{vpc_id}}' subnet_ids='{{subnet_ids}}' network)

  account=$(aws --profile {{profile}} sts get-caller-identity --query Account --output text)
  if [ -n '{{expected_account}}' ] && [ "$account" != '{{expected_account}}' ]; then
    echo "Refusing to deploy: profile '{{profile}}' resolves to account ${account}," >&2
    echo "but expected_account is {{expected_account}}." >&2
    exit 1
  fi
  echo "Deploying {{stack}} to account ${account} (profile {{profile}}, {{region}})"
  echo "  network: ${vpc} [${subnet_list}]"

  # Parameters go in as JSON rather than the `Key=Value` shorthand. The shorthand splits on
  # commas to separate one parameter from the next, so a comma-delimited List<Subnet::Id>
  # cannot survive it -- and backslash-escaping the commas does not help, because the CLI
  # splits anyway and leaves the backslash in the value ("subnet-0a4a5272\ does not exist").
  params=$(mktemp)
  trap 'rm -f "$params"' EXIT
  {
    printf '[\n'
    printf ' {"ParameterKey":"AppEnv","ParameterValue":"%s"},\n'                   '{{app_env}}'
    printf ' {"ParameterKey":"VpcId","ParameterValue":"%s"},\n'                    "$vpc"
    printf ' {"ParameterKey":"SubnetIds","ParameterValue":"%s"},\n'                "$subnet_list"
    printf ' {"ParameterKey":"ScheduleState","ParameterValue":"%s"},\n'            '{{schedule_state}}'
    printf ' {"ParameterKey":"EmailsEnabled","ParameterValue":"%s"},\n'            '{{emails_enabled}}'
    printf ' {"ParameterKey":"AddressValidationEnabled","ParameterValue":"%s"}\n'  '{{address_validation_enabled}}'
    printf ']\n'
  } > "$params"

  aws --profile {{profile}} cloudformation deploy \
    --region {{region}} \
    --stack-name {{stack}} \
    --template-file infra/catdroool-shipping.yaml \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides "file://$params"

# Real task role, real egress rules, real Stripe and the dev DynamoDB table -- but no Smarty
# lookups and no emails. The finished report goes to the dev bucket instead. The schedule is
# left disabled; trigger a run with `just app_env=dev run-now`.
#
# Deploy a dev stack: real Stripe, no Smarty, no email, report lands in S3.
deploy-dev:
  just --justfile {{justfile()}} \
    app_env=dev \
    emails_enabled=false \
    address_validation_enabled=false \
    profile='{{profile}}' \
    expected_account='{{expected_account}}' \
    vpc_id='{{vpc_id}}' \
    subnet_ids='{{subnet_ids}}' \
    deploy-infra DISABLED

# Pass DISABLED on the very first deploy. The prod ECR repo is created by this stack, so it is
# empty until `just push`, and an enabled schedule pointed at an empty repo fails the task with
# CannotPullContainerError:
#
#   just deploy-prod DISABLED && just push && just deploy-prod
#
# Deploy the PRODUCTION stack: real emails, real Smarty lookups, schedule enabled.
deploy-prod schedule_state="ENABLED":
  just --justfile {{justfile()}} \
    app_env=prod \
    emails_enabled=true \
    address_validation_enabled=true \
    profile='{{profile}}' \
    expected_account='{{expected_account}}' \
    vpc_id='{{vpc_id}}' \
    subnet_ids='{{subnet_ids}}' \
    deploy-infra {{schedule_state}}

# Build the image and push it to the stack's ECR repository.
push:
  #!/usr/bin/env bash
  set -euo pipefail
  account=$(aws --profile {{profile}} sts get-caller-identity --query Account --output text)
  registry="${account}.dkr.ecr.{{region}}.amazonaws.com"
  aws --profile {{profile}} ecr get-login-password --region {{region}} \
    | docker login --username AWS --password-stdin "$registry"
  docker build --platform {{platform}} -t {{ecr_repo}}:latest .
  docker tag {{ecr_repo}}:latest "$registry/{{ecr_repo}}:latest"
  docker push "$registry/{{ecr_repo}}:latest"

# Run the report immediately, off-schedule. This emails the real recipients.
run-now:
  #!/usr/bin/env bash
  set -euo pipefail
  out() {
    aws --profile {{profile}} cloudformation describe-stacks --region {{region}} --stack-name {{stack}} \
      --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text
  }
  cluster=$(out ClusterName)
  taskdef=$(out TaskDefinitionArn)
  sg=$(out TaskSecurityGroupId)
  subnets=$(out TaskSubnetIds)
  aws --profile {{profile}} ecs run-task \
    --region {{region}} \
    --cluster "$cluster" \
    --task-definition "$taskdef" \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$subnets],securityGroups=[$sg],assignPublicIp=ENABLED}"

# Follow the task's stdout.
logs:
  aws --profile {{profile}} logs tail /ecs/catdroool-shipping-{{app_env}} --region {{region}} --follow

# List archived reports. `just app_env=dev reports` for the dev stack's bucket.
reports:
  #!/usr/bin/env bash
  set -euo pipefail
  bucket=$(aws --profile {{profile}} cloudformation describe-stacks --region {{region}} --stack-name {{stack}} \
    --query "Stacks[0].Outputs[?OutputKey=='ReportBucketName'].OutputValue" --output text)
  aws --profile {{profile}} s3 ls "s3://$bucket/" --recursive --human-readable

# Download one date's reports into ./output/<date>/.
fetch-reports date:
  #!/usr/bin/env bash
  set -euo pipefail
  bucket=$(aws --profile {{profile}} cloudformation describe-stacks --region {{region}} --stack-name {{stack}} \
    --query "Stacks[0].Outputs[?OutputKey=='ReportBucketName'].OutputValue" --output text)
  aws --profile {{profile}} s3 sync "s3://$bucket/{{date}}/" "output/{{date}}/"
  echo "Downloaded to output/{{date}}/"
