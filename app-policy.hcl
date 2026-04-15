path "secret/data/devops-info-service/config" {
  capabilities = ["read"]
}

path "secret/metadata/devops-info-service/config" {
  capabilities = ["read", "list"]
}

path "sys/internal/ui/mounts/secret/data/devops-info-service/config" {
  capabilities = ["read"]
}
