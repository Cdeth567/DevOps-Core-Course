# StatefulSet & Persistent Storage

## 1. StatefulSet Overview

A StatefulSet is the preferred Kubernetes workload controller for applications that need:

- stable pod names and ordinal identities
- stable network identities with per-pod DNS
- persistent storage bound to each replica
- ordered startup, update, and termination behavior

This makes StatefulSet different from Deployment, which is better suited for stateless applications where replicas are interchangeable.

For the DevOps Info Service in Lab 15, StatefulSet is the correct choice because each replica stores its own visit counter in `/data/visits`, and that data must remain isolated and persistent for each pod.

### Deployment vs StatefulSet

| Characteristic | Deployment | StatefulSet |
|---|---|---|
| Pod identity | Ephemeral | Stable (`pod-0`, `pod-1`, `pod-2`) |
| DNS identity | Not stable per replica | Stable per replica |
| Storage | Typically shared or stateless | One PVC per replica |
| Scaling behavior | Unordered | Ordered |
| Suitable for | Stateless web services | Stateful services |

### Examples of stateful workloads

Typical StatefulSet workloads include PostgreSQL, MySQL, MongoDB, Kafka, RabbitMQ, Cassandra, and Elasticsearch.

## 2. Resource Verification

The application was deployed with Helm into the `dev` namespace.

### Commands used

```bash
kubectl create namespace dev
helm upgrade --install lab15 ./k8s/devops-info-service -n dev -f ./k8s/devops-info-service/values-dev.yaml
kubectl rollout status statefulset/lab15-devops-info-service -n dev
kubectl get po,sts,svc,pvc -n dev
kubectl get svc lab15-devops-info-service-headless -n dev
```

### Observed results

The StatefulSet rollout completed successfully:

```text
statefulset rolling update complete 3 pods at revision lab15-devops-info-service-84478d4564...
```

The following resources were present in the `dev` namespace:

```text
statefulset.apps/lab15-devops-info-service   3/3

pod/lab15-devops-info-service-0   1/1 Running
pod/lab15-devops-info-service-1   1/1 Running
pod/lab15-devops-info-service-2   1/1 Running

service/lab15-devops-info-service            ClusterIP   10.109.18.78   80/TCP
service/lab15-devops-info-service-headless   ClusterIP   None            80/TCP

persistentvolumeclaim/data-volume-lab15-devops-info-service-0   Bound
persistentvolumeclaim/data-volume-lab15-devops-info-service-1   Bound
persistentvolumeclaim/data-volume-lab15-devops-info-service-2   Bound
```

### Verification summary

This confirms that:

- the application is managed by a StatefulSet
- three replicas were created with stable ordinal names
- a headless service exists and has `ClusterIP: None`
- a separate PVC was created for each pod

## 3. Network Identity

A headless service was created for stable per-pod DNS resolution.

### Commands used

```bash
kubectl run dns-check -n dev --image=busybox:1.36 --restart=Never --command -- sleep 300
kubectl wait --for=condition=Ready pod/dns-check -n dev --timeout=60s
kubectl exec -n dev dns-check -- nslookup lab15-devops-info-service-1.lab15-devops-info-service-headless.dev.svc.cluster.local
kubectl exec -n dev dns-check -- nslookup lab15-devops-info-service-2.lab15-devops-info-service-headless.dev.svc.cluster.local
kubectl delete pod dns-check -n dev
```

### Observed results

```text
Name:   lab15-devops-info-service-1.lab15-devops-info-service-headless.dev.svc.cluster.local
Address: 10.244.0.171
```

```text
Name:   lab15-devops-info-service-2.lab15-devops-info-service-headless.dev.svc.cluster.local
Address: 10.244.0.172
```

### Verification summary

This confirms that each pod has a stable network identity and can be reached through the headless service DNS name.

## 4. Per-Pod Storage Evidence

To prove that each replica keeps its own independent visit counter, each pod was accessed directly through a dedicated port-forward.

### Commands used

#### Port-forward sessions

```bash
kubectl port-forward pod/lab15-devops-info-service-0 -n dev 8080:5000
kubectl port-forward pod/lab15-devops-info-service-1 -n dev 8081:5000
kubectl port-forward pod/lab15-devops-info-service-2 -n dev 8082:5000
```

#### Requests sent to each pod

```bash
curl.exe http://127.0.0.1:8080/
curl.exe http://127.0.0.1:8080/

curl.exe http://127.0.0.1:8081/

curl.exe http://127.0.0.1:8082/
curl.exe http://127.0.0.1:8082/
curl.exe http://127.0.0.1:8082/
```

#### Counter verification

```bash
kubectl exec -n dev lab15-devops-info-service-0 -- cat /data/visits
kubectl exec -n dev lab15-devops-info-service-1 -- cat /data/visits
kubectl exec -n dev lab15-devops-info-service-2 -- cat /data/visits
```

### Observed results

The responses from the pods showed distinct hostnames:

- `lab15-devops-info-service-0`
- `lab15-devops-info-service-1`
- `lab15-devops-info-service-2`

The stored counter values were:

```text
lab15-devops-info-service-0 -> 4
lab15-devops-info-service-1 -> 2
lab15-devops-info-service-2 -> 6
```

### Verification summary

These different counter values prove that each pod writes to its own persistent storage and does not share the same `/data/visits` file with the other replicas.

## 5. Persistence Test

The persistence requirement was verified by deleting pod `lab15-devops-info-service-0` and checking whether its counter value survived recreation.

### Commands used

```bash
kubectl exec -n dev lab15-devops-info-service-0 -- cat /data/visits
kubectl delete pod -n dev lab15-devops-info-service-0
kubectl rollout status statefulset/lab15-devops-info-service -n dev
kubectl exec -n dev lab15-devops-info-service-0 -- cat /data/visits
```

### Observed results

Before recreation:

```text
4
```

After pod deletion and recreation:

```text
4
```

The rollout also completed successfully:

```text
statefulset rolling update complete 3 pods at revision lab15-devops-info-service-84478d4564...
```

### Verification summary

This proves that:

- the recreated pod came back with the same ordinal identity
- the PVC attached to pod `-0` was reused
- the data in `/data/visits` persisted across pod recreation

## Conclusion

The Lab 15 StatefulSet implementation works correctly and satisfies the assignment requirements:

- StatefulSet is used instead of Deployment for the stateful scenario
- the application has stable ordinal pod identities
- the headless service provides stable per-pod DNS
- each replica has its own PVC
- visit counters are isolated per pod
- data persists after pod recreation
