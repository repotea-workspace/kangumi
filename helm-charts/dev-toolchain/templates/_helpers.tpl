{{/*
Expand the name of the chart.
*/}}
{{- define "dev-toolchain.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "dev-toolchain.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "dev-toolchain.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "dev-toolchain.labels" -}}
helm.sh/chart: {{ include "dev-toolchain.chart" . }}
{{ include "dev-toolchain.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels for a specific toolchain instance
*/}}
{{- define "dev-toolchain.selectorLabels" -}}
app.kubernetes.io/name: {{ include "dev-toolchain.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Instance-specific labels
Usage: include "dev-toolchain.instanceLabels" (dict "root" $ "name" "fewensa")
*/}}
{{- define "dev-toolchain.instanceLabels" -}}
{{ include "dev-toolchain.labels" .root }}
app.kubernetes.io/component: {{ .name | quote }}
dev-toolchain/instance: {{ .name | quote }}
{{- end }}

{{/*
Instance-specific selector labels
Usage: include "dev-toolchain.instanceSelectorLabels" (dict "root" $ "name" "fewensa")
*/}}
{{- define "dev-toolchain.instanceSelectorLabels" -}}
{{ include "dev-toolchain.selectorLabels" .root }}
app.kubernetes.io/component: {{ .name | quote }}
dev-toolchain/instance: {{ .name | quote }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "dev-toolchain.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "dev-toolchain.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Generate full image name
Usage: include "dev-toolchain.image" (dict "root" $ "config" .Values.toolchains.fewensa)
*/}}
{{- define "dev-toolchain.image" -}}
{{- $registry := .config.imageRegistry | default .root.Values.global.imageRegistry -}}
{{- if $registry }}
{{- printf "%s/%s" $registry .config.image }}
{{- else }}
{{- .config.image }}
{{- end }}
{{- end }}



{{/*
Get image pull policy
Usage: include "dev-toolchain.imagePullPolicy" (dict "root" $ "config" .Values.toolchains.fewensa)
*/}}
{{- define "dev-toolchain.imagePullPolicy" -}}
{{- .config.imagePullPolicy | default .root.Values.global.imagePullPolicy | default "IfNotPresent" }}
{{- end }}

{{/*
Generate PVC name for a toolchain instance
Usage: include "dev-toolchain.pvcName" (dict "root" $ "name" "fewensa" "config" .Values.toolchains.fewensa)
*/}}
{{- define "dev-toolchain.pvcName" -}}
{{- if .config.storage.pvc.name }}
{{- .config.storage.pvc.name }}
{{- else }}
{{- printf "%s-%s-data" (include "dev-toolchain.fullname" .root) .name }}
{{- end }}
{{- end }}

{{/*
Generate shared PVC name
Usage: include "dev-toolchain.sharedPvcName" (dict "root" $ "config" .Values.toolchains.fewensa)
*/}}
{{- define "dev-toolchain.sharedPvcName" -}}
{{- .config.storage.sharedPVC.name | default "dev-shared-wwwroot" }}
{{- end }}

{{/*
Generate deployment name for a toolchain instance
Usage: include "dev-toolchain.deploymentName" (dict "root" $ "name" "fewensa")
*/}}
{{- define "dev-toolchain.deploymentName" -}}
{{- printf "tch-%s" .name }}
{{- end }}

{{/*
Generate service name for a toolchain instance
Usage: include "dev-toolchain.serviceName" (dict "root" $ "name" "fewensa")
*/}}
{{- define "dev-toolchain.serviceName" -}}
{{- printf "%s-%s" (include "dev-toolchain.fullname" .root) .name }}
{{- end }}

{{/*
Generate config map name for a toolchain instance
Usage: include "dev-toolchain.configMapName" (dict "root" $ "name" "fewensa")
*/}}
{{- define "dev-toolchain.configMapName" -}}
{{- printf "tch-%s-sshd-config" .name }}
{{- end }}
