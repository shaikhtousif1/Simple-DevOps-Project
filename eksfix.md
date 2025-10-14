
---


# 🏗️ AWS EKS Private Cluster — VPC Endpoints Module

This module enables **private communication** between **EKS worker nodes** (in private subnets) and AWS-managed services such as **EKS**, **ECR**, **EC2**, and **S3** — **without using a NAT Gateway or Internet Gateway**.

It’s designed for **brownfield VPCs** (existing organizational networks) where you already have a VPC and subnets created but need to deploy an EKS cluster privately and securely.

---

## 📚 Why VPC Endpoints Are Needed

When EKS worker nodes are launched in private subnets (no Internet access), they **still need to reach AWS services** to:
- Download bootstrap files and CNI plugins from **S3**
- Pull container images from **ECR**
- Communicate with the **EKS control plane**
- Interact with **EC2 APIs** for tagging and metadata updates

Without NAT or these endpoints, nodes fail to join the cluster with:
```

NodeCreationFailure: Instances failed to join the Kubernetes cluster.

```

This module fixes that.

---

## 🧩 Endpoints Created by This Module

| Service | Type | Purpose | Private DNS | Cost |
|----------|------|----------|-------------|------|
| **EKS** | Interface | Control plane communication | ✅ | 💰 Yes |
| **ECR API** | Interface | Image metadata access | ✅ | 💰 Yes |
| **ECR DKR** | Interface | Docker image layer pulls | ✅ | 💰 Yes |
| **EC2** | Interface | Instance tagging, IMDS communication | ✅ | 💰 Yes |
| **S3** | Gateway | Bootstrap files, ECR layer downloads | N/A | 🆓 No cost |

> **Note:** If an S3 endpoint already exists in the VPC, this module automatically reuses it instead of creating a duplicate.

---

## 🧱 Folder Structure
```

modules/
└── vpc_endpoints/
├── main.tf
├── variables.tf
└── outputs.tf

````

---

## 🔧 main.tf

```hcl
locals {
  interface_endpoints = [
    "com.amazonaws.${var.aws_region}.ec2",
    "com.amazonaws.${var.aws_region}.ecr.api",
    "com.amazonaws.${var.aws_region}.ecr.dkr",
    "com.amazonaws.${var.aws_region}.eks"
  ]
}

# Security group for Interface Endpoints
resource "aws_security_group" "vpc_endpoints_sg" {
  name        = "${var.prefix}-vpc-endpoints-sg"
  description = "Security group for VPC interface endpoints"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidrs
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.prefix}-vpc-endpoints-sg"
  }
}

# ---------------------------------------
# Interface Endpoints: EKS, ECR, EC2
# ---------------------------------------
resource "aws_vpc_endpoint" "interface_endpoints" {
  for_each = toset(local.interface_endpoints)

  vpc_id              = var.vpc_id
  service_name        = each.value
  vpc_endpoint_type   = "Interface"
  subnet_ids          = var.private_subnet_ids
  security_group_ids  = [aws_security_group.vpc_endpoints_sg.id]
  private_dns_enabled = true

  tags = {
    Name = "${var.prefix}-${replace(each.value, "com.amazonaws.${var.aws_region}.", "")}-vpce"
  }
}

# ---------------------------------------
# Gateway Endpoint: S3 (Recreate / Reuse)
# ---------------------------------------

data "aws_vpc_endpoint_service" "s3" {
  service = "s3"
}

data "aws_vpc" "selected" {
  id = var.vpc_id
}

data "aws_route_tables" "private" {
  vpc_id = var.vpc_id
}

# Check if S3 endpoint already exists
data "aws_vpc_endpoint" "existing_s3" {
  for_each = toset([var.vpc_id])
  vpc_id   = each.key
  filter {
    name   = "service-name"
    values = ["com.amazonaws.${var.aws_region}.s3"]
  }
}

resource "aws_vpc_endpoint" "s3_gateway" {
  count             = length(data.aws_vpc_endpoint.existing_s3) == 0 ? 1 : 0
  vpc_id            = var.vpc_id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = data.aws_route_tables.private.ids

  tags = {
    Name = "${var.prefix}-s3-vpce"
  }
}
````

---

## ⚙️ variables.tf

```hcl
variable "vpc_id" {
  description = "VPC ID where endpoints will be created"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs to attach interface endpoints"
  type        = list(string)
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "prefix" {
  description = "Prefix for naming resources"
  type        = string
}

variable "allowed_cidrs" {
  description = "CIDR blocks allowed to access VPC endpoints (for ingress on SG)"
  type        = list(string)
  default     = ["10.0.0.0/8"]
}
```

---

## 📤 outputs.tf

```hcl
output "interface_endpoint_ids" {
  description = "Interface endpoint IDs"
  value       = [for ep in aws_vpc_endpoint.interface_endpoints : ep.id]
}

output "s3_gateway_endpoint_id" {
  description = "S3 gateway endpoint ID (created or reused)"
  value       = length(aws_vpc_endpoint.s3_gateway) > 0 ? aws_vpc_endpoint.s3_gateway[0].id : "Existing S3 endpoint reused"
}
```

---

## 🧩 Integration Example

In your main Terraform stack:

```hcl
module "vpc_endpoints" {
  source = "./modules/vpc_endpoints"

  vpc_id             = var.vpc_id
  private_subnet_ids = var.eks_cluster_subnet_ids
  aws_region         = var.aws_region
  prefix             = var.prefix
  allowed_cidrs      = ["10.0.0.0/8"]
}

module "eks" {
  source       = "./modules/eks"
  prefix       = var.prefix
  vpc_id       = var.vpc_id
  subnet_ids   = var.eks_cluster_subnet_ids
  aws_region   = var.aws_region
  depends_on   = [module.vpc_endpoints]
}
```

---

## ✅ Verification Commands

After `terraform apply`, verify your endpoints:

```bash
aws ec2 describe-vpc-endpoints --filters "Name=vpc-id,Values=<your-vpc-id>"
```

You should see:

* `Interface` endpoints for EKS, EC2, ECR API, ECR DKR
* `Gateway` endpoint for S3 (either reused or newly created)

Then check:

```bash
nslookup api.<your-cluster>.eks.<region>.amazonaws.com
```

Output should show **private IP addresses** (e.g., `10.x.x.x`) — meaning communication stays internal.

---

## 🧠 Operational Notes

* You can **disable EKS public access** once nodes join:

  ```bash
  aws eks update-cluster-config \
    --name <cluster-name> \
    --resources-vpc-config endpointPrivateAccess=true,endpointPublicAccess=false
  ```

* **Cost impact:** Each Interface Endpoint costs roughly **$0.01/hour** + **$0.01/GB**, while S3 Gateway is free.

* **Security benefit:** No outbound internet access required from worker nodes.

---

## 🏁 Summary

✅ No NAT Gateway needed
✅ Fully private EKS cluster
✅ Secure internal traffic via AWS backbone
✅ Reusable, modular, and organization-friendly Terraform code

---

**Authored by:** Tousif & Team 🧠
**Purpose:** Secure private EKS cluster deployments inside existing organizational VPCs
**Version:** 1.0

```

---
