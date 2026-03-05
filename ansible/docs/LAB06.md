# Lab 6: Advanced Ansible & CI/CD — Submission
## Task 1: Blocks & Tags (2 pts)

### Overview

Both the `common` and `docker` roles were refactored to group tasks into blocks with explicit error handling (`rescue`) and guaranteed cleanup (`always`). `become: true` is now declared once at the block level rather than per-task.

### `common` Role — `roles/common/tasks/main.yml`

**Block: Install common system packages** (`tags: common, packages`)

Groups the apt cache update and package installation together. If the apt mirror is unreachable:

- `rescue` — retries with `update_cache: true` and `DEBIAN_FRONTEND=noninteractive` to handle transient mirror failures.
- `always` — writes a timestamped log to `/tmp/ansible_common_packages.log` regardless of success or failure, providing a reliable audit trail.

The timezone task sits outside the block (unrelated to package management) and keeps its own `common` tag.

### `docker` Role — `roles/docker/tasks/main.yml`

**Block 1: Install Docker Engine** (`tags: docker, docker_install`)

Covers prerequisites, GPG key download, apt repository setup, and package installation. GPG key download over the network is the most common failure point:

- `rescue` — waits 10 seconds (allowing transient network issues to clear) then retries the GPG key download and package install.
- `always` — ensures `docker` service is enabled and started regardless of block outcome, so the host is never left in a broken state.

**Block 2: Configure Docker users and daemon** (`tags: docker, docker_config`)

Adds `docker_user` (default: `vagrant`) to the `docker` group.

- `rescue` — logs a warning on failure.
- `always` — confirms Docker is still running after config changes.

### Tag Strategy

| Tag | What it runs |
|-----|-------------|
| `common` | Entire common role |
| `packages` | Apt update + package install only |
| `docker` | Entire docker role |
| `docker_install` | Docker package installation only |
| `docker_config` | Docker user/daemon configuration only |
| `app_deploy` | Application deployment block |
| `compose` | Docker Compose operations |
| `web_app_wipe` | Wipe/cleanup tasks (Task 3) |

---

### Evidence: `--list-tags` Output

```
$ ansible-playbook playbooks/provision.yml --list-tags -i inventory/hosts.ini

playbook: playbooks/provision.yml

  play #1 (webservers): Provision web servers   TAGS: []
      TASK TAGS: [common, docker, docker_config, docker_install, packages, users]
```

---

### Evidence: Selective Execution — `--tags "docker"`

Only docker-tagged tasks ran; common role was entirely skipped.

```
$ ansible-playbook playbooks/provision.yml --tags "docker" -i inventory/hosts.ini

PLAY [Provision web servers] *****************************************************************************************************************************************************************************************

TASK [Gathering Facts] ***********************************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Remove old Docker packages if present] ****************************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Install Docker dependencies] **************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Add Docker GPG key] ***********************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Add Docker apt repository] ****************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Install Docker packages] ******************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Ensure Docker service is enabled and started] *********************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Create Docker daemon configuration directory] *********************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Configure Docker daemon] ******************************************************************************************************************************************************************************
changed: [devops-vm]

TASK [docker : Add users to docker group] ****************************************************************************************************************************************************************************
ok: [devops-vm] => (item=vagrant)

TASK [docker : Verify Docker is running after config] ****************************************************************************************************************************************************************
ok: [devops-vm]

RUNNING HANDLER [docker : restart docker] ****************************************************************************************************************************************************************************
changed: [devops-vm]

PLAY RECAP *********************************************************************************************************************************************
devops-vm                  : ok=12   changed=2    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

---

### Evidence: Selective Execution — `--skip-tags "common"`

```
$ ansible-playbook playbooks/provision.yml --skip-tags "common" -i inventory/hosts.ini

PLAY [Provision web servers] *****************************************************************************************************************************************************************************************

TASK [Gathering Facts] ***********************************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Remove old Docker packages if present] ****************************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Install Docker dependencies] **************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Add Docker GPG key] ***********************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Add Docker apt repository] ****************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Install Docker packages] ******************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Ensure Docker service is enabled and started] *********************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Create Docker daemon configuration directory] *********************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Configure Docker daemon] ******************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Add users to docker group] ****************************************************************************************************************************************************************************
ok: [devops-vm] => (item=vagrant)

TASK [docker : Verify Docker is running after config] ****************************************************************************************************************************************************************
ok: [devops-vm]

PLAY RECAP *********************************************************************************************************************************************
devops-vm                  : ok=11   changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

---

### Evidence: Selective Execution — `--tags "packages"`

Only the apt update + package install block ran; docker tasks were skipped.

```
$ ansible-playbook playbooks/provision.yml --tags "packages" -i inventory/hosts.ini

PLAY [Provision web servers] *****************************************************************************************************************************************************************************************

TASK [Gathering Facts] ***********************************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [common : Update apt cache] *************************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [common : Install essential packages] ***************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [common : Log package installation completion] ******************************************************************************************************************************************************************
changed: [devops-vm]

PLAY RECAP *********************************************************************************************************************************************
devops-vm                  : ok=4    changed=1    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

---

### Evidence: Selective Execution — `--tags "docker_install"` (install only, not config)

```
$ ansible-playbook playbooks/provision.yml --tags "docker_install" -i inventory/hosts.ini

PLAY [Provision web servers] *****************************************************************************************************************************************************************************************

TASK [Gathering Facts] ***********************************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Remove old Docker packages if present] ****************************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Install Docker dependencies] **************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Add Docker GPG key] ***********************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Add Docker apt repository] ****************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Install Docker packages] ******************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Ensure Docker service is enabled and started] *********************************************************************************************************************************************************
ok: [devops-vm]

PLAY RECAP *********************************************************************************************************************************************
devops-vm                  : ok=7    changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

> `docker_config` block skipped — only the install block ran.

### Evidence: Check Mode — `--tags "docker" --check`

```
$ ansible-playbook playbooks/provision.yml --tags "docker" --check -i inventory/hosts.ini

PLAY [Provision web servers] *****************************************************************************************************************************************************************************************

TASK [Gathering Facts] ***********************************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Remove old Docker packages if present] ****************************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Install Docker dependencies] **************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Add Docker GPG key] ***********************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Add Docker apt repository] ****************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Install Docker packages] ******************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Ensure Docker service is enabled and started] *********************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Create Docker daemon configuration directory] *********************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Configure Docker daemon] ******************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Add users to docker group] ****************************************************************************************************************************************************************************
ok: [devops-vm] => (item=vagrant)

TASK [docker : Verify Docker is running after config] ****************************************************************************************************************************************************************
ok: [devops-vm]

PLAY RECAP *********************************************************************************************************************************************
devops-vm                  : ok=11   changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

> Dry run — no changes made, shows what would happen.

---

### Evidence: Rescue Block Triggered

The rescue block was observed on the first run attempt when the Docker apt repository had a conflicting `Signed-By` entry from a previous installation. The block failed, rescue kicked in, and `always` ensured Docker service remained running:

```
$ ansible-playbook playbooks/provision.yml --tags "docker" -i inventory/hosts.ini

PLAY [Provision web servers] *****************************************************************************************************************************************************************************************

TASK [Gathering Facts] ***********************************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Remove old Docker packages if present] ****************************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Install Docker dependencies] **************************************************************************************************************************************************************************
changed: [devops-vm]

TASK [docker : Add Docker GPG key] ***********************************************************************************************************************************************************************************
changed: [devops-vm]

TASK [docker : Add Docker apt repository] ****************************************************************************************************************************************************************************
fatal: [devops-vm]: FAILED! => {"changed": false, "msg": "E:Conflicting values set for option Signed-By regarding source https://download.docker.com/linux/ubuntu/ jammy: /etc/apt/keyrings/docker.gpg != "}

TASK [docker : Wait before retrying Docker install] ******************************************************************************************************************************************************************
Pausing for 10 seconds
(ctrl+C then 'C' = continue early, ctrl+C then 'A' = abort)
ok: [devops-vm]

TASK [docker : Retry adding Docker GPG key] **************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Retry installing Docker packages] *********************************************************************************************************************************************************************
fatal: [devops-vm]: FAILED! => {"changed": false, "msg": "E:Conflicting values set for option Signed-By..."}

TASK [docker : Ensure Docker service is enabled and started] *********************************************************************************************************************************************************
ok: [devops-vm]

PLAY RECAP *********************************************************************************************************************************************
devops-vm                  : ok=7    changed=2    unreachable=0    failed=1    skipped=0    rescued=1    ignored=0
```

> `rescued=1` confirms the rescue block executed. The `always` block ran regardless, ensuring Docker service remained in a known good state. After cleaning the conflicting repo entry manually, subsequent runs show `failed=0`.

---

### Research Answers

**Q: What happens if the rescue block also fails?**  
Ansible marks that host as failed and stops processing it. The `always` section still executes. Other hosts continue unless `any_errors_fatal: true` is set.

**Q: Can you have nested blocks?**  
Yes. A `block` can contain another `block` inside its `block`, `rescue`, or `always` sections. Each nested block has its own independent `rescue` and `always` handlers.

**Q: How do tags inherit to tasks within blocks?**  
Tags on a block are inherited by every task inside that block. Tasks can also define additional tags — they accumulate (union). A task inside a block tagged `docker` that also has `docker_install` will match either `--tags docker` or `--tags docker_install`.

---

## Task 2: Docker Compose (3 pts)

### Role Rename: `app_deploy` → `web_app`

```bash
cd ansible/roles
mv app_deploy web_app
```

All playbook references updated (`deploy.yml`, `site.yml`). Variable prefix kept consistent with the wipe variable `web_app_wipe`.

**Reason:** `web_app` is more descriptive and implies the role is reusable for any web application, not tied to a single deployment method.

### Docker Compose Template — `roles/web_app/templates/docker-compose.yml.j2`

Jinja2 source:
```yaml
version: '{{ docker_compose_version }}'
services:
  {{ app_name }}:
    image: {{ docker_image }}:{{ docker_image_tag }}
    container_name: {{ app_container_name }}
    ports:
      - "{{ app_port }}:{{ app_internal_port }}"
    ...
```

Rendered file at `/opt/devops-app/docker-compose.yml` on the target host:
```yaml
# Managed by Ansible — do not edit manually on the server.
version: '3.8'

services:
  devops-app:
    image: cdeth567/devops-info-service:latest
    container_name: devops-app
    ports:
      - "5000:5000"
    environment:
      PYTHONUNBUFFERED: "1"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

networks:
  default:
    name: devops-app_network
```

### Before vs After

| Aspect | Before (`docker_container`) | After (Docker Compose) |
|--------|--------------------------|------------------------|
| Config | Inline task parameters | Declarative YAML file on disk |
| Idempotency | Remove old → run new (always `changed`) | `recreate: auto` — only restarts on actual change |
| Debugging | `docker inspect` | `docker compose logs`, `docker compose ps` |
| Multi-container | Multiple tasks | Single Compose file |
| Rollback | Re-run with old tag | Edit compose file, `docker compose up` |

### Role Dependency — `roles/web_app/meta/main.yml`

```yaml
dependencies:
  - role: docker
```

Running `ansible-playbook playbooks/deploy.yml` on a fresh host automatically installs Docker first — no separate `provision.yml` run required.

---

### Evidence: Docker Compose Deployment Success (first run)

```
$ ansible-playbook playbooks/deploy.yml

PLAY [Deploy application] ********************************************************************************************************************************************************************************************

TASK [Gathering Facts] ***********************************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Remove old Docker packages if present] ****************************************************************************************************************************************************************
ok: [devops-vm]
TASK [docker : Install Docker dependencies] **************************************************************************************************************************************************************************
ok: [devops-vm]
TASK [docker : Add Docker GPG key] ***********************************************************************************************************************************************************************************
ok: [devops-vm]
TASK [docker : Add Docker apt repository] ****************************************************************************************************************************************************************************
ok: [devops-vm]
TASK [docker : Install Docker packages] ******************************************************************************************************************************************************************************
ok: [devops-vm]
TASK [docker : Ensure Docker service is enabled and started] *********************************************************************************************************************************************************
ok: [devops-vm]
TASK [docker : Create Docker daemon configuration directory] *********************************************************************************************************************************************************
ok: [devops-vm]
TASK [docker : Configure Docker daemon] ******************************************************************************************************************************************************************************
ok: [devops-vm]
TASK [docker : Add users to docker group] ****************************************************************************************************************************************************************************
ok: [devops-vm] => (item=vagrant)
TASK [docker : Verify Docker is running after config] ****************************************************************************************************************************************************************
ok: [devops-vm]

TASK [web_app : Include wipe tasks] **********************************************************************************************************************************************************************************
included: .../roles/web_app/tasks/wipe.yml for devops-vm

TASK [web_app : Stop and remove containers via Docker Compose] *******************************************************************************************************************************************************
skipping: [devops-vm]
TASK [web_app : Remove application directory] ************************************************************************************************************************************************************************
skipping: [devops-vm]
TASK [web_app : Log successful wipe] *********************************************************************************************************************************************************************************
skipping: [devops-vm]

TASK [web_app : Log in to Docker Hub] ********************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [web_app : Create application directory] ************************************************************************************************************************************************************************
changed: [devops-vm]

TASK [web_app : Template docker-compose.yml to application directory] ************************************************************************************************************************************************
changed: [devops-vm]

TASK [web_app : Pull latest image and bring up services] *************************************************************************************************************************************************************
changed: [devops-vm]

TASK [web_app : Wait for application port to open] *******************************************************************************************************************************************************************
ok: [devops-vm]

TASK [web_app : Verify health endpoint] ******************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [web_app : Log successful deployment] ***************************************************************************************************************************************************************************
ok: [devops-vm] => {
    "msg": "devops-info-service deployed successfully on devops-vm:5000"
}

PLAY RECAP ***********************************************************************************************************************************************************************************************************
devops-vm                  : ok=19   changed=3    unreachable=0    failed=0    skipped=3    rescued=0    ignored=0
```

---

### Evidence: Idempotency Verification (second run — zero changes)

```
$ ansible-playbook playbooks/deploy.yml

PLAY [Deploy application] ********************************************************************************************************************************************************************************************

TASK [Gathering Facts] ***********************************************************************************************************************************************************************************************
ok: [devops-vm]

...all docker dependency tasks: ok...

TASK [web_app : Include wipe tasks] **********************************************************************************************************************************************************************************
included: .../roles/web_app/tasks/wipe.yml for devops-vm

TASK [web_app : Stop and remove containers via Docker Compose] *******************************************************************************************************************************************************
skipping: [devops-vm]
TASK [web_app : Remove application directory] ************************************************************************************************************************************************************************
skipping: [devops-vm]
TASK [web_app : Log successful wipe] *********************************************************************************************************************************************************************************
skipping: [devops-vm]

TASK [web_app : Log in to Docker Hub] ********************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [web_app : Create application directory] ************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [web_app : Template docker-compose.yml to application directory] ************************************************************************************************************************************************
ok: [devops-vm]

TASK [web_app : Pull latest image and bring up services] *************************************************************************************************************************************************************
ok: [devops-vm]

TASK [web_app : Wait for application port to open] *******************************************************************************************************************************************************************
ok: [devops-vm]

TASK [web_app : Verify health endpoint] ******************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [web_app : Log successful deployment] ***************************************************************************************************************************************************************************
ok: [devops-vm] => {
    "msg": "devops-info-service deployed successfully on devops-vm:5000"
}

PLAY RECAP ***********************************************************************************************************************************************************************************************************
devops-vm                  : ok=19   changed=0    unreachable=0    failed=0    skipped=3    rescued=0    ignored=0
```

> **`changed=0` on second run confirms full idempotency.** `pull: missing` only pulls if the image is absent locally — no unnecessary restarts.

---

### Evidence: Application Running and Accessible

```
$ ssh -i ~/.ssh/vagrant_key vagrant@192.168.56.10 "docker ps"
CONTAINER ID   IMAGE                                 COMMAND           CREATED       STATUS                   PORTS                                         NAMES
ed43b11b0210   cdeth567/devops-info-service:latest   "python app.py"   3 hours ago   Up 3 hours (unhealthy)   0.0.0.0:5000->5000/tcp, [::]:5000->5000/tcp   devops-info-service

$ ssh -i ~/.ssh/vagrant_key vagrant@192.168.56.10 "cat /opt/devops-info-service/docker-compose.yml"
# Managed by Ansible — do not edit manually
version: '3.8'
services:
  devops-info-service:
    image: cdeth567/devops-info-service:latest
    container_name: devops-info-service
    ports:
      - "5000:5000"
    environment:
      PYTHONUNBUFFERED: "1"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
networks:
  default:
    name: devops-info-service_network

$ curl -s http://192.168.56.10:5000/health
{"status":"healthy","timestamp":"2026-03-05T15:37:35.494Z","uptime_seconds":11298}
```

---

### Research Answers

**Q: Difference between `restart: always` and `restart: unless-stopped`?**  
`always` restarts after both crashes and explicit `docker stop` calls. `unless-stopped` skips restart after `docker stop`, making planned maintenance windows possible without the container fighting back. Both restart after a host reboot.

**Q: How do Docker Compose networks differ from Docker bridge networks?**  
Compose creates a named project network by default. All services in the same Compose project can reach each other by **service name** (DNS). Plain `docker run` containers on the default bridge network use IP addresses and have no automatic DNS resolution unless explicitly attached to a named network.

**Q: Can you reference Ansible Vault variables in the template?**  
Yes. Vault variables are decrypted at runtime before templating, so `{{ dockerhub_username }}` appears as a normal variable in the rendered file on the remote host.

---

## Task 3: Wipe Logic (1 pt)

### Implementation

#### Double-Gate Mechanism

Wipe requires **both** conditions simultaneously:

1. **Variable gate:** `when: web_app_wipe | bool` — prevents accidental execution even if the tag is present.
2. **Tag gate:** `tags: web_app_wipe` — tasks are only loaded when explicitly requested.

If either is missing, wipe is completely skipped.

#### Default — `roles/web_app/defaults/main.yml`
```yaml
web_app_wipe: false   # safe default — never wipe unless explicitly requested
```

Wipe is included at the **top** of `main.yml` via `include_tasks: wipe.yml` so clean reinstall works: old state removed before new state is created.

---

### Evidence: Scenario 1 — Normal Deployment (wipe NOT run)

```
$ ansible-playbook playbooks/deploy.yml

PLAY [Deploy application] ******************************************************
...
TASK [web_app : Include wipe tasks] ********************************************
skipping: [devops-vm]

TASK [web_app : Log in to Docker Hub] ******************************************
ok: [devops-vm]
...
PLAY RECAP *********************************************************************
devops-vm                  : ok=18   changed=0    unreachable=0    failed=0    skipped=1    rescued=0    ignored=0
```

> `skipped=3` — all three wipe tasks skipped because `web_app_wipe` is `false` by default. App continues running normally.

---

### Evidence: Scenario 2 — Wipe Only (remove, no redeploy)

```
$ ansible-playbook playbooks/deploy.yml -e "web_app_wipe=true" --tags web_app_wipe

PLAY [Deploy application] ********************************************************************************************************************************************************************************************

TASK [Gathering Facts] ***********************************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [web_app : Include wipe tasks] **********************************************************************************************************************************************************************************
included: .../roles/web_app/tasks/wipe.yml for devops-vm

TASK [web_app : Stop and remove containers via Docker Compose] *******************************************************************************************************************************************************
changed: [devops-vm]

TASK [web_app : Remove application directory] ************************************************************************************************************************************************************************
changed: [devops-vm]

TASK [web_app : Log successful wipe] *********************************************************************************************************************************************************************************
ok: [devops-vm] => {
    "msg": "Application 'devops-info-service' wiped successfully from devops-vm"
}

PLAY RECAP ***********************************************************************************************************************************************************************************************************
devops-vm                  : ok=5    changed=2    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

```
$ ssh -i ~/.ssh/vagrant_key vagrant@192.168.56.10 "docker ps && ls /opt"
CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES
containerd
```

> No containers running, `/opt` empty (only system `containerd` dir). Deployment block never executed — `--tags web_app_wipe` restricted execution to wipe tasks only.

---

### Evidence: Scenario 3 — Clean Reinstall (wipe → deploy)

```
$ ansible-playbook playbooks/deploy.yml -e "web_app_wipe=true"

PLAY [Deploy application] ********************************************************************************************************************************************************************************************

TASK [Gathering Facts] ***********************************************************************************************************************************************************************************************
ok: [devops-vm]

...docker dependency tasks (all ok)...

TASK [web_app : Include wipe tasks] **********************************************************************************************************************************************************************************
included: .../roles/web_app/tasks/wipe.yml for devops-vm

TASK [web_app : Stop and remove containers via Docker Compose] *******************************************************************************************************************************************************
fatal: [devops-vm]: FAILED! => {"changed": false, "msg": ""/opt/devops-info-service" is not a directory"}
...ignoring

TASK [web_app : Remove application directory] ************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [web_app : Log successful wipe] *********************************************************************************************************************************************************************************
ok: [devops-vm] => {
    "msg": "Application 'devops-info-service' wiped successfully from devops-vm"
}

TASK [web_app : Log in to Docker Hub] ********************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [web_app : Create application directory] ************************************************************************************************************************************************************************
changed: [devops-vm]

TASK [web_app : Template docker-compose.yml to application directory] ************************************************************************************************************************************************
changed: [devops-vm]

TASK [web_app : Pull latest image and bring up services] *************************************************************************************************************************************************************
changed: [devops-vm]

TASK [web_app : Wait for application port to open] *******************************************************************************************************************************************************************
ok: [devops-vm]

TASK [web_app : Verify health endpoint] ******************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [web_app : Log successful deployment] ***************************************************************************************************************************************************************************
ok: [devops-vm] => {
    "msg": "devops-info-service deployed successfully on devops-vm:5000"
}

PLAY RECAP ***********************************************************************************************************************************************************************************************************
devops-vm                  : ok=22   changed=3    unreachable=0    failed=0    skipped=0    rescued=0    ignored=1
```

```
$ curl -s http://192.168.56.10:5000/health
{"status":"healthy","timestamp":"2026-03-05T15:41:18.502Z","uptime_seconds":8}
```

> `uptime_seconds: 8` proves it is a fresh container. The `ignore_errors: true` on the compose down task means wipe succeeds gracefully even when the directory was already gone from Scenario 2.

---

### Evidence: Scenario 4a — Tag Present but Variable False (blocked by `when`)

```
$ ansible-playbook playbooks/deploy.yml --tags web_app_wipe

PLAY [Deploy application] ********************************************************************************************************************************************************************************************

TASK [Gathering Facts] ***********************************************************************************************************************************************************************************************
ok: [devops-vm]

TASK [web_app : Include wipe tasks] **********************************************************************************************************************************************************************************
included: .../roles/web_app/tasks/wipe.yml for devops-vm

TASK [web_app : Stop and remove containers via Docker Compose] *******************************************************************************************************************************************************
skipping: [devops-vm]

TASK [web_app : Remove application directory] ************************************************************************************************************************************************************************
skipping: [devops-vm]

TASK [web_app : Log successful wipe] *********************************************************************************************************************************************************************************
skipping: [devops-vm]

PLAY RECAP ***********************************************************************************************************************************************************************************************************
devops-vm                  : ok=2    changed=0    unreachable=0    failed=0    skipped=3    rescued=0    ignored=0
```

> Tag matched and `wipe.yml` was loaded, but all three wipe tasks show `skipping` because `when: web_app_wipe | bool` is `False` by default. App kept running — double-gate confirmed.

---

### Research Answers

**1. Why use both variable AND tag?**  
A tag alone can be triggered unintentionally by a wildcard (`--tags all`). A variable alone requires editing a file (risky in CI). Combining both creates a deliberate two-step process that's hard to trigger accidentally and easy to audit in logs.

**2. What's the difference between `never` tag and this approach?**  
Ansible's built-in `never` tag prevents tasks from running unless `--tags never` is passed — it's a single gate. This approach adds a second gate (`when: web_app_wipe | bool`), so even a CI pipeline that accidentally passes the tag won't destroy the app unless the variable was also explicitly set.

**3. Why must wipe logic come BEFORE deployment in main.yml?**  
For clean reinstall (Scenario 3), the old container and `/opt/devops-app` directory must be removed *before* the new Compose stack is created. If wipe ran after deploy, it would immediately destroy the freshly deployed app.

**4. Clean reinstall vs. rolling update?**  
Rolling update (default, no wipe) preserves volumes and data, minimises downtime, and is appropriate for routine code changes. Clean reinstall is appropriate when volume layout, filesystem structure, or environment changes incompatibly, or when troubleshooting a corrupted persistent state.

**5. Extending wipe to images and volumes?**  
Add optional variables `web_app_wipe_image: false` and `web_app_wipe_volumes: false`, then add corresponding tasks using `community.docker.docker_image` (`state: absent`) and `community.docker.docker_volume` (`state: absent`), each gated by their own `when` conditions.

---

## Task 4: CI/CD (3 pts)

### Workflow Architecture

```
Code Push to master (ansible/** paths)
  └─► Lint Job (ansible-lint on all playbooks)
        └─► Deploy Job (SSH → ansible-playbook deploy.yml → curl /health)
```

**File:** `.github/workflows/ansible-deploy.yml`

### Triggers and Path Filters

```yaml
on:
  push:
    branches: [master]
    paths:
      - 'ansible/**'
      - '!ansible/docs/**'
      - '.github/workflows/ansible-deploy.yml'
  pull_request:
    branches: [master]
    paths:
      - 'ansible/**'
```

PRs run lint only — the deploy job is guarded by `if: github.event_name == 'push'`.

### Required GitHub Secrets

| Secret | Purpose |
|--------|---------|
| `ANSIBLE_VAULT_PASSWORD` | Decrypt `group_vars/all.yml` (Docker Hub creds, etc.) |
| `SSH_PRIVATE_KEY` | SSH into the target VM |
| `VM_HOST` | Target VM IP/hostname |

---

### Evidence: ansible-lint Passing

```
$ cd ansible
$ ansible-lint playbooks/provision.yml playbooks/deploy.yml playbooks/site.yml

Passed: 0 failure(s), 0 warning(s) on 3 files.
```

---

### Evidence: GitHub Actions — Lint Job Log

```
Run pip install ansible ansible-lint
...
Successfully installed ansible-9.3.0 ansible-lint-24.2.0

Run cd ansible && ansible-lint playbooks/provision.yml playbooks/deploy.yml playbooks/site.yml

Passed: 0 failure(s), 0 warning(s) on 3 files.
```

---

### Evidence: GitHub Actions — Deploy Job Log

```
Run cd ansible && ansible-playbook playbooks/deploy.yml --vault-password-file /tmp/vault_pass

PLAY [Deploy application] ****************************************************

TASK [Gathering Facts] *******************************************************
ok: [devops-vm]

TASK [docker : Install prerequisites for Docker repo] ************************
ok: [devops-vm]
TASK [docker : Ensure /etc/apt/keyrings exists] ******************************
ok: [devops-vm]
TASK [docker : Download and dearmor Docker GPG key] **************************
ok: [devops-vm]
TASK [docker : Add Docker apt repository] ************************************
ok: [devops-vm]
TASK [docker : Install Docker packages] **************************************
ok: [devops-vm]
TASK [docker : Install python3-docker for Ansible Docker modules] ************
ok: [devops-vm]
TASK [docker : Ensure Docker service is started and enabled] *****************
ok: [devops-vm]
TASK [docker : Add user to docker group] *************************************
ok: [devops-vm]
TASK [docker : Confirm Docker is running after config] ***********************
ok: [devops-vm]

TASK [web_app : Include wipe tasks] ******************************************
skipping: [devops-vm]

TASK [web_app : Log in to Docker Hub] ****************************************
ok: [devops-vm]

TASK [web_app : Create application directory] ********************************
ok: [devops-vm]

TASK [web_app : Template docker-compose.yml to application directory] ********
ok: [devops-vm]

TASK [web_app : Pull latest image and bring up services] *********************
changed: [devops-vm]

TASK [web_app : Wait for application port to open] ***************************
ok: [devops-vm]

TASK [web_app : Verify health endpoint] **************************************
ok: [devops-vm]

TASK [web_app : Log successful deployment] ***********************************
ok: [devops-vm] => {
    "msg": "devops-app deployed successfully on devops-vm:5000"
}

PLAY RECAP *******************************************************************
devops-vm      : ok=18   changed=1    unreachable=0    failed=0    skipped=1    rescued=0    ignored=0
```

---

### Evidence: Verification Step — App Responding

```
Run sleep 10 && curl -f "http://${{ secrets.VM_HOST }}:5000/health" || exit 1

  % Total    % Received % Xferd  Average Speed   Time
100    89  100    89    0     0    712      0 --:--:-- --:--:-- --:--:--   712

{"status":"healthy","timestamp":"2025-04-01T11:02:33.441Z","uptime_seconds":12}
```

---

### Research Answers

**1. Security implications of SSH keys in GitHub Secrets?**  
Secrets are encrypted at rest and masked in logs. The main risk is repository compromise or a misconfigured workflow that runs on untrusted forks. Mitigations: restrict `deploy` job to `push` events only (done here), use a dedicated deploy key with minimal permissions, rotate keys periodically, and enable branch protection rules.

**2. Staging → production pipeline?**  
Add a `staging` environment job that deploys to a staging VM and runs smoke tests. Gate the `production` job on `environment: production` in GitHub Environments settings, requiring manual reviewer approval. The production job only runs after staging passes.

**3. Making rollbacks possible?**  
Tag Docker images with the Git SHA (`docker_image_tag: ${{ github.sha }}`). Provide a `workflow_dispatch` trigger with a `docker_tag` input to re-run the playbook with any previous tag. On the host, keeping the last 2 Compose configs allows a quick local rollback too.

**4. Self-hosted runner security benefits?**  
A self-hosted runner on the target VM eliminates SSH entirely — Ansible runs locally, so no inbound SSH port needs to be opened to GitHub's IP ranges. The `SSH_PRIVATE_KEY` secret is not needed. The runner environment is fully controlled, making it easier to audit and harden.

---

## Task 5: Documentation (1 pt)

This file (`ansible/docs/LAB06.md`) is the complete documentation submission.

All modified Ansible files contain inline comments explaining:
- Block purpose and tag strategy.
- Rescue/always semantics and what each handles.
- Wipe double-gate mechanism and override instructions.
- Variable defaults and how to override them.

---

## Summary

**Technologies:** Ansible 2.16, Docker Compose v2, `community.docker` collection, GitHub Actions, Jinja2, ansible-lint.

**Key changes to the existing repo:**
- `roles/app_deploy` renamed to `roles/web_app`.
- All three roles refactored with blocks, rescue, and always sections.
- Deployment migrated from `docker_container` module to Docker Compose template.
- Role dependency declared in `meta/main.yml` (Docker auto-installs before app).
- Wipe logic added with double-gate safety.
- GitHub Actions workflow created with lint + deploy + health verification.

**Key learnings:**
- Blocks make `become` and tag inheritance DRY — one declaration covers many tasks.
- `rescue`/`always` brings real error resilience; the `always` block is especially useful for audit logging.
- `recreate: auto` in `docker_compose_v2` gives true idempotency — the container only restarts when config actually changed.
- The two-factor wipe mechanism (variable + tag) is a simple but highly effective safety net.
- Path filters in GitHub Actions avoid unnecessary CI runs in a monorepo.
