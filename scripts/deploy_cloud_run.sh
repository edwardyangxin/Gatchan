#!/usr/bin/env bash
set -euo pipefail

SERVICE=${SERVICE:?Set SERVICE (Cloud Run service name)}
REGION=${REGION:?Set REGION (Cloud Run region)}
IMAGE_PACKAGE=${IMAGE_PACKAGE:?Set IMAGE_PACKAGE (Artifact Registry package path)}
KEEP=${KEEP:-1}

ARTIFACT_REPOSITORY=${ARTIFACT_REPOSITORY:-}
ARTIFACT_LOCATION=${ARTIFACT_LOCATION:-$REGION}
CLEANUP_POLICY_FILE=${CLEANUP_POLICY_FILE:-}

if [[ -n "${ARTIFACT_REPOSITORY}" && -n "${CLEANUP_POLICY_FILE}" ]]; then
  gcloud artifacts repositories set-cleanup-policies "${ARTIFACT_REPOSITORY}" \
    --location "${ARTIFACT_LOCATION}" \
    --policy "${CLEANUP_POLICY_FILE}"
fi

gcloud run deploy "${SERVICE}" \
  --source . \
  --region "${REGION}" \
  "$@"

python3 scripts/prune_cloud_run_artifacts.py \
  --service "${SERVICE}" \
  --region "${REGION}" \
  --image "${IMAGE_PACKAGE}" \
  --keep "${KEEP}"
