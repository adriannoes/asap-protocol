{{/*
Common labels for ASAP agent resources
*/}}
{{- define "asap-agent.labels" -}}
app: asap-agent
app.kubernetes.io/name: asap-protocol
app.kubernetes.io/component: agent
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ include "asap-agent.chart" . }}
{{- end }}

{{- define "asap-agent.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end }}

{{- define "asap-agent.selectorLabels" -}}
app: asap-agent
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "asap-agent.fullname" -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
