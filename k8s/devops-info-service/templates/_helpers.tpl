{{/* Expand the name of the chart. */}}
{{- define "devops-info-service.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* Create a chart name and version string. */}}
{{- define "devops-info-service.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* Create a default fully qualified app name. */}}
{{- define "devops-info-service.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/* Name of the ServiceAccount used by the Deployment. */}}
{{- define "devops-info-service.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "devops-info-service.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{/* Name of the Secret used for environment variable injection. */}}
{{- define "devops-info-service.secretName" -}}
{{- if .Values.secret.nameOverride -}}
{{- .Values.secret.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-secret" (include "devops-info-service.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{/* Name of the ConfigMap used for file-based configuration. */}}
{{- define "devops-info-service.configFileConfigMapName" -}}
{{- printf "%s-config" (include "devops-info-service.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* Name of the ConfigMap used for environment variables. */}}
{{- define "devops-info-service.envConfigMapName" -}}
{{- printf "%s-env" (include "devops-info-service.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* Name of the PersistentVolumeClaim used by the application. */}}
{{- define "devops-info-service.pvcName" -}}
{{- printf "%s-data" (include "devops-info-service.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}



{{/* Name of the headless Service used by the StatefulSet. */}}
{{- define "devops-info-service.headlessServiceName" -}}
{{- printf "%s-headless" (include "devops-info-service.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* Name of the preview Service used by the blue-green rollout strategy. */}}
{{- define "devops-info-service.previewServiceName" -}}
{{- printf "%s-preview" (include "devops-info-service.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{/* Labels used on all managed resources. */}}
{{- define "devops-info-service.labels" -}}
helm.sh/chart: {{ include "devops-info-service.chart" . }}
{{ include "devops-info-service.selectorLabels" . }}
app.kubernetes.io/version: {{ default .Chart.AppVersion .Values.appConfig.serviceVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/component: {{ .Values.component | quote }}
app.kubernetes.io/part-of: {{ .Values.partOf | quote }}
{{- end -}}

{{/* Labels used in selectors. */}}
{{- define "devops-info-service.selectorLabels" -}}
app.kubernetes.io/name: {{ include "devops-info-service.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/* Vault injector annotations added to the Pod template when enabled. */}}
{{- define "devops-info-service.vaultAnnotations" -}}
{{- if .Values.vault.enabled }}
vault.hashicorp.com/agent-inject: "true"
vault.hashicorp.com/role: {{ .Values.vault.role | quote }}
vault.hashicorp.com/agent-inject-status: "update"
vault.hashicorp.com/agent-inject-secret-{{ .Values.vault.injectFileName }}: {{ .Values.vault.secretPath | quote }}
{{- end }}
{{- end -}}