import base64
import pulumi
import pulumi_aws as aws
import pulumi_docker as docker
import json

cluster = aws.ecs.Cluster("cluster")

vpc = aws.ec2.get_vpc(default=True)
vpc_subnets = aws.ec2.get_subnet_ids(vpc_id=vpc.id)

group = aws.ec2.SecurityGroup(
    "web-secgrp",
    vpc_id=vpc.id,
    description="HTTP access on port 8080",
    ingress=[
        {
            "protocol": "tcp",
            "from_port": 8080,
            "to_port": 8080,
            "cidr_blocks": ["0.0.0.0/0"],
        },
    ],
    egress=[
        {
            "protocol": "-1",
            "from_port": 0,
            "to_port": 0,
            "cidr_blocks": ["0.0.0.0/0"],
        }
    ],
)

alb = aws.lb.LoadBalancer(
    "app-lb",
    internal="false",
    security_groups=[group.id],
    subnets=vpc_subnets.ids,
    load_balancer_type="application",
)

atg = aws.lb.TargetGroup(
    "app-tg",
    port=8080,
    deregistration_delay=0,
    protocol="HTTP",
    target_type="ip",
    vpc_id=vpc.id,
)

wl = aws.lb.Listener(
    "web",
    load_balancer_arn=alb.arn,
    port=8080,
    default_actions=[{"type": "forward", "target_group_arn": atg.arn}],
)

role = aws.iam.Role(
    "task-exec-role",
    assume_role_policy=json.dumps(
        {
            "Version": "2008-10-17",
            "Statement": [
                {
                    "Sid": "",
                    "Effect": "Allow",
                    "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }
            ],
        }
    ),
)

rpa = aws.iam.RolePolicyAttachment(
    "task-exec-policy",
    role=role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy",
)

# Create a private ECR repository.
repo = aws.ecr.Repository('webapprepo')

def get_registry_info(rid):
    creds = aws.ecr.get_credentials(registry_id=rid)
    decoded = base64.b64decode(creds.authorization_token).decode()
    parts = decoded.split(':')
    if len(parts) != 2:
        raise Exception("Invalid credentials")
    return docker.ImageRegistry(creds.proxy_endpoint, parts[0], parts[1])

app_registry = repo.registry_id.apply(get_registry_info)

# Build and publish the container image.
image = docker.Image('webapp',
    build='app',
    image_name=repo.repository_url,
    registry=app_registry,
)

task_definition = aws.ecs.TaskDefinition(
    "webapp-task",
    family="fargate-task-definition",
    cpu="256",
    memory="512",
    network_mode="awsvpc",
    requires_compatibilities=["FARGATE"],
    execution_role_arn=role.arn,
    container_definitions=pulumi.Output.all(image.image_name).apply(lambda args: json.dumps(
        [
            {
                "name": "webapp",
                "image": args[0],
                "portMappings": [
                    {"containerPort": 8080, "hostPort": 8080, "protocol": "tcp"}
                ],
            }
        ]
    )),
)

service = aws.ecs.Service(
    "app-svc",
    cluster=cluster.arn,
    desired_count=2,
    launch_type="FARGATE",
    task_definition=task_definition.arn,
    network_configuration={
        "assign_public_ip": "true",
        "subnets": vpc_subnets.ids,
        "security_groups": [group.id],
    },
    load_balancers=[
        {"target_group_arn": atg.arn, "container_name": "webapp", "container_port": 8080}
    ],
    opts=pulumi.ResourceOptions(depends_on=[wl]),
    force_new_deployment=True,
)

pulumi.export("url", pulumi.Output.concat("You should now be able to browse to http://", alb.dns_name, ":8080 it may take a few minutes to start responding :)"))
