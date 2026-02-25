# LAB04 — Infrastructure as Code (Terraform & Pulumi)

> Course: DevOps Core Course — Lab 4  
> Topic: Infrastructure as Code (Terraform + Pulumi)  
> Cloud provider: **Yandex Cloud**  
> Date: 2026-02-19

---

## 1. Cloud Provider & Infrastructure

### Cloud provider chosen and rationale
I used **Yandex Cloud** because it is accessible from Russia and provides a free-tier friendly VM configuration that matches the lab requirements (small VM + simple networking and firewall rules).

### Region / Zone
- Zone: `ru-central1-a`

### Instance size (free-tier friendly)
- Platform: `standard-v2`
- vCPU: `2` with `core_fraction = 20`
- RAM: `1 GB`
- Boot disk: `10 GB` (`network-hdd`)

### Estimated cost
- Expected cost: **$0** (free-tier / minimal resources)

### Resources created
Using IaC, the following resources are provisioned:
- VPC network
- Subnet
- Security group with rules:
  - SSH 22 — only from my IP (`95.111.204.70/32`)
  - HTTP 80 — open to `0.0.0.0/0`
  - App port 5000 — open to `0.0.0.0/0`
- Compute instance (VM) with NAT public IP

---

## 2. Terraform Implementation

### Terraform version
```text
<PASTE: terraform version>
```

### Project structure
```
terraform/
├── main.tf
├── variables.tf
├── outputs.tf
├── versions.tf
├── terraform.tfvars   (gitignored)
└── .gitignore
```

### Authentication (Yandex Cloud)
Authentication is done via **Service Account authorized key (JSON)**.

- Service account key file (local path, not committed):
  - `C:/Users/11kvv/.yc/lab04-sa-key.json`

> Important: credential files (`*.json`) and state are excluded from Git.

### Key configuration decisions
- **SSH access restricted** to my public IP only: `95.111.204.70/32`
- Public ports required by lab (80 and 5000) are open to the internet.
- Outputs exported:
  - VM public IP
  - SSH command string

### Challenges encountered & fixes
1) **Provider authentication missing**
- Error: `one of 'token' or 'service_account_key_file' should be specified`
- Fix: generated service account key and configured `service_account_key_file`.

2) **PermissionDenied when creating security group ingress**
- Error: `Permission denied to add ingress rule to security group`
- Fix: updated IAM roles for the service account (VPC permissions) and re-ran `terraform apply`.

### Terminal output (sanitized)

#### `terraform init`
```text
Initializing the backend...
Initializing provider plugins...
- Using previously-installed yandex-cloud/yandex v0.187.0

Terraform has been successfully initialized!
```

#### `terraform plan` (excerpt)
```text
Plan: 2 to add, 0 to change, 0 to destroy.

Changes to Outputs:
  + public_ip   = (known after apply)
  + ssh_command = (known after apply)
```

> Note: I also saw a warning: “Cannot connect to YC tool initialization service...”. This warning did not block plan generation.

#### `terraform apply` (result)
```text
<PASTE: the final terraform apply output AFTER permissions fix>
```

### Outputs
```text
Public IP: <PASTE_PUBLIC_IP>
SSH command (from output):
<PASTE: terraform output ssh_command>
```

### SSH proof
```text
<PASTE: ssh session proof, e.g. `uname -a` / `whoami`>
```

Example command (Windows):
```powershell
ssh -i C:\Users\11kvv\.ssh\lab04_ed25519 ubuntu@<PUBLIC_IP>
```

---

## 3. Pulumi Implementation

### Pulumi version and language
- Language: **Python**
```text
<PASTE: pulumi version>
```

### Cleanup of Terraform resources
Before provisioning the same infrastructure with Pulumi, Terraform resources were destroyed:

```text
<PASTE: terraform destroy output>
```

### Pulumi project structure
```
pulumi/
├── __main__.py
├── requirements.txt
├── Pulumi.yaml
└── Pulumi.<stack>.yaml (gitignored if contains secrets)
```

### Planned changes (`pulumi preview`)
```text
<PASTE: pulumi preview output>
```

### Apply (`pulumi up`)
```text
<PASTE: pulumi up output>
```

### Outputs and SSH proof
```text
Pulumi public IP: <PASTE_PUBLIC_IP>
SSH proof:
<PASTE: ssh session proof>
```

---

## 4. Terraform vs Pulumi Comparison

### Ease of Learning
Terraform was easier to start with because HCL is concise and the workflow is very straightforward (`init → plan → apply`). Pulumi required a bit more setup (runtime, deps) and code structure, but felt natural once configured.

### Code Readability
Terraform is very readable for simple infra because it is declarative and compact. Pulumi is more verbose but benefits from real language features (variables, functions, reuse) which can help as the project grows.

### Debugging
Terraform errors are often direct and tied to a specific resource block. In Pulumi, errors can appear deeper in the program flow, but the ability to print/debug in code can help.

### Documentation
Terraform has a large ecosystem and many examples. Pulumi documentation is also strong, especially when you already know the language SDK, but examples for some providers may be fewer.

### Use Case
- Terraform: best for standard, repeatable infra with a simple declarative model, especially in teams.
- Pulumi: best when infrastructure needs non-trivial logic/reuse and you want to leverage full programming languages and testing.

---

## 5. Lab 5 Preparation & Cleanup

### VM for Lab 5
- Keeping a VM for Lab 5 (Ansible): **<YES/NO>**
- If YES: Which one: **Terraform / Pulumi**
- Reason:
  - <short explanation>

### Cleanup status
- Terraform resources destroyed: **<YES/NO>**
- Pulumi resources destroyed: **<YES/NO>**
- Proof (outputs/log excerpts):
```text
<PASTE: destroy outputs OR mention cloud console status>
```

---

## Appendix — Security & Git hygiene

- `terraform.tfstate` and `terraform.tfvars` are not committed.
- Service account key `*.json` is not committed.
- SSH private key is not committed.
- `.gitignore` contains patterns for state and secrets.
