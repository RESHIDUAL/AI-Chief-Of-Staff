#!/usr/bin/env bash
# AI Chief of Staff — GCP Infrastructure Provisioning & Deployment Script

set -e

PROJECT_ID=${1:-"ai-chief-of-staff-prod"}
REGION="us-central1"

echo "=== 1. Setting GCP Project: ${PROJECT_ID} ==="
gcloud config set project ${PROJECT_ID}

echo "=== 2. Enabling Required GCP APIs ==="
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  pubsub.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com

echo "=== 3. Creating Artifact Registry Repository ==="
gcloud artifacts repositories create cos-repo \
  --repository-format=docker \
  --location=${REGION} \
  --description="AI Chief of Staff Container Registry" || true

echo "=== 4. Creating Cloud Pub/Sub Topic & Subscription ==="
gcloud pubsub topics create meeting-transcripts-topic || true
gcloud pubsub subscriptions create meeting-transcripts-sub \
  --topic=meeting-transcripts-topic \
  --push-endpoint="https://cos-backend-${PROJECT_ID}.${REGION}.run.app/api/v1/ingest/pubsub" || true

echo "=== 5. Deploying via Cloud Build ==="
gcloud builds submit --config=cloudbuild.yaml .

echo "=== GCP Infrastructure Provisioning Complete! ==="
