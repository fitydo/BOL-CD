#!/usr/bin/env bash
set -euo pipefail

# BOL-CD Kubernetes preflight/postflight checker
#
# Usage:
#   scripts/k8s-preflight.sh [namespace] [--release bolcd] [--reports-pvc <name>] [--logs-pvc <name>] \
#                            [--require-external-secrets] [--check-post]
#
# Examples:
#   scripts/k8s-preflight.sh bolcd-prod --release bolcd --require-external-secrets
#   scripts/k8s-preflight.sh bolcd-prod --release bolcd --reports-pvc bolcd-reports --check-post

NS="bolcd"
RELEASE="bolcd"
REPORTS_PVC=""
LOGS_PVC=""
REQUIRE_ES=0
CHECK_POST=0

# Optional first positional argument: namespace (defaults to "bolcd")
if [[ $# -gt 0 && "$1" != --* ]]; then
  NS="$1"; shift || true
fi
while [[ $# -gt 0 ]]; do
  case "$1" in
    --release) RELEASE="$2"; shift 2;;
    --reports-pvc) REPORTS_PVC="$2"; shift 2;;
    --logs-pvc) LOGS_PVC="$2"; shift 2;;
    --require-external-secrets) REQUIRE_ES=1; shift;;
    --check-post) CHECK_POST=1; shift;;
    *) echo "Unknown arg: $1" >&2; exit 2;;
  esac
done

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl is required" >&2
  exit 2
fi

echo "[info] Namespace           : ${NS}"
echo "[info] Release             : ${RELEASE}"

if [[ -z "${REPORTS_PVC}" ]]; then
  REPORTS_PVC="${RELEASE}-reports"
fi
if [[ -z "${LOGS_PVC}" ]]; then
  LOGS_PVC="${RELEASE}-logs"
fi

PASS=()
FAIL=()
WARN=()

_ok() { echo "[ok]   $1"; PASS+=("$1"); }
_fail() { echo "[fail] $1"; FAIL+=("$1"); }
_warn() { echo "[warn] $1"; WARN+=("$1"); }

_ns() { kubectl -n "$NS" "$@"; }

echo "[info] kubectl context     : $(kubectl config current-context 2>/dev/null || echo '-')"
kubectl version --short >/dev/null 2>&1 && _ok "kubectl reachable" || _warn "kubectl version check failed (continuing)"

echo "\n== Preflight: Secrets =="
if _ns get secret bolcd-apikeys >/dev/null 2>&1; then
  if [[ -n "$(_ns get secret bolcd-apikeys -o jsonpath='{.data.BOLCD_API_KEYS}' 2>/dev/null)" ]]; then
    _ok "secret/bolcd-apikeys with key BOLCD_API_KEYS"
  else
    _fail "secret/bolcd-apikeys exists but missing key BOLCD_API_KEYS"
  fi
else
  _fail "secret/bolcd-apikeys not found"
fi

if _ns get secret bolcd-secrets >/dev/null 2>&1; then
  MISSING=()
  for k in splunk_url splunk_token; do
    if [[ -z "$(_ns get secret bolcd-secrets -o jsonpath="{.data.${k}}" 2>/dev/null)" ]]; then
      MISSING+=("$k")
    fi
  done
  if [[ ${#MISSING[@]} -eq 0 ]]; then
    _ok "secret/bolcd-secrets has Splunk keys (splunk_url,splunk_token)"
  else
    _fail "secret/bolcd-secrets missing keys: ${MISSING[*]}"
  fi
  # Optional keys (warn only)
  for k in sentinel_workspace_id azure_token azure_subscription_id azure_resource_group azure_workspace_name opensearch_endpoint opensearch_basic; do
    if [[ -z "$(_ns get secret bolcd-secrets -o jsonpath="{.data.${k}}" 2>/dev/null)" ]]; then
      _warn "secret/bolcd-secrets optional key missing: ${k}"
    fi
  done
else
  _fail "secret/bolcd-secrets not found"
fi

if [[ $REQUIRE_ES -eq 1 ]]; then
  echo "\n== Preflight: ExternalSecrets =="
  if _ns api-resources --api-group=external-secrets.io >/dev/null 2>&1; then
    if _ns get externalsecret >/dev/null 2>&1; then
      # Print brief status
      _ns get externalsecret -o wide || true
      _ok "ExternalSecrets API and resources present"
    else
      _fail "ExternalSecrets CRD present but no ExternalSecret found"
    fi
  else
    _fail "ExternalSecrets API not available in cluster"
  fi
fi

echo "\n== Preflight: StorageClass & PVC (advisory) =="
if kubectl get sc >/dev/null 2>&1; then
  DEFAULT_SC=$(kubectl get sc -o jsonpath='{range .items[?(@.metadata.annotations.storageclass\.kubernetes\.io/is-default-class=="true")]}{.metadata.name}{"\n"}{end}' || true)
  if [[ -n "$DEFAULT_SC" ]]; then
    _ok "default StorageClass: ${DEFAULT_SC}"
  else
    _warn "no default StorageClass detected"
  fi
else
  _warn "cannot list StorageClasses (RBAC?)"
fi

for PVC in "$REPORTS_PVC" "$LOGS_PVC"; do
  if _ns get pvc "$PVC" >/dev/null 2>&1; then
    PHASE=$(_ns get pvc "$PVC" -o jsonpath='{.status.phase}' 2>/dev/null || true)
    if [[ "$PHASE" == "Bound" ]]; then
      _ok "pvc/${PVC} is Bound"
    else
      _warn "pvc/${PVC} exists but not Bound (phase=${PHASE})"
    fi
  else
    _warn "pvc/${PVC} not found (Helm may create it)"
  fi
done

if [[ $CHECK_POST -eq 1 ]]; then
  echo "\n== Postflight: Workloads (after Helm apply) =="
  if _ns get deploy "$RELEASE" >/dev/null 2>&1; then
    if _ns rollout status deploy/"$RELEASE" --timeout=300s; then
      _ok "deployment/${RELEASE} Ready"
    else
      _fail "deployment/${RELEASE} failed to become Ready"
    fi
  else
    _fail "deployment/${RELEASE} not found"
  fi

  # CronJobs (optional, report-only)
  for CJ in "${RELEASE}-ab-daily" "${RELEASE}-cleanup" "${RELEASE}-ab-weekly" "${RELEASE}-ab-notify"; do
    if _ns get cronjob "$CJ" >/dev/null 2>&1; then
      SCHED=$(_ns get cronjob "$CJ" -o jsonpath='{.spec.schedule}' 2>/dev/null || true)
      _ok "cronjob/${CJ} present (schedule=${SCHED})"
    fi
  done
fi

echo "\n== Summary =="
echo "Passed : ${#PASS[@]}"
echo "Warnings: ${#WARN[@]}"
echo "Failed : ${#FAIL[@]}"
if [[ ${#FAIL[@]} -gt 0 ]]; then
  exit 1
fi
exit 0


