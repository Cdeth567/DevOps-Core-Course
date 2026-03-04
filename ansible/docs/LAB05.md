# Lab 05 — Ansible Fundamentals

## 1. Architecture Overview

**Ansible version:** ansible [core 2.16.3]

**Target VM OS:** Ubuntu 22.04.5 LTS (ubuntu/jammy64 via Vagrant + VirtualBox)

**Control node:** WSL2 (Ubuntu) on Windows

### Role Structure

```
ansible/
├── inventory/
│   └── hosts.ini              # Static inventory — VM IP + SSH key
├── roles/
│   ├── common/                # System packages & timezone
│   │   ├── tasks/main.yml
│   │   └── defaults/main.yml
│   ├── docker/                # Docker CE installation
│   │   ├── tasks/main.yml
│   │   ├── handlers/main.yml
│   │   └── defaults/main.yml
│   └── app_deploy/            # Pull & run containerized app
│       ├── tasks/main.yml
│       ├── handlers/main.yml
│       └── defaults/main.yml
├── playbooks/
│   ├── site.yml               # Imports both playbooks
│   ├── provision.yml          # common + docker roles
│   └── deploy.yml             # app_deploy role
├── group_vars/
│   └── all.yml               # Ansible Vault encrypted secrets
├── ansible.cfg
└── docs/LAB05.md
```

### Connectivity Test

```
$ ansible all -m ping

devops-vm | SUCCESS => {
    "changed": false,
    "ping": "pong"
}
```

---

### Why Roles Instead of Monolithic Playbooks?

Roles split responsibilities cleanly: `common` handles system setup, `docker` handles Docker installation, `app_deploy` handles the application. Each role can be reused across multiple projects, tested independently, and understood in isolation. A monolithic playbook with 50+ tasks becomes impossible to maintain — roles keep complexity manageable.

---

## 2. Roles Documentation

### Role: `common`

**Purpose:** Prepares every server with baseline tools. Updates the apt cache and installs utilities like git, curl, vim, htop, python3-pip.

**Variables (`defaults/main.yml`):**
| Variable | Default | Description |
|---|---|---|
| `common_packages` | list of packages | Packages to install via apt |
| `common_timezone` | `UTC` | System timezone |

**Handlers:** None

**Dependencies:** None

---

### Role: `docker`

**Purpose:** Installs Docker CE from the official Docker repository using the modern GPG key method (`/etc/apt/keyrings/docker.gpg`), ensures the service is running and enabled at boot, adds the target user to the `docker` group.

**Variables (`defaults/main.yml`):**
| Variable | Default | Description |
|---|---|---|
| `docker_packages` | docker-ce, cli, containerd, plugins | Packages to install |
| `docker_user` | `vagrant` | User to add to docker group |

**Handlers:**
- `restart docker` — triggered when Docker packages are installed for the first time

**Dependencies:** `common` role (needs ca-certificates, gnupg pre-installed)

---

### Role: `app_deploy`

**Purpose:** Authenticates with Docker Hub using vaulted credentials, pulls the latest image of the Python app (`cdeth567/devops-info-service`), removes any old container, starts a fresh container with port mapping 5000:5000, and verifies the `/health` endpoint responds HTTP 200.

**Variables (`group_vars/all.yml` — Vault encrypted):**
| Variable | Description |
|---|---|
| `dockerhub_username` | Docker Hub username (`cdeth567`) |
| `dockerhub_password` | Docker Hub access token |
| `app_name` | `devops-info-service` |
| `docker_image` | `cdeth567/devops-info-service` |
| `docker_image_tag` | `latest` |
| `app_port` | `5000` |
| `app_container_name` | `devops-info-service` |

**Variables (`defaults/main.yml`):**
| Variable | Default | Description |
|---|---|---|
| `app_port` | `5000` | Port to expose |
| `app_restart_policy` | `unless-stopped` | Docker restart policy |
| `app_env_vars` | `{}` | Extra env vars for container |

**Handlers:**
- `restart app container` — restarts the container when triggered by config change

**Dependencies:** `docker` role must run first

---

## 3. Idempotency Demonstration

### First Run (`ansible-playbook playbooks/provision.yml`)

```
PLAY [Provision web servers] ****************************************************

TASK [Gathering Facts] **********************************************************
ok: [devops-vm]

TASK [common : Update apt cache] ************************************************
changed: [devops-vm]

TASK [common : Install common packages] *****************************************
changed: [devops-vm]

TASK [common : Set timezone (optional)] *****************************************
changed: [devops-vm]

TASK [docker : Install prerequisites for Docker repo] ***************************
ok: [devops-vm]

TASK [docker : Ensure /etc/apt/keyrings exists] *********************************
ok: [devops-vm]

TASK [docker : Download and dearmor Docker GPG key] *****************************
ok: [devops-vm]

TASK [docker : Add Docker apt repository] ***************************************
changed: [devops-vm]

TASK [docker : Install Docker packages] *****************************************
changed: [devops-vm]

TASK [docker : Ensure Docker service is started and enabled] ********************
ok: [devops-vm]

TASK [docker : Add user to docker group] ****************************************
changed: [devops-vm]

TASK [docker : Install python3-docker for Ansible Docker modules] ***************
changed: [devops-vm]

PLAY RECAP **********************************************************************
devops-vm : ok=10   changed=6   unreachable=0   failed=0
```

### Second Run (`ansible-playbook playbooks/provision.yml`)

```
PLAY [Provision web servers] ****************************************************

TASK [Gathering Facts] **********************************************************
ok: [devops-vm]

TASK [common : Update apt cache] ************************************************
ok: [devops-vm]

TASK [common : Install common packages] *****************************************
ok: [devops-vm]

TASK [common : Set timezone (optional)] *****************************************
ok: [devops-vm]

TASK [docker : Install prerequisites for Docker repo] ***************************
ok: [devops-vm]

TASK [docker : Ensure /etc/apt/keyrings exists] *********************************
ok: [devops-vm]

TASK [docker : Download and dearmor Docker GPG key] *****************************
ok: [devops-vm]

TASK [docker : Add Docker apt repository] ***************************************
ok: [devops-vm]

TASK [docker : Install Docker packages] *****************************************
ok: [devops-vm]

TASK [docker : Ensure Docker service is started and enabled] ********************
ok: [devops-vm]

TASK [docker : Add user to docker group] ****************************************
ok: [devops-vm]

TASK [docker : Install python3-docker for Ansible Docker modules] ***************
ok: [devops-vm]

PLAY RECAP **********************************************************************
devops-vm : ok=12   changed=0   unreachable=0   failed=0
```

### Analysis

**First run — why tasks showed `changed`:**
- `Update apt cache` — package lists were stale, had to refresh
- `Install common packages` — git, curl, vim etc. weren't installed yet
- `Set timezone` — timezone wasn't configured
- `Download and dearmor Docker GPG key` — key wasn't in `/etc/apt/keyrings/` yet
- `Add Docker apt repository` — Docker repo wasn't in sources
- `Install Docker packages` — Docker CE wasn't installed
- `Add user to docker group` — vagrant user wasn't in docker group
- `Install python3-docker` — Python Docker SDK wasn't installed

**Second run — zero `changed`, all `ok`:**
Every Ansible module checks current state before acting. `apt: state=present` checks if package already exists. `file: state=directory` checks if directory exists. `apt_repository` checks if repo is already listed. Since everything was already in desired state, no changes were made. This is idempotency.

**What makes these roles idempotent:**
- `apt: state=present` — only installs if not already present
- `file: state=directory` — only creates if missing
- `args: creates: /etc/apt/keyrings/docker.gpg` — shell task only runs if file doesn't exist
- `service: state=started` — only starts if not running
- `user: groups=docker append=yes` — only adds group if not already member

---

## 4. Ansible Vault Usage

### How Credentials Are Stored

Sensitive values (Docker Hub username and access token) are stored in `group_vars/all.yml`, encrypted with Ansible Vault AES256. The file in the repository looks like:

```
$ANSIBLE_VAULT;1.1;AES256
65633261653764613262313261356561613666306634343139313537336332386233336231343839
3737366161363662643132656239373562613734356364660a646666633665353562643636393261
...
```

Nobody can read the credentials without the vault password.

### Vault Commands Used

```bash
# Create encrypted file
ansible-vault create group_vars/all.yml

# View contents (to verify)
ansible-vault view group_vars/all.yml --ask-vault-pass

# Edit contents
ansible-vault edit group_vars/all.yml
```

### Vault Password Management

A `.vault_pass` file stores the password locally:
```bash
echo "your-password" > .vault_pass
chmod 600 .vault_pass
```

`ansible.cfg` references it:
```ini
[defaults]
vault_password_file = .vault_pass
```

`.vault_pass` is added to `.gitignore` — never committed.

### Proof File Is Encrypted

```
$ cat group_vars/all.yml
$ANSIBLE_VAULT;1.1;AES256
65633261653764613262313261356561613666306634343139313537336332386233336231343839
3737366161363662643132656239373562613734356364660a646666633665353562643636393261
61346366636665303935353636656633663539616561373266333139356432623534636264326636
6338313961386638380a656665313965346133373436656339613837356563363965313735316339
...
```

### Why Ansible Vault Is Necessary

Without Vault, Docker Hub credentials would be in plain text in the repository. Anyone with read access (teammates, CI/CD systems, public GitHub) could see the token. Vault encrypts with AES-256 — the file is safe to commit while keeping actual values private.

---

## 5. Deployment Verification

### Deployment Run (`ansible-playbook playbooks/deploy.yml`)

```
PLAY [Deploy application] *******************************************************

TASK [Gathering Facts] **********************************************************
ok: [devops-vm]

TASK [app_deploy : Log in to Docker Hub] ****************************************
ok: [devops-vm]

TASK [app_deploy : Pull Docker image] *******************************************
ok: [devops-vm]

TASK [app_deploy : Remove old container if exists] ******************************
changed: [devops-vm]

TASK [app_deploy : Run new container] *******************************************
changed: [devops-vm]

TASK [app_deploy : Wait for application port] ***********************************
ok: [devops-vm]

TASK [app_deploy : Verify health endpoint] **************************************
ok: [devops-vm]

PLAY RECAP **********************************************************************
devops-vm : ok=7    changed=2    unreachable=0    failed=0
```

### Container Status (`docker ps`)

```
$ ansible webservers -a "docker ps"

devops-vm | CHANGED | rc=0 >>
CONTAINER ID   IMAGE                                 COMMAND           CREATED         STATUS         PORTS                    NAMES
89b8f4104cfb   cdeth567/devops-info-service:latest   "python app.py"   1 minute ago    Up 1 minute    0.0.0.0:5000->5000/tcp   devops-info-service
```

### Health Check Verification

```
$ ansible webservers -a "curl -s http://localhost:5000/health"

devops-vm | CHANGED | rc=0 >>
{"status":"healthy","timestamp":"2026-02-25T18:31:56.187Z","uptime_seconds":32}
```

### Handler Execution

The `restart app container` handler is defined in `app_deploy/handlers/main.yml` and triggers only when container configuration changes. During normal re-deployment, the remove+start tasks handle container lifecycle directly.

---

## 6. Key Decisions

**Why use roles instead of plain playbooks?**
Roles enforce a standard structure and make code reusable. The `docker` role can be dropped into any future project without modification. A monolithic playbook with all tasks in one file becomes unmaintainable past 50 tasks — roles keep each concern isolated and understandable.

**How do roles improve reusability?**
Each role encapsulates one responsibility with its own defaults, handlers, and tasks. The `common` and `docker` roles can be included in any server provisioning project. Variables in `defaults/` provide sensible out-of-the-box behavior that can be overridden per environment without changing role code.

**What makes a task idempotent?**
A task is idempotent when it checks existing state before acting and only makes changes if current state differs from desired state. Ansible's built-in modules (apt, service, user, docker_container) all implement this natively — they check first, act only if needed.

**How do handlers improve efficiency?**
Handlers only run once at the end of a play, even if notified multiple times by different tasks. Without handlers, Docker would restart after every individual package or config task. With handlers, it restarts exactly once after all changes complete — saving time and avoiding unnecessary service disruptions.

**Why is Ansible Vault necessary?**
Credentials in plain text in a repository are a security breach. Any team member, CI system, or public viewer could see Docker Hub tokens. Vault encrypts secrets with AES-256 so the file can be safely committed and shared while keeping actual values accessible only to those with the vault password.

---

## 7. Challenges Encountered

- **WSL ↔ Windows networking**: WSL couldn't reach Vagrant VM on `127.0.0.1:2222` — fixed by adding a Windows portproxy (`netsh interface portproxy`) and using the WSL gateway IP `172.26.16.1` as the Ansible host
- **ansible.cfg ignored**: Ansible ignores config files in world-writable directories (Windows NTFS mounts in WSL) — fixed by copying the project to WSL home directory `~/ansible`
- **Docker GPG key**: The `apt_key` module is deprecated on Ubuntu 22.04 — fixed by using `curl | gpg --dearmor` to save key to `/etc/apt/keyrings/docker.gpg` with `signed-by=` in the repo line
- **Vault vars undefined in role**: With `become: true`, vault variables weren't passed into the role context — fixed by adding `vars_files: ../group_vars/all.yml` explicitly in `deploy.yml`
- **Vault password file path**: Relative path `.vault_pass` in `ansible.cfg` didn't work — fixed by using absolute path `/home/cdeth567/ansible/.vault_pass` locally (relative path used in repo version)
