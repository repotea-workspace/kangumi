{{/*
Expand the name of the chart.
*/}}
{{- define "graphiti.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "graphiti.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "graphiti.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Base labels.
*/}}
{{- define "graphiti.baseLabels" -}}
helm.sh/chart: {{ include "graphiti.chart" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Common labels.
*/}}
{{- define "graphiti.labels" -}}
{{ include "graphiti.baseLabels" . }}
{{ include "graphiti.selectorLabels" . }}
{{- end }}

{{/*
Neo4j labels.
*/}}
{{- define "graphiti.neo4jLabels" -}}
{{ include "graphiti.baseLabels" . }}
{{ include "graphiti.neo4jSelectorLabels" . }}
{{- end }}

{{/*
Selector labels.
*/}}
{{- define "graphiti.selectorLabels" -}}
app.kubernetes.io/name: {{ include "graphiti.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: mcp
{{- end }}

{{/*
Neo4j selector labels.
*/}}
{{- define "graphiti.neo4jSelectorLabels" -}}
app.kubernetes.io/name: {{ include "graphiti.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: neo4j
{{- end }}

{{/*
Create the name of the service account to use.
*/}}
{{- define "graphiti.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "graphiti.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Build the image reference.
*/}}
{{- define "graphiti.image" -}}
{{- if .Values.image.digest }}
{{- printf "%s@%s" .Values.image.repository .Values.image.digest }}
{{- else if .Values.image.tag }}
{{- printf "%s:%s" .Values.image.repository .Values.image.tag }}
{{- else }}
{{- printf "%s:%s" .Values.image.repository .Chart.AppVersion }}
{{- end }}
{{- end }}

{{/*
Build the Neo4j image reference.
*/}}
{{- define "graphiti.neo4jImage" -}}
{{- printf "%s:%s" .Values.neo4j.image.repository .Values.neo4j.image.tag }}
{{- end }}

{{/*
Neo4j resource name.
*/}}
{{- define "graphiti.neo4jName" -}}
{{- printf "%s-neo4j" (include "graphiti.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Neo4j headless service name.
*/}}
{{- define "graphiti.neo4jHeadlessName" -}}
{{- printf "%s-neo4j-headless" (include "graphiti.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Whether the auth proxy sidecar should be enabled.
*/}}
{{- define "graphiti.authProxyEnabled" -}}
{{- if and .Values.ingress.enabled .Values.ingress.auth.enabled }}true{{- else }}false{{- end }}
{{- end }}

{{/*
Ingress backend service name.
*/}}
{{- define "graphiti.ingressServiceName" -}}
{{- if eq (include "graphiti.authProxyEnabled" .) "true" }}
{{- printf "%s-auth-proxy" (include "graphiti.fullname" .) }}
{{- else }}
{{- include "graphiti.fullname" . }}
{{- end }}
{{- end }}
