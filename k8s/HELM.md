# Lab 10 — Helm Package Manager

## 1. Chart Overview

For Lab 10, the Kubernetes manifests from Lab 9 were converted into a reusable Helm chart located in `k8s/devops-info-service`.

### Chart structure

```text
k8s/devops-info-service/
├── Chart.yaml
├── values.yaml
├── values-dev.yaml
├── values-prod.yaml
├── .helmignore
├── charts/
└── templates/
    ├── _helpers.tpl
    ├── deployment.yaml
    ├── service.yaml
    ├── NOTES.txt
    └── hooks/
        ├── pre-install-job.yaml
        └── post-install-job.yaml
```

### Key template files and their purpose

- `Chart.yaml` — chart metadata: `apiVersion`, `name`, `description`, `type`, `version`, `appVersion`
- `values.yaml` — default configuration for the application and chart
- `values-dev.yaml` — overrides for the development environment
- `values-prod.yaml` — overrides for the production environment
- `templates/_helpers.tpl` — helper templates for names, full names, selector labels, common labels, and chart labels
- `templates/deployment.yaml` — templated Deployment created from the Lab 9 `deployment.yml`
- `templates/service.yaml` — templated Service created from the Lab 9 `service.yml`
- `templates/hooks/pre-install-job.yaml` — pre-install validation job
- `templates/hooks/post-install-job.yaml` — post-install smoke test job
- `templates/NOTES.txt` — post-install instructions shown by Helm after install/upgrade

### Values organization strategy

The chart values are grouped by responsibility:

- `image` — repository, tag, and image pull policy
- `replicaCount` — number of application replicas
- `container` — container port
- `service` — service type, port, target port, and optional `nodePort`
- `resources` — CPU and memory requests/limits
- `appConfig` — environment variables passed to the application
- `startupProbe`, `readinessProbe`, `livenessProbe` — health checks
- `hooks` — configuration for hook images and hook behavior
- `podSecurityContext` and `containerSecurityContext` — security hardening settings

This organization makes the templates reusable and allows environment-specific customization without duplicating manifests.

---

## 2. Configuration Guide

### Important values and their purpose

| Value | Purpose |
|---|---|
| `replicaCount` | Number of replicas for the Deployment |
| `image.repository` | Docker image repository |
| `image.tag` | Docker image tag |
| `image.pullPolicy` | Pull policy for the container image |
| `container.port` | Container port exposed by the application |
| `service.type` | Kubernetes Service type (`NodePort` or `LoadBalancer`) |
| `service.port` | Service port |
| `service.targetPort` | Target port in the container |
| `service.nodePort` | Fixed NodePort value for dev profile |
| `resources.requests` | Minimal CPU and memory required by the container |
| `resources.limits` | Maximum CPU and memory allowed for the container |
| `startupProbe` | Startup health check |
| `readinessProbe` | Readiness health check |
| `livenessProbe` | Liveness health check |
| `appConfig.serviceVersion` | Application version value passed as env var |
| `appConfig.serviceDescription` | Application description passed as env var |
| `hooks.preInstall.*` | Settings for pre-install validation job |
| `hooks.postInstall.*` | Settings for post-install smoke test job |

### Environment customization strategy

Two separate values files were created for different environments.

#### Development environment — `values-dev.yaml`

Development profile uses:

- `replicaCount: 1`
- smaller CPU and memory limits/requests
- `service.type: NodePort`
- fixed `nodePort: 30080`
- `serviceVersion: 1.0.0-dev`
- `serviceDescription: Development profile for DevOps Info Service`
- faster readiness/liveness settings

#### Production environment — `values-prod.yaml`

Production profile uses:

- `replicaCount: 3`
- increased CPU and memory limits/requests
- `service.type: LoadBalancer`
- `nodePort: null`
- `serviceVersion: 1.0.0-prod`
- `serviceDescription: Production profile for DevOps Info Service`
- more conservative readiness/liveness timings

### Example installations with different configurations

#### Render templates locally

```bash
helm template devops-info-service ./k8s/devops-info-service
helm template devops-info-service ./k8s/devops-info-service -f ./k8s/devops-info-service/values-dev.yaml
helm template devops-info-service ./k8s/devops-info-service -f ./k8s/devops-info-service/values-prod.yaml
```

#### Install development profile

```bash
helm upgrade --install devops-info-service ./k8s/devops-info-service \
  --namespace devops-lab10 \
  --create-namespace \
  -f ./k8s/devops-info-service/values-dev.yaml \
  --wait --timeout 5m
```

#### Upgrade the same release to production profile

```bash
helm upgrade devops-info-service ./k8s/devops-info-service \
  --namespace devops-lab10 \
  -f ./k8s/devops-info-service/values-prod.yaml \
  --wait --timeout 5m
```

#### Override one value manually

```bash
helm upgrade --install devops-info-service ./k8s/devops-info-service \
  --namespace devops-lab10 \
  --create-namespace \
  -f ./k8s/devops-info-service/values-dev.yaml \
  --set replicaCount=2 \
  --wait --timeout 5m
```

---

## 3. Hook Implementation

Two Helm hook Jobs were implemented.

### Pre-install hook

File:

```text
k8s/devops-info-service/templates/hooks/pre-install-job.yaml
```

Purpose:

- validates that the critical chart values are present before installation starts
- checks that image repository, image tag, and service port are defined

Hook annotations:

```yaml
"helm.sh/hook": pre-install
"helm.sh/hook-weight": "-5"
"helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
```

### Post-install hook

File:

```text
k8s/devops-info-service/templates/hooks/post-install-job.yaml
```

Purpose:

- performs a simple smoke test after the application is installed
- checks `/ready` through the Service using BusyBox and `wget`
- retries several times before failing

Hook annotations:

```yaml
"helm.sh/hook": post-install
"helm.sh/hook-weight": "5"
"helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
```

### Hook execution order and weights

The chart uses the following execution order:

1. Helm renders templates.
2. `pre-install` hook runs first because it has weight `-5`.
3. Main resources are created.
4. Helm waits for resources to become ready because installation was done with `--wait`.
5. `post-install` hook runs after the main resources are available because it has weight `5`.
6. On success, hook Jobs are deleted automatically.

### Deletion policies explanation

`before-hook-creation,hook-succeeded` means:

- old hook resources are removed before the hook is recreated on the next install/upgrade
- successful hook Jobs are automatically deleted after completion

This behavior was confirmed during testing: after successful execution, `kubectl get jobs -n devops-lab10` showed no remaining Job resources.

---

## 4. Installation Evidence

This section documents the actual commands and observed outputs from the completed lab execution.

### Helm installation and exploration evidence

Helm was installed and verified successfully:

```text
helm version
version.BuildInfo{Version:"v4.1.3", GitCommit:"c94d381b03be117e7e57908edbf642104e00eb8f", GitTreeState:"clean", GoVersion:"go1.25.8", KubeClientVersion:"v1.35"}
```

Repository configuration:

```text
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
"prometheus-community" has been added to your repositories

helm repo update
...Successfully got an update from the "prometheus-community" chart repository
Update Complete. ⎈Happy Helming!⎈
```

Public chart exploration:

```text
helm show chart prometheus-community/prometheus
apiVersion: v2
name: prometheus
type: application
version: 28.14.1
appVersion: v3.10.0
...
```

### Validation evidence

Linting succeeded:

```text
helm lint .\k8s\devops-info-service
==> Linting .\k8s\devops-info-service
[INFO] Chart.yaml: icon is recommended

1 chart(s) linted, 0 chart(s) failed
```

Dry-run and template rendering succeeded:

- `helm template devops-info-service .\k8s\devops-info-service`
- `helm install --dry-run --debug test-release .\k8s\devops-info-service`

The dry-run output confirmed that:

- `Deployment` and `Service` are rendered correctly
- `pre-install` and `post-install` hook Jobs are rendered
- values are injected correctly
- `SERVICE_NAME`, `SERVICE_VERSION`, `SERVICE_DESCRIPTION` are templated
- health probes remain enabled and configurable

### Development environment deployment evidence

Minikube cluster was started successfully:

```text
minikube start
... Done! kubectl is now configured to use "minikube" cluster and "default" namespace by default

kubectl get nodes
NAME       STATUS   ROLES           AGE     VERSION
minikube   Ready    control-plane   7d23h   v1.35.1
```

#### First install issue and resolution

The first dev installation attempt failed because `NodePort 30080` was already occupied by the old Lab 9 service:

```text
Error: Service "devops-info-service" is invalid: spec.ports[0].nodePort: Invalid value: 30080: provided port is already allocated
```

The conflicting service was identified and removed:

```text
kubectl get svc -A | findstr 30080
devops-lab09   devops-info-service   NodePort   ...   80:30080/TCP

kubectl delete svc devops-info-service -n devops-lab09
service "devops-info-service" deleted from devops-lab09 namespace
```

After that, the dev installation completed successfully:

```text
helm upgrade --install devops-info-service .\k8s\devops-info-service \
  --namespace devops-lab10 \
  --create-namespace \
  -f .\k8s\devops-info-service\values-dev.yaml \
  --wait --timeout 5m

STATUS: deployed
REVISION: 1
DESCRIPTION: Install complete
```

Confirmed dev release state:

```text
helm list -n devops-lab10
NAME                    NAMESPACE       REVISION   STATUS    CHART                      APP VERSION
devops-info-service     devops-lab10    1          deployed  devops-info-service-0.1.0 1.0.0-k8s
```

Deployed resources in dev:

```text
kubectl get all -n devops-lab10
pod/devops-info-service-6f49d858fb-q9lr4     1/1 Running
service/devops-info-service                  NodePort   80:30080/TCP
deployment.apps/devops-info-service          1/1
replicaset.apps/devops-info-service-6f49d858fb  1/1
```

`kubectl describe deployment devops-info-service -n devops-lab10` confirmed:

- `Replicas: 1 desired | 1 updated | 1 total | 1 available | 0 unavailable`
- image: `cdeth567/devops-info-service:lab09`
- limits: `cpu 100m`, `memory 128Mi`
- requests: `cpu 50m`, `memory 64Mi`
- `SERVICE_VERSION=1.0.0-dev`
- `SERVICE_DESCRIPTION=Development profile for DevOps Info Service`

`kubectl describe service devops-info-service -n devops-lab10` confirmed:

- `Type: NodePort`
- `Port: 80/TCP`
- `NodePort: 30080/TCP`
- valid endpoint pointing to the application pod

### Hook execution evidence

The watch command showed successful execution of both hooks:

```text
kubectl get jobs -n devops-lab10 -w
...
devops-info-service-pre-install    Complete   1/1
devops-info-service-post-install   Complete   1/1
```

Event log confirmed both hook Jobs were created and completed:

```text
kubectl get events -n devops-lab10 --sort-by=.metadata.creationTimestamp
...
Normal  SuccessfulCreate  job/devops-info-service-pre-install   Created pod: ...
Normal  Completed         job/devops-info-service-pre-install   Job completed
Normal  SuccessfulCreate  job/devops-info-service-post-install  Created pod: ...
Normal  Completed         job/devops-info-service-post-install  Job completed
```

After successful completion, the Jobs were removed automatically:

```text
kubectl get jobs -n devops-lab10
No resources found in devops-lab10 namespace.
```

### Production environment deployment evidence

The same release was upgraded to the production profile:

```text
helm upgrade devops-info-service .\k8s\devops-info-service \
  --namespace devops-lab10 \
  -f .\k8s\devops-info-service\values-prod.yaml \
  --wait --timeout 5m

STATUS: deployed
REVISION: 2
DESCRIPTION: Upgrade complete
```

Applied production values:

```text
helm get values devops-info-service -n devops-lab10
replicaCount: 3
service:
  type: LoadBalancer
  nodePort: null
resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 200m
    memory: 256Mi
appConfig:
  serviceVersion: 1.0.0-prod
  serviceDescription: Production profile for DevOps Info Service
```

Cluster state after upgrade:

```text
kubectl get all -n devops-lab10
service/devops-info-service   LoadBalancer   ...   80:30080/TCP
deployment.apps/devops-info-service   3/3
replicaset.apps/devops-info-service-57468b586f   3/3
```

`kubectl describe deployment devops-info-service -n devops-lab10` confirmed:

- `Replicas: 3 desired | 3 updated | 3 total | 3 available | 0 unavailable`
- limits: `cpu 500m`, `memory 512Mi`
- requests: `cpu 200m`, `memory 256Mi`
- `SERVICE_VERSION=1.0.0-prod`
- `SERVICE_DESCRIPTION=Production profile for DevOps Info Service`

`kubectl describe service devops-info-service -n devops-lab10` confirmed:

- `Type: LoadBalancer`
- `NodePort: 30080/TCP`
- three pod endpoints behind the service

`EXTERNAL-IP` stayed `<pending>`, which is expected in Minikube without `minikube tunnel`.

### Release history evidence

```text
helm history devops-info-service -n devops-lab10
REVISION  UPDATED                    STATUS       DESCRIPTION
1         Install time               superseded   Install complete
2         Upgrade time               deployed     Upgrade complete
```

---

## 5. Operations

### Installation commands used

```bash
helm version
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm show chart prometheus-community/prometheus

helm lint ./k8s/devops-info-service
helm template devops-info-service ./k8s/devops-info-service
helm install --dry-run --debug test-release ./k8s/devops-info-service

minikube start
kubectl get nodes

helm upgrade --install devops-info-service ./k8s/devops-info-service \
  --namespace devops-lab10 \
  --create-namespace \
  -f ./k8s/devops-info-service/values-dev.yaml \
  --wait --timeout 5m
```

### How to upgrade a release

```bash
helm upgrade devops-info-service ./k8s/devops-info-service \
  --namespace devops-lab10 \
  -f ./k8s/devops-info-service/values-prod.yaml \
  --wait --timeout 5m
```

### How to rollback

Rollback from prod to revision 1 was tested successfully:

```text
helm rollback devops-info-service 1 -n devops-lab10 --wait --timeout 5m
Rollback was a success! Happy Helming!
```

History after rollback:

```text
helm history devops-info-service -n devops-lab10
1   ...   superseded   Install complete
2   ...   superseded   Upgrade complete
3   ...   deployed     Rollback to 1
```

`kubectl get all -n devops-lab10` after rollback confirmed that the environment returned to dev profile:

- `Service` returned to `NodePort`
- Deployment returned to `1/1`

Then the release was rolled forward again to revision 2 successfully:

```bash
helm rollback devops-info-service 2 -n devops-lab10 --wait --timeout 5m
```

### How to uninstall

Uninstall was tested successfully:

```text
helm uninstall devops-info-service -n devops-lab10
release "devops-info-service" uninstalled

kubectl delete namespace devops-lab10
namespace "devops-lab10" deleted
```

---

## 6. Testing & Validation

### `helm lint` output

```text
==> Linting .\k8s\devops-info-service
[INFO] Chart.yaml: icon is recommended

1 chart(s) linted, 0 chart(s) failed
```

### `helm template` verification

`helm template devops-info-service .\k8s\devops-info-service` rendered:

- `Service`
- `Deployment`
- `pre-install` Job
- `post-install` Job

The rendered YAML confirmed:

- dynamic labels from `_helpers.tpl`
- templated names based on the release name
- image repository and tag from values
- probes included in the Deployment
- environment variables templated correctly

### Dry-run verification

`helm install --dry-run --debug test-release .\k8s\devops-info-service` showed:

- all computed values
- `HOOKS` section with both hook Jobs
- `MANIFEST` section with Service and Deployment
- final `NOTES` instructions

### Application accessibility verification

Development profile could be reached with:

```bash
minikube service devops-info-service -n devops-lab10 --url
```

For the production profile in Minikube, `LoadBalancer` remained with `EXTERNAL-IP: <pending>` unless `minikube tunnel` is started. That is expected behavior in a local Minikube environment.

### Additional operational observations

- During startup, the application briefly failed `startupProbe` with `connection refused` before the process was fully ready.
- This did not break the deployment because the pod eventually became `Running` and the Deployment reached the desired available replica count.
- Hook cleanup behavior worked as expected: `kubectl get jobs -n devops-lab10` showed no jobs after success.

---

## Conclusion

The Lab 9 static Kubernetes manifests were successfully converted into a reusable Helm chart with:

- parameterized templates
- helper templates for labels and names
- configurable health checks
- separate dev and prod values files
- working pre-install and post-install hooks
- successful install, upgrade, rollback, and uninstall validation

Bonus Task was intentionally skipped according to the lab requirement for this submission.
