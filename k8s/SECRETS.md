# Lab 11 — Kubernetes Secrets & HashiCorp Vault

В этой лабораторной работе были реализованы два подхода к управлению секретами:

- нативные Kubernetes Secrets, создаваемые вручную и через Helm chart;
- HashiCorp Vault Agent Injector для файловой инъекции секрета в Pod.

**Bonus task не выполнялся.**

---

## 1. Kubernetes Secrets

### 1.1 Создание секрета через kubectl

Secret был создан императивной командой:

```powershell
kubectl create secret generic app-credentials --from-literal=username=demo-user --from-literal=password=demo-password -n devops-lab11
```

### 1.2 Просмотр секрета в YAML

Команда:

```powershell
kubectl get secret app-credentials -n devops-lab11 -o yaml
```

Полученный вывод:

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

### 1.3 Декодирование значений

В PowerShell base64-значения были декодированы так:

```powershell
[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String((kubectl get secret app-credentials -n devops-lab11 -o jsonpath='{.data.username}')))
[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String((kubectl get secret app-credentials -n devops-lab11 -o jsonpath='{.data.password}')))
```

Результат:

```text
demo-user
demo-password
```

### 1.4 Base64 encoding vs encryption

`Secret` в Kubernetes по умолчанию хранит значения в YAML в виде base64. Это **encoding**, а не encryption:

- **encoding** меняет представление данных, но не защищает их;
- любой пользователь, который может прочитать Secret через API, может декодировать значения;
- base64 нельзя считать механизмом защиты секрета.

### 1.5 Безопасность: encrypted at rest и etcd encryption

Kubernetes Secrets **не считаются безопасно зашифрованными только потому, что их значения представлены в base64**. Для production-кластеров нужно отдельно включать **encryption at rest** для `etcd`.

`etcd encryption` — это механизм control plane, который шифрует чувствительные ресурсы (прежде всего Secrets) перед записью в `etcd`.

Его рекомендуется включать всегда, если:

- кластер не является одноразовой учебной средой;
- в Secret хранятся токены, пароли, API keys, сертификаты;
- к control plane или backup-ам `etcd` имеют доступ другие администраторы;
- есть требования безопасности или комплаенса.

Также для production необходимы:

- RBAC-ограничения на чтение Secret;
- отдельные service account для workloads;
- использование внешнего secret manager, например Vault.

---

## 2. Helm Secret Integration

### 2.1 Изменения в Helm chart

В chart были добавлены и изменены следующие файлы:

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

Также были добавлены Vault-related файлы:

```text
k8s/vault/
├── app-policy.hcl
└── configure-vault.sh
```

### 2.2 Secret template

В chart был добавлен файл:

```text
k8s/devops-info-service/templates/secrets.yaml
```

Его содержимое:

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

Использование `stringData` упрощает передачу plaintext-значений через Helm: Kubernetes сам кодирует их в base64 при создании Secret.

### 2.3 Подключение Secret в Deployment

Deployment был обновлён так, чтобы получать переменные окружения из Secret через `envFrom`:

```yaml
envFrom:
  - secretRef:
      name: devops-info-service-secret
```

Также для предсказуемой привязки Vault role был добавлен отдельный `ServiceAccount`.

### 2.4 Resource limits и requests

После рендера chart были видны следующие значения:

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

- **requests** — минимальные ресурсы, которые Kubernetes учитывает при планировании Pod;
- **limits** — верхняя граница, которую контейнер не должен превышать.

Для небольшого Flask-сервиса эти значения подходят для локального Minikube и демонстрируют базовые best practices.

### 2.5 Проверка Helm Secret Integration

Рендер chart:

```powershell
helm template devops-info-service .\k8s\devops-info-service --namespace devops-lab11 --set image.tag=lab11 --set secret.enabled=true --set secret.data.username=demo-user --set secret.data.password=demo-password
```

Из результата было подтверждено, что chart рендерит:

- `ServiceAccount`
- `Secret`
- `Deployment` с `serviceAccountName`
- `envFrom.secretRef`

Фрагменты отрендеренного манифеста:

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

Установка chart:

```powershell
helm upgrade --install devops-info-service .\k8s\devops-info-service --namespace devops-lab11 --create-namespace --set image.tag=lab11 --set secret.enabled=true --set secret.data.username=demo-user --set secret.data.password=demo-password --wait --timeout 5m
```

### 2.6 Проверка Secret в кластере

Команда:

```powershell
kubectl get secret devops-info-service-secret -n devops-lab11 -o yaml
```

Фактический вывод:

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

### 2.7 Проверка env vars в Pod

Имя Pod:

```powershell
$POD = kubectl get pods -n devops-lab11 -l app.kubernetes.io/instance=devops-info-service -o jsonpath='{.items[0].metadata.name}'
```

Проверка переменных окружения:

```powershell
kubectl exec -n devops-lab11 $POD -- printenv | Select-String '^(username|password)='
```

Фактический вывод:

```text
password=demo-password
username=demo-user
```

Проверка описания Pod:

```powershell
kubectl describe pod -n devops-lab11 $POD
```

Из `describe pod` было подтверждено:

- используется `Service Account: devops-info-service`;
- Secret подключён как `Environment Variables from: devops-info-service-secret Secret Optional: false`;
- сами значения секрета в `kubectl describe pod` не выводятся открытым текстом.

---

## 3. HashiCorp Vault Integration

### 3.1 Установка Vault через Helm

Vault был установлен в dev mode:

```powershell
helm repo add hashicorp https://helm.releases.hashicorp.com
helm repo update
helm upgrade --install vault hashicorp/vault --namespace devops-lab11 --create-namespace --set server.dev.enabled=true --set injector.enabled=true --wait --timeout 5m
```

Проверка Pod:

```powershell
kubectl get pods -n devops-lab11
```

После старта были доступны:

- `vault-0`
- `vault-agent-injector-*`

Проверка статуса Vault:

```powershell
kubectl exec -n devops-lab11 vault-0 -- vault status
```

Фактический вывод:

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

### 3.2 Включение KV и запись секрета

Был использован KV secrets engine и создан секрет по пути:

```text
secret/devops-info-service/config
```

Команды:

```powershell
kubectl exec -n devops-lab11 vault-0 -- sh -c "vault kv put secret/devops-info-service/config username=demo-user password=demo-password"
kubectl exec -n devops-lab11 vault-0 -- sh -c "vault kv get secret/devops-info-service/config"
```

Подтверждённый вывод:

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

### 3.3 Kubernetes auth, policy и role

Была включена аутентификация Kubernetes:

```powershell
kubectl exec -n devops-lab11 vault-0 -- sh -c "vault auth enable kubernetes || true"
kubectl exec -n devops-lab11 vault-0 -- sh -c 'vault write auth/kubernetes/config kubernetes_host="https://kubernetes.default.svc:443"'
```

Для приложения была создана policy с доступом к KV v2 path:

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

Эта policy была загружена в Vault и прочитана обратно:

```powershell
kubectl exec -n devops-lab11 vault-0 -- sh -c "vault policy read devops-info-service"
```

Фактический вывод:

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

Роль была привязана к service account приложения:

```powershell
kubectl exec -n devops-lab11 vault-0 -- sh -c "vault write auth/kubernetes/role/devops-info-service bound_service_account_names=devops-info-service bound_service_account_namespaces=devops-lab11 policies=devops-info-service ttl=24h"
```

### 3.4 Включение Vault Agent Injector в Deployment

При рендере chart с `values-vault.yaml` были подтверждены аннотации:

```yaml
annotations:
  vault.hashicorp.com/agent-inject: "true"
  vault.hashicorp.com/role: "devops-info-service"
  vault.hashicorp.com/agent-inject-status: "update"
  vault.hashicorp.com/agent-inject-secret-app-config: "secret/data/devops-info-service/config"
```

### 3.5 Проверка Pod с Vault Injection

После исправления policy и роли новый Pod успешно поднялся с двумя контейнерами и завершённым init-container.

Команда:

```powershell
kubectl describe pod -n devops-lab11 devops-info-service-6896694dd9-8gp2w
```

Из фактического вывода подтверждено:

- `Annotations` содержат `vault.hashicorp.com/...`;
- `vault-agent-init` завершился с `Reason: Completed`, `Exit Code: 0`;
- `vault-agent` работает как sidecar;
- приложение имеет volume mount `/vault/secrets`;
- Pod имеет состояние `Running` и `Ready: True`.

Ключевые фрагменты:

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

### 3.6 Проверка файла с секретом внутри Pod

Команды:

```powershell
kubectl exec -n devops-lab11 devops-info-service-6896694dd9-8gp2w -- ls -la /vault/secrets
kubectl exec -n devops-lab11 devops-info-service-6896694dd9-8gp2w -- cat /vault/secrets/app-config
```

Фактический вывод:

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

Это подтверждает, что Vault Agent Injection работает и файл с секретом действительно появляется в Pod по ожидаемому пути.

> Примечание: текущий шаблон рендерит весь KV v2 response (`.Data`), а не только `.Data.data`. Для обязательной части лабораторной это не мешает, так как секрет успешно инжектируется и читается из файла.

### 3.7 Sidecar injection pattern

Использованный паттерн работы Vault Injector:

1. Pod создаётся с Vault annotations.
2. Admission webhook Vault Injector модифицирует Pod spec.
3. В Pod добавляются:
   - `vault-agent-init`
   - `vault-agent`
4. Init container аутентифицируется в Vault через service account token.
5. Vault Agent получает разрешённый secret path.
6. Секрет рендерится в общий in-memory volume.
7. Приложение читает файл из `/vault/secrets/app-config`.

Такой подход позволяет не хранить production-секреты в Git и не вшивать их в контейнерный образ.

---

## 4. Особенности локальной проверки в Minikube

Изначально chart использовал `replicaCount: 3`. После включения Vault sidecar rollout несколько раз упирался в `progress deadline`, хотя отдельный Pod с Vault уже работал корректно.

Для стабильной локальной проверки в Minikube был использован:

```powershell
helm upgrade --install devops-info-service .\k8s\devops-info-service --namespace devops-lab11 --create-namespace -f .\k8s\devops-info-service\values-vault.yaml --set replicaCount=1 --set image.tag=lab11 --set secret.enabled=true --set secret.data.username=demo-user --set secret.data.password=demo-password --wait --timeout 5m
```

После этого rollout завершился успешно:

```powershell
kubectl rollout status deployment/devops-info-service -n devops-lab11
```

Фактический результат:

```text
deployment "devops-info-service" successfully rolled out
```

Это не меняет корректность реализации secret management, а только делает проверку устойчивой на локальном одноузловом Minikube.

---

## 5. Security Analysis

### 5.1 Kubernetes Secrets vs Vault

#### Kubernetes Secrets

Плюсы:

- встроены в Kubernetes;
- просто использовать через Helm;
- подходят для простых или учебных сценариев.

Минусы:

- base64 не является защитой;
- без encryption at rest и RBAC это слабый вариант для production;
- хуже подходят для централизованного управления и ротации.

#### HashiCorp Vault

Плюсы:

- централизованное хранение секретов;
- гибкие policy и auth methods;
- хорошая модель разделения доступа;
- можно доставлять секреты в Pod как файлы, не помещая их в image или Git.

Минусы:

- настройка сложнее, чем у обычных Kubernetes Secrets;
- требует дополнительных компонентов и runtime integration.

### 5.2 Когда использовать каждый подход

Kubernetes Secrets стоит использовать, когда:

- приложение простое;
- окружение временное или учебное;
- ротация секретов не является критичной;
- используется RBAC и encryption at rest.

Vault стоит использовать, когда:

- секреты высокочувствительные;
- требуется централизованное управление;
- нужны policy, auditability и future rotation;
- нельзя хранить секреты как source of truth в Kubernetes manifests.

### 5.3 Production recommendations

- не коммитить реальные секреты в Git;
- хранить в `values.yaml` только placeholder values;
- включать `etcd` encryption at rest;
- ограничивать доступ к Secrets через RBAC;
- использовать отдельные service account для workloads;
- применять Vault или другой внешний secret manager для production credentials.

---

## 6. Итог

В рамках lab11 были успешно выполнены обязательные задания:

- Secret создан через `kubectl`;
- значения секрета просмотрены и декодированы;
- в Helm chart добавлен `templates/secrets.yaml`;
- приложение получает секреты через environment variables;
- resource limits/requests настроены;
- Vault установлен и настроен;
- Kubernetes auth, policy и role созданы;
- Vault Agent Injection работает;
- секрет доступен внутри Pod по пути `/vault/secrets/app-config`.

Следовательно, обязательная часть лабораторной работы выполнена полностью.
