# Lab 13 — GitOps with ArgoCD

## Overview

This lab adds a GitOps deployment workflow for the `devops-info-service` Helm chart using ArgoCD.
The repository now contains:

- ArgoCD application manifests for a single manual deployment and separate dev/prod environments
- namespace manifests for the dev and prod environments
- an ArgoCD Helm values override for local Minikube setup
- updated Helm environment values for ArgoCD-based deployment

Bonus Task with ApplicationSet was intentionally **not implemented**.

---

## 1. ArgoCD installation and access

### Helm installation

ArgoCD is installed into a dedicated `argocd` namespace.

Commands:

```powershell
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update
kubectl create namespace argocd
helm upgrade --install argocd argo/argo-cd `
  --namespace argocd `
  -f .\k8s\argocd\argocd-values.yaml
kubectl get pods -n argocd
kubectl wait --for=condition=ready pod -l app.kubernetes.io/part-of=argocd -n argocd --timeout=300s
```

The file `k8s/argocd/argocd-values.yaml` sets:

```yaml
configs:
  params:
    server.insecure: true
server:
  service:
    type: ClusterIP
```

This simplifies local access by allowing HTTP port-forwarding to the ArgoCD server.

### Accessing the UI

Port-forward the ArgoCD server:

```powershell
kubectl port-forward svc/argocd-server -n argocd 8080:80
```

Get the initial admin password:

```powershell
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}"
```

Decode the password in PowerShell:

```powershell
[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String((kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}")))
```

Open the UI at:

```text
http://127.0.0.1:8080
```

Username:

```text
admin
```

### ArgoCD CLI installation and login

On Windows, the CLI can be downloaded with PowerShell:

```powershell
$version = (Invoke-RestMethod https://api.github.com/repos/argoproj/argo-cd/releases/latest).tag_name
$url = "https://github.com/argoproj/argo-cd/releases/download/$version/argocd-windows-amd64.exe"
Invoke-WebRequest -Uri $url -OutFile .\argocd.exe
```

Login command:

```powershell
.\argocd.exe login 127.0.0.1:8080 --insecure
.\argocd.exe app list
```

---

## 2. Application manifests

The following directory was added:

```text
k8s/argocd/
```

It contains:

- `application.yaml` — single manual ArgoCD Application for the chart
- `application-dev.yaml` — dev environment with auto-sync and self-heal
- `application-prod.yaml` — prod environment with manual sync
- `namespaces.yaml` — dev and prod namespaces
- `argocd-values.yaml` — Helm values override for installing ArgoCD locally

### Single application manifest

`k8s/argocd/application.yaml` defines a manual ArgoCD Application:

- source repo: `https://github.com/Cdeth567/DevOps-Core-Course.git`
- target revision: `lab13`
- chart path: `k8s/devops-info-service`
- destination namespace: `devops`
- sync policy: manual

It uses `values-dev.yaml`, but overrides the service type to `ClusterIP` to avoid NodePort conflicts when multiple ArgoCD applications exist in the same cluster.

Apply it with:

```powershell
kubectl apply -f .\k8s\argocd\application.yaml
kubectl get applications -n argocd
.\argocd.exe app get devops-info-service
```

Manual sync:

```powershell
.\argocd.exe app sync devops-info-service
.\argocd.exe app get devops-info-service
kubectl get all -n devops
kubectl port-forward svc/devops-info-service-gitops -n devops 8081:80
```

Verify the app:

```powershell
Invoke-RestMethod http://127.0.0.1:8081/health
Invoke-RestMethod http://127.0.0.1:8081/visits
```

---

## 3. Multi-environment deployment

### Namespace separation

The file `k8s/argocd/namespaces.yaml` creates two namespaces:

```text
dev
prod
```

Apply them with:

```powershell
kubectl apply -f .\k8s\argocd\namespaces.yaml
```

### Dev application

`k8s/argocd/application-dev.yaml` deploys the chart into the `dev` namespace using `values-dev.yaml`.

Important settings:

- `releaseName: devops-info-service-dev`
- destination namespace: `dev`
- sync policy: automated
- `prune: true`
- `selfHeal: true`

Apply it with:

```powershell
kubectl apply -f .\k8s\argocd\application-dev.yaml
.\argocd.exe app get devops-info-service-dev
```

### Prod application

`k8s/argocd/application-prod.yaml` deploys the chart into the `prod` namespace using `values-prod.yaml`.

Important settings:

- `releaseName: devops-info-service-prod`
- destination namespace: `prod`
- sync policy: manual

Apply it with:

```powershell
kubectl apply -f .\k8s\argocd\application-prod.yaml
.\argocd.exe app get devops-info-service-prod
```

### Dev vs Prod configuration differences

#### Dev (`values-dev.yaml`)

- `replicaCount: 1`
- `environment: dev`
- `logLevel: DEBUG`
- smaller resource requests and limits
- `service.type: NodePort`
- local image: `app_python-devops-info-service:latest`
- auto-sync enabled in ArgoCD

#### Prod (`values-prod.yaml`)

- `replicaCount: 3`
- `environment: prod`
- `logLevel: WARN`
- higher resource requests and limits
- `service.type: LoadBalancer`
- same image but manual promotion workflow
- ArgoCD sync remains manual

### Why dev is automated and prod is manual

Dev is configured for automatic sync because it is used for fast feedback, iterative changes, and self-healing during development.

Prod remains manual because it is safer to review Git changes before deployment, control the release timing, and confirm readiness before promoting changes to production.

### Verifying both environments

Before syncing applications, make sure the app image is available in Minikube:

```powershell
minikube image load app_python-devops-info-service:latest
```

Check ArgoCD applications:

```powershell
.\argocd.exe app list
```

Check workloads:

```powershell
kubectl get pods -n dev
kubectl get pods -n prod
kubectl get svc -n dev
kubectl get svc -n prod
```

Access dev via Minikube NodePort or port-forward:

```powershell
kubectl port-forward svc/devops-info-service-dev -n dev 8082:80
Invoke-RestMethod http://127.0.0.1:8082/visits
```

Access prod via port-forward:

```powershell
kubectl port-forward svc/devops-info-service-prod -n prod 8083:80
Invoke-RestMethod http://127.0.0.1:8083/visits
```

---

## 4. GitOps workflow

A GitOps deployment flow for this repository is:

1. Modify the Helm chart or values in Git.
2. Commit the change.
3. Push the change to the `lab13` branch.
4. ArgoCD detects the change.
5. Dev auto-syncs automatically.
6. Prod becomes `OutOfSync` until a manual sync is approved.

Example change to test the workflow:

- edit `k8s/devops-info-service/values-dev.yaml`
- change `replicaCount` from `1` to `2`
- commit and push

Commands:

```powershell
git add .
k8s\devops-info-service\values-dev.yaml
git commit -m "Update dev replica count for ArgoCD GitOps test"
git push origin lab13
.\argocd.exe app get devops-info-service-dev
.\argocd.exe app get devops-info-service-prod
```

Expected behavior:

- `devops-info-service-dev` auto-syncs to the new replica count
- `devops-info-service-prod` is marked `OutOfSync` until manual sync is triggered

Manual prod sync:

```powershell
.\argocd.exe app sync devops-info-service-prod
```

---

## 5. Self-healing and drift detection

### Manual scale drift test (ArgoCD self-healing)

This test should be performed in the **dev** namespace because auto-sync and self-heal are enabled there.

Commands:

```powershell
kubectl scale deployment devops-info-service-dev -n dev --replicas=5
kubectl get deploy -n dev
.\argocd.exe app get devops-info-service-dev
.\argocd.exe app diff devops-info-service-dev
kubectl get pods -n dev -w
```

Expected behavior:

- Kubernetes scales the Deployment to 5 replicas immediately.
- ArgoCD detects that the cluster state no longer matches Git.
- Because `selfHeal: true` is enabled, ArgoCD restores the deployment to the replica count defined in Git.

### Pod deletion test (Kubernetes self-healing)

Commands:

```powershell
kubectl delete pod -n dev -l app.kubernetes.io/instance=devops-info-service-dev
kubectl get pods -n dev -w
```

Expected behavior:

- The ReplicaSet/Deployment controller recreates the missing pod.
- This is **Kubernetes self-healing**, not ArgoCD self-healing.

### Configuration drift test

Commands:

```powershell
kubectl label deployment devops-info-service-dev -n dev drift-test=manual --overwrite
.\argocd.exe app diff devops-info-service-dev
.\argocd.exe app get devops-info-service-dev
kubectl get deployment devops-info-service-dev -n dev --show-labels
```

Expected behavior:

- ArgoCD detects the drift in the Deployment definition.
- Dev application returns to `Synced` after self-heal removes the manual label.

### Sync behavior explanation

- **Kubernetes self-healing** recreates failed or deleted pods to maintain the desired replica count.
- **ArgoCD self-healing** reverts manual changes so that live cluster resources match the Git-defined manifests.
- ArgoCD syncs automatically only for applications with `syncPolicy.automated` enabled.
- For manual applications, ArgoCD marks them `OutOfSync` and waits for an explicit sync action.
- The default ArgoCD polling interval is about **3 minutes** (120 seconds plus jitter), unless webhooks or manual refresh are used.

---

## 6. Screenshots to capture during verification

The assignment requires screenshots. Capture these while running the commands above:

1. ArgoCD UI showing both `devops-info-service-dev` and `devops-info-service-prod`
2. Sync status badges for both applications
3. Application details view for the dev environment
4. Drift/self-heal example in the diff view

---

## 7. Summary

The repository was prepared for GitOps deployment with ArgoCD by adding:

- ArgoCD installation values for local setup
- manual Application manifest
- dev/prod ArgoCD Application manifests
- namespace manifests for dev and prod
- cleaned environment values for Helm chart deployment via ArgoCD

Bonus Task with ApplicationSet was intentionally skipped.
