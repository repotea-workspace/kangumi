{{/*
Expand the name of the chart.
*/}}
{{- define "lanhu-mcp.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "lanhu-mcp.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "lanhu-mcp.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "lanhu-mcp.labels" -}}
helm.sh/chart: {{ include "lanhu-mcp.chart" . }}
{{ include "lanhu-mcp.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "lanhu-mcp.selectorLabels" -}}
app.kubernetes.io/name: {{ include "lanhu-mcp.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "lanhu-mcp.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "lanhu-mcp.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Whether the auth proxy sidecar should be enabled
*/}}
{{- define "lanhu-mcp.authProxyEnabled" -}}
{{- if .Values.ingress.auth.token }}true{{- else }}false{{- end }}
{{- end }}

{{/*
Ingress backend service name
*/}}
{{- define "lanhu-mcp.ingressServiceName" -}}
{{- if eq (include "lanhu-mcp.authProxyEnabled" .) "true" }}
{{- printf "%s-auth-proxy" (include "lanhu-mcp.fullname" .) }}
{{- else }}
{{- include "lanhu-mcp.fullname" . }}
{{- end }}
{{- end }}

{{/*
PVC names
*/}}
{{- define "lanhu-mcp.sharedClaimName" -}}
{{- if .Values.persistence.shared.existingClaim }}
{{- .Values.persistence.shared.existingClaim }}
{{- else }}
{{- printf "%s-storage" (include "lanhu-mcp.fullname" .) }}
{{- end }}
{{- end }}
