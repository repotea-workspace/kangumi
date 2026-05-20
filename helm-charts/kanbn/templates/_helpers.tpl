{{/*
Expand the name of the chart.
*/}}
{{- define "kanbn.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "kanbn.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "kanbn.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels.
*/}}
{{- define "kanbn.labels" -}}
helm.sh/chart: {{ include "kanbn.chart" . }}
{{ include "kanbn.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels.
*/}}
{{- define "kanbn.selectorLabels" -}}
app.kubernetes.io/name: {{ include "kanbn.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the service account name.
*/}}
{{- define "kanbn.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "kanbn.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the web image reference.
*/}}
{{- define "kanbn.image" -}}
{{- printf "%s:%s" .Values.image.repository (.Values.image.tag | default .Chart.AppVersion) }}
{{- end }}

{{/*
Create the migrate image reference.
*/}}
{{- define "kanbn.migrateImage" -}}
{{- printf "%s:%s" .Values.migrateImage.repository (.Values.migrateImage.tag | default .Chart.AppVersion) }}
{{- end }}

{{/*
Secret name for app and database credentials.
*/}}
{{- define "kanbn.secretName" -}}
{{- default (include "kanbn.fullname" .) .Values.secret.name }}
{{- end }}

{{/*
PostgreSQL service name.
*/}}
{{- define "kanbn.postgresql.fullname" -}}
{{- printf "%s-postgresql" (include "kanbn.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
PostgreSQL PVC name.
*/}}
{{- define "kanbn.postgresql.claimName" -}}
{{- printf "%s-data" (include "kanbn.postgresql.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
PostgreSQL URL with shell-expanded password.
*/}}
{{- define "kanbn.postgresUrl" -}}
{{- printf "postgresql://%s:$(POSTGRES_PASSWORD)@%s:%v/%s" .Values.postgresql.username (include "kanbn.postgresql.fullname" .) (.Values.postgresql.port | int) .Values.postgresql.database }}
{{- end }}
