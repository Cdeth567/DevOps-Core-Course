# Lab 12 — ConfigMaps & Persistent Volumes

## Overview

This lab extends the application and Helm chart with:
- a persistent file-based visit counter
- ConfigMaps for file-based and environment-based configuration
- a PersistentVolumeClaim for durable storage

Bonus Task was **not implemented**, as requested.

---

## 1. Application changes

### Visits counter implementation

The Flask application was updated to persist the number of visits to the root endpoint.

Implemented behavior:
- `GET /` increments the counter and saves it to a file
- `GET /visits` returns the current persisted counter value
- the counter is loaded from disk on startup
- file writes are protected with `threading.Lock`
- writes are atomic via a temporary file and `os.replace(...)`

Default counter file path:
```text
/data/visits
```

The application uses the `VISITS_FILE` environment variable, with `/data/visits` as the default.

### New endpoint

A new endpoint was added:

- `GET /visits` — returns the current visit counter value from persisted storage

Example response:
```json
{
  "storage": "/data/visits",
  "visits": 7
}
```

---

## 2. Local Docker verification

### Docker Compose configuration

A `docker-compose.yml` file was added to `app_python/` with a bind mount for the visits directory:

```yaml
services:
  devops-info-service:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: devops-info-service
    environment:
      HOST: 0.0.0.0
      PORT: 5000
      DEBUG: "False"
      VISITS_FILE: /data/visits
    ports:
      - "5000:5000"
    volumes:
      - ./data:/data
    restart: unless-stopped
```

### Local verification steps

Commands used on Windows PowerShell:
```powershell
docker compose up -d --build
Start-Sleep -Seconds 5

Invoke-RestMethod http://127.0.0.1:5000/
Invoke-RestMethod http://127.0.0.1:5000/
Invoke-RestMethod http://127.0.0.1:5000/visits

Get-Content .\data\visits

docker compose restart
Start-Sleep -Seconds 5

Invoke-RestMethod http://127.0.0.1:5000/visits
Get-Content .\data\visits
```

### Local verification results

Output of `Invoke-RestMethod http://127.0.0.1:5000/visits`:
```text
storage      visits
-------      ------
/data/visits      7
```

Content of the persisted file:
```text
7
```

After `docker compose restart`, the value was still preserved.

Output of `Invoke-RestMethod http://127.0.0.1:5000/visits` after restart:
```text
storage      visits
-------      ------
/data/visits      7
```

Content of the file after restart:
```text
7
```

### Unit tests

The application test suite passed successfully:

```text
7 passed in 0.35s
```

### Conclusion for local testing

The visit counter:
- is incremented on each request to `/`
- is stored in a file
- survives container restart when a volume is mounted

---

## 3. ConfigMap implementation

### Files added

The following files were added to the Helm chart:
- `k8s/devops-info-service/files/config.json`
- `k8s/devops-info-service/templates/configmap.yaml`

### File-based ConfigMap

The chart contains a dedicated JSON configuration file in `files/config.json` and renders it into a ConfigMap with Helm.

Template structure:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "devops-info-service.configFileConfigMapName" . }}
  labels:
    {{- include "devops-info-service.labels" . | nindent 4 }}
data:
  {{ .Values.config.fileName }}: |-
{{ tpl (.Files.Get "files/config.json") . | indent 4 }}
```

### Environment ConfigMap

A second ConfigMap provides environment variables to the container:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "devops-info-service.envConfigMapName" . }}
  labels:
    {{- include "devops-info-service.labels" . | nindent 4 }}
data:
  APP_ENV: {{ .Values.environment | quote }}
  LOG_LEVEL: {{ .Values.logLevel | quote }}
  FEATURE_VISITS: {{ ternary "true" "false" .Values.featureFlags.visitsCounter | quote }}
  FEATURE_METRICS: {{ ternary "true" "false" .Values.featureFlags.prometheusMetrics | quote }}
  FEATURE_READINESS: {{ ternary "true" "false" .Values.featureFlags.readinessProbe | quote }}
  CONFIG_PATH: {{ printf "%s/%s" .Values.config.mountPath .Values.config.fileName | quote }}
  VISITS_FILE: {{ printf "%s/visits" .Values.persistence.mountPath | quote }}
```

### Mounting ConfigMap as a file

The Deployment mounts the file-based ConfigMap to `/config`:

```yaml
volumeMounts:
  - name: config-volume
    mountPath: /config
    readOnly: true
```

```yaml
volumes:
  - name: config-volume
    configMap:
      name: {{ include "devops-info-service.configFileConfigMapName" . }}
      items:
        - key: config.json
          path: config.json
```

As a result, the file is available inside the pod at:

```text
/config/config.json
```

### Injecting ConfigMap as environment variables

The Deployment also uses `envFrom`:

```yaml
envFrom:
  - configMapRef:
      name: {{ include "devops-info-service.envConfigMapName" . }}
```

Injected variables:
- `APP_ENV`
- `LOG_LEVEL`
- `FEATURE_VISITS`
- `FEATURE_METRICS`
- `FEATURE_READINESS`
- `CONFIG_PATH`
- `VISITS_FILE`

### Kubernetes verification output

The chart was rendered successfully with:

```powershell
helm template lab12 .\k8s\devops-info-service -f .\k8s\devops-info-service\values-dev.yaml
```

The application was deployed to Minikube with:

```powershell
helm upgrade --install lab12 .\k8s\devops-info-service `
  -n devops `
  -f .\k8s\devops-info-service\values-dev.yaml
```

Deployment rollout result:
```text
deployment "lab12-devops-info-service" successfully rolled out
```

Output of `kubectl get configmap,pvc -n devops`:
```text
NAME                                         DATA   AGE
configmap/kube-root-ca.crt                   1      43m
configmap/lab12-devops-info-service-config   1      43m
configmap/lab12-devops-info-service-env      7      43m

NAME                                                   STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
persistentvolumeclaim/lab12-devops-info-service-data   Bound    pvc-34f77d7e-46ad-459b-a4c5-0dafb3fb7b55   100Mi      RWO            standard       <unset>                 43m
```

Output of `kubectl exec -n devops $POD -- cat /config/config.json`:
```json
{
  "applicationName": "lab12-devops-info-service",
  "environment": "dev",
  "features": {
    "visitsCounter": true,
    "prometheusMetrics": true,
    "readinessProbe": true
  },
  "settings": {
    "port": 5000,
    "configPath": "/config/config.json",
    "visitsFile": "/data/visits",
    "logLevel": "DEBUG"
  }
}
```

Environment variable verification:
```text
kubectl exec -n devops $POD -- printenv APP_ENV
dev

kubectl exec -n devops $POD -- printenv LOG_LEVEL
DEBUG

kubectl exec -n devops $POD -- printenv FEATURE_VISITS
true

kubectl exec -n devops $POD -- printenv FEATURE_METRICS
true

kubectl exec -n devops $POD -- printenv FEATURE_READINESS
true

kubectl exec -n devops $POD -- printenv CONFIG_PATH
/config/config.json

kubectl exec -n devops $POD -- printenv VISITS_FILE
/data/visits
```

### Minikube note

For local Kubernetes testing on Windows with the Minikube Docker driver:
- the application image was loaded into Minikube with `minikube image load`
- `kubectl port-forward` was used for service access during runtime verification

---

## 4. Persistent Volume implementation

### PVC template

A PersistentVolumeClaim template was added in:
- `k8s/devops-info-service/templates/pvc.yaml`

Template:
```yaml
{{- if .Values.persistence.enabled }}
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: {{ include "devops-info-service.pvcName" . }}
  labels:
    {{- include "devops-info-service.labels" . | nindent 4 }}
spec:
  accessModes:
    - {{ .Values.persistence.accessMode }}
  resources:
    requests:
      storage: {{ .Values.persistence.size }}
  {{- if .Values.persistence.storageClass }}
  storageClassName: {{ .Values.persistence.storageClass | quote }}
  {{- end }}
{{- end }}
```

### Persistence values

The chart uses:
```yaml
persistence:
  enabled: true
  accessMode: ReadWriteOnce
  size: 100Mi
  storageClass: ""
  mountPath: /data
```

Explanation:
- `enabled: true` creates and mounts the PVC
- `ReadWriteOnce` is suitable for a single writing pod
- `100Mi` is enough for the simple counter file
- `storageClass: ""` uses the cluster default StorageClass
- `/data` is the path used by the application for `/data/visits`

### Mounting the PVC in the Deployment

The Deployment mounts the PVC like this:

```yaml
volumeMounts:
  - name: data-volume
    mountPath: /data
```

```yaml
volumes:
  - name: data-volume
    persistentVolumeClaim:
      claimName: {{ include "devops-info-service.pvcName" . }}
```

This ensures the visits counter is stored on persistent storage instead of inside the container filesystem.

### Persistence verification

For service access, `kubectl port-forward` was used:

```powershell
kubectl port-forward -n devops service/lab12-devops-info-service 8080:80
```

Before pod deletion:

Output of `Invoke-RestMethod http://127.0.0.1:8080/visits`:
```text
storage      visits
-------      ------
/data/visits      2
```

The pod serving the requests before deletion:
```text
lab12-devops-info-service-64c8d79496-5spbv
```

The pod was then deleted:
```powershell
kubectl delete pod -n devops lab12-devops-info-service-64c8d79496-5spbv
```

Output:
```text
pod "lab12-devops-info-service-64c8d79496-5spbv" deleted from devops namespace
```

A new pod was created by the Deployment:
```text
lab12-devops-info-service-64c8d79496-hqbpm
```

Output of `kubectl exec -n devops $NEW_POD -- cat /data/visits`:
```text
2
```

### Persistence conclusion

The visit counter value survived pod deletion and recreation.
This confirms that the counter is stored on the PVC and not lost when the pod is replaced.

---

## 5. Values configuration

### `values.yaml`
Main defaults include:
- persistence enabled
- ConfigMap mount path `/config`
- config file name `config.json`

### `values-dev.yaml`
Development profile includes:
- `environment: dev`
- `replicaCount: 1`
- `logLevel: DEBUG`

For Minikube verification, the development values were overridden to use the locally built image:
```yaml
image:
  repository: app_python-devops-info-service
  tag: latest
  pullPolicy: IfNotPresent
```

The service was exposed as:
```yaml
service:
  type: NodePort
  nodePort: 30081
```

### `values-prod.yaml`
Production profile includes:
- `environment: prod`
- `replicaCount: 3`
- `logLevel: WARN`

---

## 6. ConfigMap vs Secret

### When to use ConfigMap

Use a ConfigMap for:
- non-sensitive configuration
- feature flags
- environment names
- application settings
- file-based configuration such as JSON or YAML

Examples from this lab:
- `APP_ENV`
- `LOG_LEVEL`
- `FEATURE_VISITS`
- `CONFIG_PATH`
- `config.json`

### When to use Secret

Use a Secret for:
- passwords
- tokens
- API keys
- database credentials
- any confidential value

Examples:
- database password
- Vault token
- access token for external services

### Key differences

| Aspect | ConfigMap | Secret |
|-------|-----------|--------|
| Purpose | Non-sensitive config | Sensitive data |
| Typical data | app settings, feature flags | passwords, tokens, credentials |
| Encoding | Plain text in YAML | Base64-encoded in manifests |
| Use in pods | env vars or mounted files | env vars or mounted files |
| Security expectation | not confidential | should be treated as confidential |

Important note:
- ConfigMaps are not intended for secrets
- Secrets should be used for confidential values

---

## 7. Summary

All required non-bonus tasks were implemented and verified.

### Task 1
- visits counter implemented
- `/visits` endpoint added
- counter stored in a file
- Docker Compose volume configured
- local persistence verified
- README updated

### Task 2
- `files/config.json` created
- file-based ConfigMap implemented
- environment ConfigMap implemented
- ConfigMap mounted as `/config/config.json`
- environment variables injected successfully
- Kubernetes verification completed

### Task 3
- PVC created
- PVC mounted to `/data`
- application writes counter to `/data/visits`
- PVC is `Bound`
- data survived pod deletion and recreation

### Task 4
- documentation completed in `k8s/CONFIGMAPS.md`

The lab requirements for ConfigMaps and Persistent Volumes were completed successfully without the Bonus Task.
