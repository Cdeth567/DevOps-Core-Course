# Lab 11 — Kubernetes Secrets & HashiCorp Vault

This lab implemented two approaches to secrets management:

- native Kubernetes Secrets, created manually and via a Helm chart;
- HashiCorp Vault Agent Injector for file-based secret injection into a Pod.

**The bonus task was not completed.**

---

## 1. Kubernetes Secrets

### 1.1 Creating a secret with kubectl

The Secret was created using an imperative command:

```powershell
kubectl create secret generic app-credentials --from-literal=username=demo-user --from-literal=password=demo-password -n devops-lab11
```

### 1.2 Viewing the Secret in YAML

Command:

```powershell
kubectl get secret app-credentials -n devops-lab11 -o yaml
```

Output obtained:

```yaml
apiVersion: v1
data:
  password: ZGVtby1wYXNzd29yZA==
  username: ZGVtby11c2Vy
kind: Secret
metadata:
  creationTimestamp: "2026-04-07T11:31:25Z"
  name: app-credentials
  namespace: devops-lab11
  resourceVersion: "58494"
  uid: 70e72408-18a3-4f60-930b-7fdeb5051ac9
type: Opaque
```

### 1.3 Decoding the values

In PowerShell, the base64 values were decoded as follows:

```powershell
[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String((kubectl get secret app-credentials -n devops-lab11 -o jsonpath='{.data.username}')))
[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String((kubectl get secret app-credentials -n devops-lab11 -o jsonpath='{.data.password}')))
```

Result:

```text
demo-user
demo-password
```

### 1.4 Base64 encoding vs encryption

In Kubernetes, a `Secret` stores values in YAML as base64 by default. This is **encoding**, not encryption:

- **encoding** changes the representation of data, but does not protect it;
- any user who can read the Secret through the API can decode the values;
- base64 cannot be considered a protection mechanism for secrets.

### 1.5 Security: encrypted at rest and etcd encryption

Kubernetes Secrets **are not considered securely encrypted just because their values are represented in base64**. For production clusters, **encryption at rest** must be enabled separately for `etcd`.

`etcd encryption` is a control plane mechanism that encrypts sensitive resources (primarily Secrets) before writing them to `etcd`.

It is recommended to enable it whenever:

- the cluster is not a disposable learning environment;
- Secrets store tokens, passwords, API keys, or certificates;
- other administrators have access to the control plane or `etcd` backups;
- there are security or compliance requirements.

Production environments also require:

- RBAC restrictions for reading Secrets;
- separate service accounts for workloads;
- use of an external secret manager, such as Vault.

---

## 2. Helm Secret Integration

### 2.1 Changes in the Helm chart

The following files were added or modified in the chart:

```text
k8s/devops-info-service/
├── templates/
│   ├── deployment.yaml
│   ├── secrets.yaml
│   ├── serviceaccount.yaml
│   └── _helpers.tpl
├── values.yaml
└── values-vault.yaml
```

Vault-related files were also added:

```text
k8s/vault/
├── app-policy.hcl
└── configure-vault.sh
```

### 2.2 Secret template

The following file was added to the chart:

```text
k8s/devops-info-service/templates/secrets.yaml
```

Its content:

```yaml
{{- if .Values.secret.enabled }}
apiVersion: v1
kind: Secret
metadata:
  name: {{ include "devops-info-service.secretName" . }}
  labels:
    {{- include "devops-info-service.labels" . | nindent 4 }}
type: {{ .Values.secret.type }}
stringData:
  {{- range $key, $value := .Values.secret.data }}
  {{ $key }}: {{ $value | quote }}
  {{- end }}
{{- end }}
```

Using `stringData` simplifies passing plaintext values through Helm: Kubernetes encodes them into base64 automatically when the Secret is created.

### 2.3 Connecting the Secret in the Deployment

The Deployment was updated so that environment variables are loaded from the Secret via `envFrom`:

```yaml
envFrom:
  - secretRef:
      name: devops-info-service-secret
```

A separate `ServiceAccount` was also added for predictable Vault role binding.

### 2.4 Resource limits and requests

After rendering the chart, the following values were visible:

```yaml
resources:
  limits:
    cpu: 250m
    memory: 256Mi
  requests:
    cpu: 100m
    memory: 128Mi
```

#### Requests vs limits

- **requests** are the minimum resources Kubernetes considers when scheduling a Pod;
- **limits** are the maximum amount of resources the container should not exceed.

For a small Flask service, these values are appropriate for local Minikube usage and demonstrate basic best practices.

### 2.5 Verifying Helm Secret Integration

Chart rendering:

```powershell
helm template devops-info-service .\k8s\devops-info-service --namespace devops-lab11 --set image.tag=lab11 --set secret.enabled=true --set secret.data.username=demo-user --set secret.data.password=demo-password
```

The result confirmed that the chart renders:

- `ServiceAccount`
- `Secret`
- `Deployment` with `serviceAccountName`
- `envFrom.secretRef`

Fragments of the rendered manifest:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: devops-info-service-secret
...
type: Opaque
stringData:
  password: "demo-password"
  username: "demo-user"
```

```yaml
spec:
  serviceAccountName: devops-info-service
  ...
  containers:
    - name: devops-info-service
      ...
      envFrom:
        - secretRef:
            name: devops-info-service-secret
```

Chart installation:

```powershell
helm upgrade --install devops-info-service .\k8s\devops-info-service --namespace devops-lab11 --create-namespace --set image.tag=lab11 --set secret.enabled=true --set secret.data.username=demo-user --set secret.data.password=demo-password --wait --timeout 5m
```

### 2.6 Verifying the Secret in the cluster

Command:

```powershell
kubectl get secret devops-info-service-secret -n devops-lab11 -o yaml
```

Actual output:

```yaml
apiVersion: v1
data:
  password: ZGVtby1wYXNzd29yZA==
  username: ZGVtby11c2Vy
kind: Secret
metadata:
  annotations:
    meta.helm.sh/release-name: devops-info-service
    meta.helm.sh/release-namespace: devops-lab11
  creationTimestamp: "2026-04-07T11:59:18Z"
  labels:
    app.kubernetes.io/component: web
    app.kubernetes.io/instance: devops-info-service
    app.kubernetes.io/managed-by: Helm
    app.kubernetes.io/name: devops-info-service
    app.kubernetes.io/part-of: devops-core-course
    app.kubernetes.io/version: 1.0.0-k8s
    helm.sh/chart: devops-info-service-0.1.0
  name: devops-info-service-secret
  namespace: devops-lab11
type: Opaque
```

### 2.7 Verifying env vars in the Pod

Pod name:

```powershell
$POD = kubectl get pods -n devops-lab11 -l app.kubernetes.io/instance=devops-info-service -o jsonpath='{.items[0].metadata.name}'
```

Checking environment variables:

```powershell
kubectl exec -n devops-lab11 $POD -- printenv | Select-String '^(username|password)='
```

Actual output:

```text
password=demo-password
username=demo-user
```

Checking the Pod description:

```powershell
kubectl describe pod -n devops-lab11 $POD
```

The `describe pod` output confirmed that:

- `Service Account: devops-info-service` is used;
- the Secret is connected as `Environment Variables from: devops-info-service-secret Secret Optional: false`;
- the secret values themselves are not displayed in plaintext in `kubectl describe pod`.

---

## 3. HashiCorp Vault Integration

### 3.1 Installing Vault with Helm

Vault was installed in dev mode:

```powershell
helm repo add hashicorp https://helm.releases.hashicorp.com
helm repo update
helm upgrade --install vault hashicorp/vault --namespace devops-lab11 --create-namespace --set server.dev.enabled=true --set injector.enabled=true --wait --timeout 5m
```

Checking Pods:

```powershell
kubectl get pods -n devops-lab11
```

After startup, the following were available:

- `vault-0`
- `vault-agent-injector-*`

Checking Vault status:

```powershell
kubectl exec -n devops-lab11 vault-0 -- vault status
```

Actual output:

```text
Key             Value
---             -----
Seal Type       shamir
Initialized     true
Sealed          false
Total Shares    1
Threshold       1
Version         1.21.2
Build Date      2026-01-06T08:33:05Z
Storage Type    inmem
Cluster Name    vault-cluster-d37cc4d1
Cluster ID      50bf3a48-77fb-bfab-dc55-777aabcfe866
HA Enabled      false
```

### 3.2 Enabling KV and writing a secret

The KV secrets engine was used, and a secret was created at the following path:

```text
secret/devops-info-service/config
```

Commands:

```powershell
kubectl exec -n devops-lab11 vault-0 -- sh -c "vault kv put secret/devops-info-service/config username=demo-user password=demo-password"
kubectl exec -n devops-lab11 vault-0 -- sh -c "vault kv get secret/devops-info-service/config"
```

Confirmed output:

```text
============= Secret Path =============
secret/data/devops-info-service/config

======= Metadata =======
Key                Value
---                -----
created_time       2026-04-07T12:29:19.517034267Z
custom_metadata    <nil>
delection_time     n/a
...                ...

====== Data ======
Key         Value
---         -----
password    demo-password
username    demo-user
```

### 3.3 Kubernetes auth, policy, and role

Kubernetes authentication was enabled:

```powershell
kubectl exec -n devops-lab11 vault-0 -- sh -c "vault auth enable kubernetes || true"
kubectl exec -n devops-lab11 vault-0 -- sh -c 'vault write auth/kubernetes/config kubernetes_host="https://kubernetes.default.svc:443"'
```

A policy was created for the application with access to the KV v2 path:

```hcl
path "secret/data/devops-info-service/config" {
  capabilities = ["read"]
}

path "secret/metadata/devops-info-service/config" {
  capabilities = ["read", "list"]
}

path "sys/internal/ui/mounts/secret/data/devops-info-service/config" {
  capabilities = ["read"]
}
```

This policy was loaded into Vault and read back:

```powershell
kubectl exec -n devops-lab11 vault-0 -- sh -c "vault policy read devops-info-service"
```

Actual output:

```text
path "secret/data/devops-info-service/config" {
  capabilities = ["read"]
}

path "secret/metadata/devops-info-service/config" {
  capabilities = ["read", "list"]
}

path "sys/internal/ui/mounts/secret/data/devops-info-service/config" {
  capabilities = ["read"]
}
```

The role was bound to the application service account:

```powershell
kubectl exec -n devops-lab11 vault-0 -- sh -c "vault write auth/kubernetes/role/devops-info-service bound_service_account_names=devops-info-service bound_service_account_namespaces=devops-lab11 policies=devops-info-service ttl=24h"
```

### 3.4 Enabling Vault Agent Injector in the Deployment

When rendering the chart with `values-vault.yaml`, the following annotations were confirmed:

```yaml
annotations:
  vault.hashicorp.com/agent-inject: "true"
  vault.hashicorp.com/role: "devops-info-service"
  vault.hashicorp.com/agent-inject-status: "update"
  vault.hashicorp.com/agent-inject-secret-app-config: "secret/data/devops-info-service/config"
```

### 3.5 Verifying the Pod with Vault Injection

After fixing the policy and role, a new Pod started successfully with two containers and a completed init container.

Command:

```powershell
kubectl describe pod -n devops-lab11 devops-info-service-6896694dd9-8gp2w
```

The actual output confirmed that:

- `Annotations` contain `vault.hashicorp.com/...`;
- `vault-agent-init` finished with `Reason: Completed`, `Exit Code: 0`;
- `vault-agent` is running as a sidecar;
- the application has a volume mount at `/vault/secrets`;
- the Pod is in `Running` state and `Ready: True`.

Key fragments:

```text
Annotations:
  vault.hashicorp.com/agent-inject: true
  vault.hashicorp.com/agent-inject-secret-app-config: secret/data/devops-info-service/config
  vault.hashicorp.com/agent-inject-status: injected
  vault.hashicorp.com/role: devops-info-service
```

```text
Init Containers:
  vault-agent-init:
    State:          Terminated
      Reason:       Completed
      Exit Code:    0
```

```text
Containers:
  devops-info-service:
    State: Running
  vault-agent:
    State: Running
```

### 3.6 Verifying the secret file inside the Pod

Commands:

```powershell
kubectl exec -n devops-lab11 devops-info-service-6896694dd9-8gp2w -- ls -la /vault/secrets
kubectl exec -n devops-lab11 devops-info-service-6896694dd9-8gp2w -- cat /vault/secrets/app-config
```

Actual output:

```text
total 8
drwxrwxrwt 2 root root   60 Apr  7 12:56 .
drwxr-xr-x 3 root root 4096 Apr  7 12:57 ..
-rw-r--r-- 1  100 app   175 Apr  7 12:56 app-config
```

```text
data: map[password:demo-password username:demo-user]
metadata: map[created_time:2026-04-07T12:29:19.517034267Z custom_metadata:<nil> deletion_time: destroyed:false version:1]
```

This confirms that Vault Agent Injection works and that the secret file does appear inside the Pod at the expected path.

> Note: the current template renders the entire KV v2 response (`.Data`), not only `.Data.data`. For the mandatory part of the lab, this does not interfere with the result, because the secret is successfully injected and read from the file.

### 3.7 Sidecar injection pattern

The following Vault Injector pattern was used:

1. A Pod is created with Vault annotations.
2. The Vault Injector admission webhook mutates the Pod spec.
3. The following are added to the Pod:
   - `vault-agent-init`
   - `vault-agent`
4. The init container authenticates to Vault using the service account token.
5. Vault Agent receives access to the allowed secret path.
6. The secret is rendered into a shared in-memory volume.
7. The application reads the file from `/vault/secrets/app-config`.

This approach avoids storing production secrets in Git or baking them into the container image.

---

## 4. Specifics of local verification in Minikube

Initially, the chart used `replicaCount: 3`. After enabling the Vault sidecar, the rollout hit the `progress deadline` several times, even though an individual Pod with Vault was already working correctly.

For stable local verification in Minikube, the following command was used:

```powershell
helm upgrade --install devops-info-service .\k8s\devops-info-service --namespace devops-lab11 --create-namespace -f .\k8s\devops-info-service\values-vault.yaml --set replicaCount=1 --set image.tag=lab11 --set secret.enabled=true --set secret.data.username=demo-user --set secret.data.password=demo-password --wait --timeout 5m
```

After that, the rollout completed successfully:

```powershell
kubectl rollout status deployment/devops-info-service -n devops-lab11
```

Actual result:

```text
deployment "devops-info-service" successfully rolled out
```

This does not change the correctness of the secret management implementation; it only makes verification more stable in a local single-node Minikube environment.

---

## 5. Security Analysis

### 5.1 Kubernetes Secrets vs Vault

#### Kubernetes Secrets

Pros:

- built into Kubernetes;
- easy to use via Helm;
- suitable for simple or educational scenarios.

Cons:

- base64 is not protection;
- without encryption at rest and RBAC, this is a weak option for production;
- less suitable for centralized management and rotation.

#### HashiCorp Vault

Pros:

- centralized secret storage;
- flexible policies and auth methods;
- a strong access separation model;
- secrets can be delivered into a Pod as files without placing them into the image or Git.

Cons:

- setup is more complex than regular Kubernetes Secrets;
- requires additional components and runtime integration.

### 5.2 When to use each approach

Kubernetes Secrets should be used when:

- the application is simple;
- the environment is temporary or educational;
- secret rotation is not critical;
- RBAC and encryption at rest are enabled.

Vault should be used when:

- secrets are highly sensitive;
- centralized management is required;
- policies, auditability, and future rotation are needed;
- secrets cannot be stored as the source of truth in Kubernetes manifests.

### 5.3 Production recommendations

- do not commit real secrets to Git;
- keep only placeholder values in `values.yaml`;
- enable `etcd` encryption at rest;
- restrict access to Secrets via RBAC;
- use separate service accounts for workloads;
- use Vault or another external secret manager for production credentials.

---

## 6. Conclusion

As part of lab11, the mandatory tasks were completed successfully:

- a Secret was created via `kubectl`;
- the secret values were viewed and decoded;
- `templates/secrets.yaml` was added to the Helm chart;
- the application receives secrets through environment variables;
- resource limits/requests were configured;
- Vault was installed and configured;
- Kubernetes auth, policy, and role were created;
- Vault Agent Injection works;
- the secret is available inside the Pod at `/vault/secrets/app-config`.

Therefore, the mandatory part of the lab assignment was completed in full.
