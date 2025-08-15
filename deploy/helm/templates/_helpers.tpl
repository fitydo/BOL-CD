{{- define "bolcd.name" -}}
bolcd
{{- end -}}

{{- define "bolcd.fullname" -}}
{{ include "bolcd.name" . }}
{{- end -}}

{{- define "bolcd.serviceAccountName" -}}
{{- if .Values.serviceAccount.name -}}
{{ .Values.serviceAccount.name }}
{{- else -}}
{{ include "bolcd.fullname" . }}
{{- end -}}
{{- end -}}

{{- define "bolcd.jobsServiceAccountName" -}}
{{- if .Values.jobServiceAccount.name -}}
{{ .Values.jobServiceAccount.name }}
{{- else -}}
{{ include "bolcd.fullname" . }}-jobs
{{- end -}}
{{- end -}}

