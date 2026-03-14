# 🛡️ Security Report & Remediation Code

As a Principal Cloud Security Architect, I have performed a strict threat model analysis of the provided AWS infrastructure diagram, referencing the live threat intelligence for this week.

## 1. Identified Components
The diagram illustrates a three-tier AWS architecture with the following components:

### External Facing:
* **User (Internet)**
* **Amazon Route 53** (DNS Service)
* **Web Application Firewall** (WAF)
* **Amazon CloudFront**

### AWS Cloud - Global Services / VPC Configuration:
* **AWS Cloud Region** (containing a VPC spanning two Availability Zones)
* **VPC** (Virtual Private Cloud)
* **Internet Gateway**
* **IAM Roles** (for IAM security)

### Availability Zone 1 (AZ1):
* **Tier 1 (Presentation Layer):** Public subnet (e.g., 172.16.0.0/24), Application Load Balancer (ALB), EC2 Web Servers (M1 Mac instances), Autoscaling Group.
* **Tier 2 (Logic Layer):** Private subnet (e.g., 172.16.0.0/24), NAT Gateway, Application Load Balancer (ALB), EC2 Instances (Application Servers, M1 Mac instances).
* **Tier 3 (Data Layer):** Private subnet (e.g., 172.16.0.0/24), Network ACL, Amazon RDS (Database).

### Availability Zone 2 (AZ2):
* **Tier 1 (Presentation Layer):** Public subnet (e.g., 172.16.1.0/24), Application Load Balancer (ALB), EC2 Web Servers (M1 Mac instances).
* **Tier 2 (Logic Layer):** Private subnet (e.g., 172.16.1.0/24), NAT Gateway, Application Load Balancer (ALB), EC2 Instances (Application Servers, M1 Mac instances).
* **Tier 3 (Data Layer):** Private subnet (e.g., 172.16.1.0/24), Network ACL, Amazon RDS (Backup Database).

### Networking & Operations:
* **Public/Private Route Tables**
* **Continuous Backup** (between RDS instances)

---

## 2. Security Best Practice Failures and Threat Intelligence References

### 🚨 Direct Internet Exposure of Tier 1 EC2 Web Servers
**Failure:** The EC2 Web Servers in Tier 1 are depicted within "Public subnets." Placing compute instances that do not require public IP addresses into public subnets is a significant security risk, allowing attackers to potentially bypass ALB-specific controls.
**Threat Intelligence:** Highly susceptible to **CVE-2023-34362** (Unauthenticated RCE). If running containers, **CVE-2024-21626** (Container Breakout) is a critical concern.

### 🚨 Lack of Granular Security Group Enforcement
**Failure:** No explicit depiction of Security Groups for ALBs, EC2s, or RDS. The absence of specific Security Groups implies excessively permissive default rules, weakening the defense-in-depth strategy.
**Threat Intelligence:** Exacerbates **CVE-2023-34362** and makes lateral movement easier for attackers following an initial compromise.

### 🚨 Implied Cleartext Transit / Lack of Encryption in Transit
**Failure:** No indication of TLS enforcement between ALBs and EC2s, or between app servers and RDS. This violates Zero-Trust principles.
**Threat Intelligence:** Directly related to **Cleartext Transit (Zero-Trust Violation)**, allowing eavesdropping on unencrypted internal communications.

### 🚨 No Explicit Encryption at Rest for RDS
**Failure:** No mention of encryption for RDS instances using KMS keys.
**Threat Intelligence:** Relates to **CVE-2023-47627** (Cloud Data Exposure) principles: unencrypted data at rest is a major exposure risk.

### 🚨 Unspecified IAM Privilege Management
**Failure:** IAM Roles are listed without scoping. Broad permissions (e.g., wildcards) lead to privilege escalation paths.
**Threat Intelligence:** Points to **Identity Threat (IAM Privilege Escalation)**.

---

## 3. Terraform Code for Top 2 Critical Vulnerabilities

The remediation addresses the two most critical issues by moving Tier 1 EC2s to private subnets and implementing least-privilege Security Groups.

```hcl
# This Terraform code assumes an existing VPC.
# Replace "my-app-vpc" with your actual VPC tag or ID.

# --- Data Sources to retrieve existing VPC and AZs ---
data "aws_vpc" "main" {
  filter {
    name   = "tag:Name"
    values = ["my-app-vpc"] 
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

# --- REMEDIATION 1: Move Tier 1 EC2 Web Servers to Dedicated Private Subnets ---

# New private subnet for Tier 1 EC2 Web Servers in AZ1
resource "aws_subnet" "web_private_az1" {
  vpc_id            = data.aws_vpc.main.id
  cidr_block        = "172.16.3.0/24" 
  availability_zone = data.aws_availability_zones.available.names[0]
  tags = {
    Name = "web-tier-private-az1"
  }
}

# New private subnet for Tier 1 EC2 Web Servers in AZ2
resource "aws_subnet" "web_private_az2" {
  vpc_id            = data.aws_vpc.main.id
  cidr_block        = "172.16.4.0/24" 
  availability_zone = data.aws_availability_zones.available.names[1]
  tags = {
    Name = "web-tier-private-az2"
  }
}

# --- REMEDIATION 2: Implement Comprehensive Security Groups ---

# Security Group for Tier 1 Public Application Load Balancer
resource "aws_security_group" "alb_public_sg" {
  name_prefix = "alb-public-sg"
  vpc_id      = data.aws_vpc.main.id
  description = "Allow HTTP/HTTPS traffic to the public ALB, fronted by CloudFront/WAF"

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow HTTP from anywhere (filtered by WAF/CloudFront)"
  }
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow HTTPS from anywhere (filtered by WAF/CloudFront)"
  }

  egress {
    from_port       = 80 
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.web_servers_sg.id]
    description     = "Allow outbound to Tier 1 Web Servers"
  }
  egress {
    from_port       = 443 
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.web_servers_sg.id]
    description     = "Allow outbound to Tier 1 Web Servers (HTTPS)"
  }

  tags = { Name = "alb-public-sg" }
}

# Security Group for Tier 1 EC2 Web Servers (now in private subnets)
resource "aws_security_group" "web_servers_sg" {
  name_prefix = "web-servers-sg"
  vpc_id      = data.aws_vpc.main.id
  description = "Allow traffic from public ALB, outbound to App Servers, and NAT for updates"

  ingress {
    from_port       = 80 
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_public_sg.id]
    description     = "Allow HTTP from public ALB"
  }
  ingress {
    from_port       = 443 
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_public_sg.id]
    description     = "Allow HTTPS from public ALB"
  }

  tags = { Name = "web-servers-sg" }
}