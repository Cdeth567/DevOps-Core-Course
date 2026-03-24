# Kubernetes Implementation

## Architecture Overview

The application is deployed into a dedicated Kubernetes namespace called `devops-lab09`.

Architecture of the deployment:

- **1 Namespace**: `devops-lab09`
- **1 Deployment**: `devops-info-service`
- **3 Pods** in the base configuration
- **1 Service** of type `NodePort`
- **1 container per Pod**
- **HTTP probes** for health and readiness control

Networking flow:

1. External request reaches the Service exposed through Minikube.
2. The `NodePort` Service forwards traffic to healthy Pods selected by labels.
3. The Deployment ensures the desired number of replicas is always running.
4. Readiness probe prevents traffic from reaching Pods that are not ready.
5. Liveness and startup probes help recover from unhealthy or slow-starting containers.

Resource allocation strategy:

- Requests:
  - `cpu: 100m`
  - `memory: 128Mi`
- Limits:
  - `cpu: 250m`
  - `memory: 256Mi`

This configuration is small enough for local Minikube usage, but still demonstrates production-oriented resource governance.

---

## Manifest Files

### `namespace.yml`
Creates the namespace `devops-lab09` for logical isolation of Kubernetes resources.

### `deployment.yml`
Main Deployment manifest for the Python application.

Key choices:
- `replicas: 3` to satisfy the task requirement and demonstrate high availability
- `RollingUpdate` strategy with:
  - `maxSurge: 1`
  - `maxUnavailable: 0`
- resource requests and limits
- environment variables for app metadata
- container exposed on port `5000`
- `livenessProbe` on `/health`
- `readinessProbe` on `/ready`
- `startupProbe` on `/ready`

Why these values were chosen:
- 3 replicas are the minimum required by the assignment and provide redundancy
- `maxUnavailable: 0` helps ensure no downtime during updates
- `maxSurge: 1` allows gradual replacement of Pods
- modest CPU/memory settings are appropriate for local development while still demonstrating best practice

### `service.yml`
Creates a `NodePort` Service for exposing the Deployment outside the cluster.

Key choices:
- `type: NodePort`
- service port `80`
- target container port `5000`
- fixed nodePort `30080`

Why:
- NodePort is explicitly recommended in the assignment for local cluster access
- fixed nodePort makes local testing predictable

### `deployment-update.yml`
Used to demonstrate rolling updates.  
This manifest changes application configuration so that a new rollout occurs and the new version can be verified via `/ready`.

### Unused bonus manifests
The repository may also contain:
- `deployment-app2.yml`
- `service-app2.yml`
- `ingress.yml`

These were not used because the bonus task was intentionally not completed.

---

## Deployment Evidence

### Cluster setup verification

Commands used:

```powershell
kubectl cluster-info
kubectl get nodes -o wide
```

Observed output:

```text
Kubernetes control plane is running at https://127.0.0.1:56880
CoreDNS is running at https://127.0.0.1:56880/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy
```

```text
NAME       STATUS   ROLES           AGE   VERSION   INTERNAL-IP    EXTERNAL-IP   OS-IMAGE                         KERNEL-VERSION                     CONTAINER-RUNTIME
minikube   Ready    control-plane   40m   v1.35.1   192.168.49.2   <none>        Debian GNU/Linux 12 (bookworm)   6.6.87.2-microsoft-standard-WSL2   docker://29.2.1
```

### Deployment state

Commands used:

```powershell
kubectl get all -n devops-lab09
kubectl get pods,svc -o wide -n devops-lab09
kubectl describe deployment devops-info-service -n devops-lab09
```

Observed output:

```text
NAME                                       READY   STATUS    RESTARTS   AGE
pod/devops-info-service-6dc8c746f4-7bp9n   1/1     Running   0          2m15s
pod/devops-info-service-6dc8c746f4-kxx8k   1/1     Running   0          2m15s
pod/devops-info-service-6dc8c746f4-njvzw   1/1     Running   0          2m15s

NAME                          TYPE       CLUSTER-IP       EXTERNAL-IP   PORT(S)        AGE
service/devops-info-service   NodePort   10.110.237.170   <none>        80:30080/TCP   34m

NAME                                  READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/devops-info-service   3/3     3            3           2m16s
```

```text
NAME                                       READY   STATUS    RESTARTS   AGE     IP            NODE       NOMINATED NODE   READINESS GATES
pod/devops-info-service-6dc8c746f4-7bp9n   1/1     Running   0          2m15s   10.244.0.8    minikube   <none>           <none>
pod/devops-info-service-6dc8c746f4-kxx8k   1/1     Running   0          2m15s   10.244.0.9    minikube   <none>           <none>
pod/devops-info-service-6dc8c746f4-njvzw   1/1     Running   0          2m15s   10.244.0.10   minikube   <none>           <none>

NAME                          TYPE       CLUSTER-IP       EXTERNAL-IP   PORT(S)        AGE   SELECTOR
service/devops-info-service   NodePort   10.110.237.170   <none>        80:30080/TCP   34m   app.kubernetes.io/instance=devops-info-service,app.kubernetes.io/name=devops-info-service
```

Deployment description confirmed:
- 3 desired replicas
- RollingUpdate strategy
- probes configured
- resource requests and limits configured

### Application working verification

Service URL:

```powershell
minikube service devops-info-service -n devops-lab09 --url
```

Observed URL:

```text
http://127.0.0.1:49708
```

Endpoint checks:

```powershell
curl http://127.0.0.1:49708/
curl http://127.0.0.1:49708/health
curl http://127.0.0.1:49708/ready
```

Observed results:

- `/` returned `200 OK`
- `/health` returned `200 OK`
- `/ready` returned `200 OK`

Example `/health` response:

```json
{"status":"healthy","timestamp":"2026-03-24T18:18:05.669Z","uptime_seconds":111}
```

Example `/ready` response:

```json
{"service":"devops-info-service","status":"ready","timestamp":"2026-03-24T18:18:13.566Z","version":"1.0.0-k8s"}
```

---

## Operations Performed

### 1. Image build

```powershell
minikube image build -t cdeth567/devops-info-service:lab09 .\app_python
```

### 2. Initial deployment

```powershell
kubectl apply -f .\k8s\namespace.yml
kubectl apply -f .\k8s\deployment.yml
kubectl apply -f .\k8s\service.yml
```

### 3. Scaling demonstration

Scale command:

```powershell
kubectl scale deployment/devops-info-service --replicas=5 -n devops-lab09
kubectl rollout status deployment/devops-info-service -n devops-lab09
kubectl get pods -n devops-lab09
```

Observed output:

```text
deployment "devops-info-service" successfully rolled out
```

```text
NAME                                   READY   STATUS    RESTARTS   AGE
devops-info-service-6dc8c746f4-7bp9n   1/1     Running   0          2m48s
devops-info-service-6dc8c746f4-fq87x   1/1     Running   0          12s
devops-info-service-6dc8c746f4-kxx8k   1/1     Running   0          2m48s
devops-info-service-6dc8c746f4-njvzw   1/1     Running   0          2m48s
devops-info-service-6dc8c746f4-skgb2   1/1     Running   0          12s
```

Then the Deployment was returned to the base configuration:

```powershell
kubectl apply -f .\k8s\deployment.yml
kubectl rollout status deployment/devops-info-service -n devops-lab09
```

### 4. Rolling update demonstration

Update command:

```powershell
kubectl apply -f .\k8s\deployment-update.yml
kubectl rollout status deployment/devops-info-service -n devops-lab09
kubectl rollout history deployment/devops-info-service -n devops-lab09
kubectl get pods -n devops-lab09
```

Observed output:

```text
deployment "devops-info-service" successfully rolled out
```

```text
deployment.apps/devops-info-service
REVISION  CHANGE-CAUSE
1         <none>
2         <none>
```

Pods during update:

```text
NAME                                   READY   STATUS        RESTARTS   AGE
devops-info-service-5675c54f79-27x4l   1/1     Running       0          21s
devops-info-service-5675c54f79-5dd2p   1/1     Running       0          8s
devops-info-service-5675c54f79-6qwqs   1/1     Running       0          14s
devops-info-service-6dc8c746f4-7bp9n   1/1     Terminating   0          3m44s
devops-info-service-6dc8c746f4-kxx8k   1/1     Terminating   0          3m44s
devops-info-service-6dc8c746f4-njvzw   1/1     Terminating   0          3m44s
```

Version check after update:

```powershell
curl http://127.0.0.1:49708/ready
```

Response:

```json
{"service":"devops-info-service","status":"ready","timestamp":"2026-03-24T18:21:00.104Z","version":"1.1.0-k8s"}
```

### 5. Rollback demonstration

Rollback commands:

```powershell
kubectl rollout undo deployment/devops-info-service -n devops-lab09
kubectl rollout status deployment/devops-info-service -n devops-lab09
kubectl rollout history deployment/devops-info-service -n devops-lab09
kubectl get pods -n devops-lab09
```

Observed output:

```text
deployment.apps/devops-info-service rolled back
deployment "devops-info-service" successfully rolled out
```

Pods after rollback:

```text
NAME                                   READY   STATUS        RESTARTS   AGE
devops-info-service-5675c54f79-27x4l   1/1     Terminating   0          116s
devops-info-service-5675c54f79-5dd2p   1/1     Terminating   0          103s
devops-info-service-5675c54f79-6qwqs   1/1     Terminating   0          109s
devops-info-service-6dc8c746f4-jncd8   1/1     Running       0          15s
devops-info-service-6dc8c746f4-pbxjd   1/1     Running       0          9s
devops-info-service-6dc8c746f4-qwr2t   1/1     Running       0          21s
```

Version check after rollback:

```powershell
curl http://127.0.0.1:49708/ready
```

Response:

```json
{"service":"devops-info-service","status":"ready","timestamp":"2026-03-24T18:21:30.812Z","version":"1.0.0-k8s"}
```

### 6. Zero downtime verification

Zero downtime was verified during the rolling update by checking service availability before and after the rollout and confirming that:
- new Pods became Ready before old Pods were terminated
- Service endpoint continued returning `200 OK`
- update and rollback both completed successfully without total service loss

This was supported by:
- `maxUnavailable: 0`
- readiness probes on `/ready`
- successful responses from the application during rollout validation

### 7. Service access method

The application was accessed using:

```powershell
minikube service devops-info-service -n devops-lab09 --url
```

On Windows with Docker driver, the terminal used for this command must stay open because Minikube keeps a local tunnel active.

---

## Production Considerations

### Health checks implemented

The Deployment uses:
- `livenessProbe` on `/health`
- `readinessProbe` on `/ready`
- `startupProbe` on `/ready`

Why:
- **liveness probe** detects broken containers and allows automatic restart
- **readiness probe** ensures traffic is sent only to ready Pods
- **startup probe** protects slow starts from being killed too early

This closely reflects production deployment best practices for HTTP services.

### Resource limits rationale

Chosen values:

- requests:
  - `cpu: 100m`
  - `memory: 128Mi`
- limits:
  - `cpu: 250m`
  - `memory: 256Mi`

Rationale:
- sufficient for a lightweight Flask service in a local cluster
- demonstrates proper scheduling hints and protection against uncontrolled resource usage
- helps avoid resource starvation and noisy neighbor effects

### How this could be improved for production

For a real production environment, I would improve the setup by:

- using a real container registry and immutable image tags
- adding Horizontal Pod Autoscaler
- using Ingress or Gateway API instead of direct NodePort exposure
- separating config into ConfigMaps and Secrets
- adding PodDisruptionBudget
- adding affinity / anti-affinity rules
- using multiple nodes instead of single-node Minikube
- storing logs centrally

### Monitoring and observability strategy

For production observability I would add:

- Prometheus for metrics collection
- Grafana dashboards
- centralized logging (for example Loki or ELK)
- alerting on Pod restarts, probe failures, CPU/memory saturation, and rollout failures
- Kubernetes events monitoring
- tracing if the application becomes distributed

---

## Challenges & Solutions

### Challenge 1 — `CreateContainerConfigError`

Initial Pods failed with:

```text
CreateContainerConfigError
```

Detailed debugging with `kubectl describe pod` showed:

```text
Error: container has runAsNonRoot and image has non-numeric user (app), cannot verify user is non-root
```

#### Cause
The Deployment required non-root execution, but the image used a named user instead of a numeric UID.

#### Solution
The Dockerfile was updated to create a numeric user and run the app as:

```dockerfile
RUN addgroup --system --gid 1000 app \
    && adduser --system --uid 1000 --ingroup app app

USER 1000:1000
```

#### What I learned
Kubernetes security settings may reject a container even before startup if the runtime cannot verify non-root execution.

### Challenge 2 — `CrashLoopBackOff`

After fixing the non-root issue, Pods still failed and entered:

```text
CrashLoopBackOff
```

Debugging using:
- `kubectl describe pod`
- `kubectl logs`
- `kubectl get events`

showed:

```text
Startup probe failed: HTTP probe failed with statuscode: 404
```

and application logs confirmed:

```text
"path": "/ready", "status_code": 404
```

#### Cause
`startupProbe` and `readinessProbe` were configured to call `/ready`, but the application image did not yet contain that endpoint.

#### Solution
A `/ready` endpoint was added to `app_python/app.py`, the image was rebuilt, and the Deployment was recreated.

#### What I learned
Kubernetes probes are strict and extremely useful for debugging application readiness problems.  
If probes and application endpoints do not match, Pods may restart even when the container process itself starts successfully.

### Debugging methods used

The main Kubernetes debugging commands used during this lab were:

```powershell
kubectl describe pod <pod-name> -n devops-lab09
kubectl logs -n devops-lab09 <pod-name>
kubectl get events -n devops-lab09 --sort-by=.metadata.creationTimestamp
kubectl describe deployment devops-info-service -n devops-lab09
```

These commands were enough to identify both configuration-level and application-level issues.

---

## Conclusion

The required Kubernetes tasks for Lab 09 were completed successfully without the bonus task.

Completed items:

- local Minikube cluster setup
- Deployment manifest with 3 replicas
- NodePort Service
- liveness, readiness and startup probes
- resource requests and limits
- service accessibility from outside the cluster
- scaling to 5 replicas
- rolling update
- rollback
- documentation with evidence, production considerations, and troubleshooting

Bonus task with Ingress and TLS was intentionally not completed.
