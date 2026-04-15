#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-devops-lab11}"
VAULT_POD="${VAULT_POD:-vault-0}"
POLICY_NAME="${POLICY_NAME:-devops-info-service}"
ROLE_NAME="${ROLE_NAME:-devops-info-service}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:-devops-info-service}"
SECRET_PATH="${SECRET_PATH:-secret/myapp/config}"
APP_USERNAME="${APP_USERNAME:-vault-admin}"
APP_PASSWORD="${APP_PASSWORD:-vault-password-123}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POLICY_FILE="${SCRIPT_DIR}/app-policy.hcl"

kubectl exec -n "${NAMESPACE}" "${VAULT_POD}" -- sh -lc 'export VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=root; vault status >/dev/null'

kubectl exec -n "${NAMESPACE}" "${VAULT_POD}" -- sh -lc 'export VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=root; vault secrets list -format=json | grep -q '"'"'secret/'"'"' || vault secrets enable -path=secret kv-v2'

kubectl exec -n "${NAMESPACE}" "${VAULT_POD}" -- sh -lc "export VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=root; vault kv put ${SECRET_PATH} username='${APP_USERNAME}' password='${APP_PASSWORD}'"

kubectl cp "${POLICY_FILE}" "${NAMESPACE}/${VAULT_POD}:/tmp/app-policy.hcl"
kubectl exec -n "${NAMESPACE}" "${VAULT_POD}" -- sh -lc "export VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=root; vault policy write ${POLICY_NAME} /tmp/app-policy.hcl"

kubectl exec -n "${NAMESPACE}" "${VAULT_POD}" -- sh -lc 'export VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=root; vault auth list -format=json | grep -q '"'"'kubernetes/'"'"' || vault auth enable kubernetes'

kubectl exec -n "${NAMESPACE}" "${VAULT_POD}" -- sh -lc 'export VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=root; vault write auth/kubernetes/config \
  token_reviewer_jwt="$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)" \
  kubernetes_host="https://${KUBERNETES_PORT_443_TCP_ADDR}:443" \
  kubernetes_ca_cert=@/var/run/secrets/kubernetes.io/serviceaccount/ca.crt >/dev/null'

kubectl exec -n "${NAMESPACE}" "${VAULT_POD}" -- sh -lc "export VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=root; vault write auth/kubernetes/role/${ROLE_NAME} \
  bound_service_account_names=${SERVICE_ACCOUNT} \
  bound_service_account_namespaces=${NAMESPACE} \
  policies=${POLICY_NAME} \
  ttl=24h >/dev/null"

echo "Vault has been configured."
echo "Policy: ${POLICY_NAME}"
echo "Role: ${ROLE_NAME}"
echo "Secret path: ${SECRET_PATH}"
