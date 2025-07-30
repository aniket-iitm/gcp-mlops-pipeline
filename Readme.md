# Comprehensive MLOps CI/CD Pipeline Guide (Generalized)

**Purpose:**  
This detailed, end-to-end guide provides all the steps and explanations needed to build, secure, deploy, autoscale, observe, load-test, and manage costs for any machine learning service on Kubernetes. Although examples use GCP/GKE, the patterns and commands can be adapted to AWS/EKS, Azure/AKS, or on-prem Kubernetes with minimal changes.

---

## Table of Contents

1. [Project Goal & Reference Architecture](#1-project-goal--reference-architecture)  
2. [Prerequisites](#2-prerequisites)  
3. [Phase 1: Cloud Project & API Setup](#3-phase-1-cloud-project--api-setup)  
4. [Phase 2: Kubernetes Cluster Creation (Standard & Managed)](#4-phase-2-kubernetes-cluster-creation-standard--managed)  
5. [Phase 3: Container Registry & CI/CD Service Account](#5-phase-3-container-registry--cicd-service-account)  
6. [Phase 4: Workload Identity (Pod-to-Cloud Authentication)](#6-phase-4-workload-identity-pod-to-cloud-authentication)  
7. [Phase 5: Project Structure & Core Files](#7-phase-5-project-structure--core-files)  
8. [Phase 6: Dockerfile & Dependency Management](#8-phase-6-dockerfile--dependency-management)  
9. [Phase 7: Telemetry & Health Checks](#9-phase-7-telemetry--health-checks)  
10. [Phase 8: Kubernetes Manifests & Autoscaling (HPA)](#10-phase-8-kubernetes-manifests--autoscaling-hpa)  
11. [Phase 9: Live Load Testing with Locust](#11-phase-9-live-load-testing-with-locust)  
12. [Phase 10: CI/CD Workflows](#12-phase-10-cicd-workflows)  
    1. [10.1 Build & Deploy on Push (ci-cd.yml)](#121-build--deploy-on-push-ci-cdyml)  
    2. [10.2 Continuous Deployment on Pull Request](#122-continuous-deployment-on-pull-request)  
13. [Phase 11: Cleanup & Pause Methods to Stop Charges](#13-phase-11-cleanup--pause-methods-to-stop-charges)  
14. [Appendix A: Required Cloud APIs/Services](#14-appendix-a-required-cloud-apisservices)  
15. [Appendix B: Verification & Troubleshooting Commands](#15-appendix-b-verification--troubleshooting-commands)  

---

## 1. Project Goal & Reference Architecture

**Objective:**  
Automate the ML service lifecycle from code commit to production-ready deployment, ensuring:

- **CI:** Build, linting, unit/integration tests  
- **CD:** Immutable Docker images, zero-downtime rollouts  
- **Security:** Pod-to-cloud authentication via Workload Identity (no static keys)  
- **Reliability:** Health checks (liveness, readiness)  
- **Scalability:** Horizontal Pod Autoscaler (HPA) based on CPU or custom metrics  
- **Observability:** Structured logging, distributed tracing, metrics dashboards  
- **Performance Validation:** Load testing with Locust  
- **Cost Management:** Cleanup or pause resources to avoid charges

**High-Level Architecture:**
```
Developer → GitHub Repository
     │           │
     │ Push/PR   │
     ▼           ▼
 GitHub Actions  → Artifact Registry
     │                             │
     │ Build & Test, Train         │ Pull & Deploy Image
     ▼                             ▼
Kubernetes Cluster (Standard/Managed)
     ├─ Workload Identity → IAM
     ├─ Liveness/Readiness Probes
     ├─ HPA (CPU/Custom Metrics)
     └─ Observability (Logging, Metrics, Trace)
                     │
                     └─ Monitoring UI / Grafana
```

---

## 2. Prerequisites

- **Cloud CLI:** `gcloud`, `aws`, or `az` installed and authenticated  
- **kubectl:** Installed and configured  
- **Docker:** Installed locally or on CI runner  
- **GitHub Repo:** Initialized with `main` and `dev` branches  
- **GitHub Secrets:**  
  - `CLOUD_PROJECT_ID`  
  - `CI_CD_SA_KEY` (contents of service account key JSON)  
  - `CLUSTER_NAME`  
  - `CLUSTER_ZONE` or `CLUSTER_REGION`  
  - `REGISTRY_LOCATION`, `REGISTRY_REPO`  

---

## 3. Phase 1: Cloud Project & API Setup

### 3.1 Create or Select a Cloud Project

**GCP (Console):**  
1. Go to https://console.cloud.google.com/  
2. Create/new project → note **Project ID**.  
3. (Optional) Link a billing account.

**GCP (CLI):**
```bash
gcloud projects create my-mlops-project --name="MLOps Demo"
gcloud config set project my-mlops-project
gcloud config set compute/region us-central1
gcloud config set compute/zone us-central1-a
```

**AWS / Azure:**  
- AWS: `aws configure`  
- Azure: `az account set --subscription "<ID>"` & `az configure --defaults location=<region>`

### 3.2 Enable Required Cloud APIs or Services

| Service                        | GCP CLI                                                          | AWS Equivalent                         | Azure Equivalent                         |
|--------------------------------|------------------------------------------------------------------|----------------------------------------|-------------------------------------------|
| Kubernetes Engine (EKS/AKS)    | `gcloud services enable container.googleapis.com`               | EKS default                            | AKS default                               |
| Compute                        | `gcloud services enable compute.googleapis.com`                 | EC2/EKS                                | Compute                                   |
| Container Registry (ECR/ACR)   | `gcloud services enable artifactregistry.googleapis.com`        | `aws ecr create-repository ...`        | `az acr create ...`                       |
| IAM Credentials                | `gcloud services enable iamcredentials.googleapis.com`          | IAM                                    | Managed Identities                        |
| Logging                        | `gcloud services enable logging.googleapis.com`                 | CloudWatch                             | Azure Monitor / Log Analytics             |
| Monitoring                     | `gcloud services enable monitoring.googleapis.com`              | CloudWatch                             | Azure Monitor                             |
| Tracing                        | `gcloud services enable cloudtrace.googleapis.com`              | X-Ray                                  | Application Insights                      |

Verify:
```bash
gcloud services list --enabled
```

---

## 4. Phase 2: Kubernetes Cluster Creation (Standard & Managed)

### 4.1 Standard (User-Managed) Cluster

**GKE Console:**  
- Kubernetes Engine → Clusters → Create → Standard  
- Name: `mlops-standard`, Region: `us-central1`, Node Pool: 2 × `e2-medium`  
- Click **Create**.

**GCP CLI:**  
```bash
gcloud container clusters create mlops-standard \
  --region=us-central1 \
  --num-nodes=2 \
  --machine-type=e2-medium
```

**AWS EKS (eksctl):**  
```bash
eksctl create cluster \
  --name mlops-standard \
  --region us-west-2 \
  --nodes 2 --node-type t3.medium
```

**Azure AKS:**  
```bash
az aks create \
  --resource-group my-aks-rg \
  --name mlops-standard \
  --node-count 2 \
  --node-vm-size Standard_DS2_v2 \
  --generate-ssh-keys
```

### 4.2 Managed (Autopilot / Fargate) Cluster

**GKE Console:**  
- Kubernetes Engine → Clusters → Create → Autopilot  

**GCP CLI:**  
```bash
gcloud container clusters create-auto mlops-auto \
  --region=us-central1
```

**AWS Fargate:**  
- EKS → Fargate Profiles → Add profile for namespace  

**Azure Virtual Nodes:**  
- AKS → Virtual Node → Enable  

**Key Differences:**  
- **Standard:** You manage nodes (scale, patch, upgrade). Billed per VM uptime.  
- **Managed (Autopilot/Fargate):** Provider manages nodes. Billed for Pod resource requests. No direct node access.

### 4.3 Connect kubectl

```bash
# GKE Standard
gcloud container clusters get-credentials mlops-standard --region=us-central1

# GKE Autopilot
gcloud container clusters get-credentials mlops-auto --region=us-central1

# AWS EKS
aws eks update-kubeconfig --name mlops-standard --region us-west-2

# Azure AKS
az aks get-credentials --resource-group my-aks-rg --name mlops-standard
```

Verify:
```bash
kubectl get nodes
```

---

## 5. Phase 3: Container Registry & CI/CD Service Account

### 5.1 Create Container Registry

**GCP Console:**  
- Artifact Registry → Create Repository →  
  - Name: `mlops-images`  
  - Format: Docker  
  - Location: `us-central1`

**GCP CLI:**  
```bash
gcloud artifacts repositories create mlops-images \
  --repository-format=docker \
  --location=us-central1
```

**AWS ECR:**  
```bash
aws ecr create-repository --repository-name mlops-images --region us-west-2
```

**Azure ACR:**  
```bash
az acr create --resource-group my-aks-rg --name mlopsImages --sku Basic
```

### 5.2 Create CI/CD Service Account

**Why:** CI/CD runner needs permissions to build/push images and deploy to Kubernetes.

**GCP Console:**  
1. IAM & Admin → Service Accounts → Create → `cicd-deployer`  
2. Grant Roles:  
   - Artifact Registry Writer (`roles/artifactregistry.writer`)  
   - Kubernetes Engine Developer (`roles/container.developer`)  
3. Create and download JSON key (`cicd-deployer-key.json`).

**GCP CLI:**  
```bash
gcloud iam service-accounts create cicd-deployer --display-name="CI/CD Deployer"

gcloud projects add-iam-policy-binding my-mlops-project \
  --member="serviceAccount:cicd-deployer@my-mlops-project.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding my-mlops-project \
  --member="serviceAccount:cicd-deployer@my-mlops-project.iam.gserviceaccount.com" \
  --role="roles/container.developer"

gcloud iam service-accounts keys create cicd-deployer-key.json \
  --iam-account="cicd-deployer@my-mlops-project.iam.gserviceaccount.com"
```

**AWS IAM / Azure AD:**  
- Create user/role or service principal with equivalent registry & cluster permissions.

---

## 6. Phase 4: Workload Identity (Pod-to-Cloud Authentication)

### 6.1 Why Workload Identity?

- Removes static JSON keys from Pods.  
- Uses short-lived tokens bound to Pod’s Kubernetes Service Account (KSA).  
- GSA (Google Service Account) holds IAM roles; KSA impersonates GSA.

### 6.2 Enable Workload Identity on GKE

**GCP CLI:**  
```bash
gcloud container clusters create mlops-standard \
  --region=us-central1 \
  --workload-pool=my-mlops-project.svc.id.goog \
  --num-nodes=2
```

For existing cluster:
```bash
gcloud container clusters update mlops-standard \
  --region=us-central1 \
  --update-addons=GcpFilestoreCsiDriver \
  --workload-pool=my-mlops-project.svc.id.goog
```

### 6.3 Create and Bind Service Accounts

1. **Create GSA & Grant Roles**  
   ```bash
   gcloud iam service-accounts create telemetry-access \
     --display-name="Telemetry Access"

   gcloud projects add-iam-policy-binding my-mlops-project \
     --member="serviceAccount:telemetry-access@my-mlops-project.iam.gserviceaccount.com" \
     --role="roles/logging.logWriter"

   gcloud projects add-iam-policy-binding my-mlops-project \
     --member="serviceAccount:telemetry-access@my-mlops-project.iam.gserviceaccount.com" \
     --role="roles/cloudtrace.agent"
   ```

2. **Create KSA**  
   ```bash
   kubectl create serviceaccount telemetry-access --namespace default
   ```

3. **Allow Impersonation**  
   ```bash
   gcloud iam service-accounts add-iam-policy-binding \
     telemetry-access@my-mlops-project.iam.gserviceaccount.com \
     --member="serviceAccount:my-mlops-project.svc.id.goog[default/telemetry-access]" \
     --role="roles/iam.workloadIdentityUser"
   ```

4. **Annotate KSA**  
   ```bash
   kubectl annotate serviceaccount telemetry-access \
     --namespace default \
     iam.gke.io/gcp-service-account=telemetry-access@my-mlops-project.iam.gserviceaccount.com
   ```

### 6.4 Verification

```bash
kubectl describe serviceaccount telemetry-access --namespace default
gcloud iam service-accounts get-iam-policy telemetry-access@my-mlops-project.iam.gserviceaccount.com
```

**Test with a Pod:**
```bash
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata: { name: wai-test }
spec:
  serviceAccountName: telemetry-access
  containers:
    - name: curl
      image: curlimages/curl
      command:
        - "sh"
        - "-c"
        - |
          curl -H "Metadata-Flavor: Google" \
            http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token
EOF
kubectl logs wai-test
```

Expected: JSON with `access_token`.

---

## 7. Phase 5: Project Structure & Core Files

```
project-root/
├── app/
│   └── main.py         # FastAPI + OpenTelemetry + JSON logging + health checks
├── artifacts/
│   └── model.joblib    # Trained model artifact
├── data/               # Training data (optional)
├── k8s/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── hpa.yaml
├── tests/              # pytest tests
│   └── test_predict.py
├── Dockerfile
├── locustfile.py
├── requirements.txt
├── train.py            # Model training script
├── README.md
└── .github/
    └── workflows/
        ├── ci-cd.yml
        └── continuous-deployment-to-gke.yml
```

---

## 8. Phase 6: Dockerfile & Dependency Management

### Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source code and artifacts
COPY . .

# Expose application port
EXPOSE 8000

# Run the FastAPI app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### requirements.txt
```txt
fastapi
uvicorn[standard]
joblib
scikit-learn
pandas
opentelemetry-api
opentelemetry-sdk
opentelemetry-instrumentation-fastapi
opentelemetry-exporter-cloud-trace
requests
locust
pytest
```

---

## 9. Phase 7: Telemetry & Health Checks

### 9.1 OpenTelemetry Tracing & Logging

In `app/main.py`, set up:
- **TracerProvider** & **BatchSpanProcessor**  
- **CloudTraceSpanExporter**  
- **FastAPIInstrumentor**  
- **JSONFormatter** for structured logs with `trace_id` & `span_id`

### 9.2 Health Check Endpoints

```python
@app.get("/live_check")
def liveness_probe():
    return {"status": "alive"}

@app.get("/ready_check")
def readiness_probe():
    if model: return {"status": "ready"}
    return Response(status_code=503)
```

- **Liveness:** Kubernetes kills & restarts unhealthy containers.  
- **Readiness:** Kubernetes only routes traffic to ready Pods.

---

## 10. Phase 8: Kubernetes Manifests & Autoscaling (HPA)

### deployment.yaml
```yaml
apiVersion: apps/v1
kind: Deployment
metadata: { name: iris-classifier-deployment }
spec:
  replicas: 2
  selector:
    matchLabels: { app: iris-classifier }
  template:
    metadata: { labels: { app: iris-classifier } }
    spec:
      serviceAccountName: telemetry-access
      containers:
        - name: iris-api
          image: DOCKER_IMAGE_PLACEHOLDER
          ports:
            - containerPort: 8000
          readinessProbe:
            httpGet: { path: /ready_check, port: 8000 }
            initialDelaySeconds: 10
            periodSeconds: 5
          livenessProbe:
            httpGet: { path: /live_check, port: 8000 }
            initialDelaySeconds: 15
            periodSeconds: 20
          resources:
            requests: { cpu: "100m", memory: "128Mi" }
            limits:   { cpu: "500m", memory: "256Mi" }
```

### service.yaml
```yaml
apiVersion: v1
kind: Service
metadata: { name: iris-classifier-service }
spec:
  type: LoadBalancer
  selector: { app: iris-classifier }
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
```

### hpa.yaml
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata: { name: iris-classifier-hpa }
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: iris-classifier-deployment
  minReplicas: 2
  maxReplicas: 5
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 60
```

**Apply all manifests:**
```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/hpa.yaml
```

---

## 11. Phase 9: Live Load Testing with Locust

### 11.1 Retrieve External IP
```bash
export SERVICE_IP=$(kubectl get svc iris-classifier-service \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo "Model API URL: http://$SERVICE_IP"
```

### 11.2 locustfile.py
```python
from locust import HttpUser, task, between
import random

class IrisApiUser(HttpUser):
    wait_time = between(0.5, 2.5)

    @task
    def make_prediction(self):
        payload = {
            "sepal_length": round(random.uniform(4.0, 8.0), 1),
            "sepal_width":  round(random.uniform(2.0, 4.5), 1),
            "petal_length": round(random.uniform(1.0, 7.0), 1),
            "petal_width":  round(random.uniform(0.1, 2.5), 1)
        }
        self.client.post("/predict", json=payload, name="/predict")
```

### 11.3 Run Locust
```bash
pip install locust
locust --headless --users 1000 --spawn-rate 50 --host=http://$SERVICE_IP
# Or interactive:
locust --host=http://$SERVICE_IP
# Access UI at http://localhost:8089
```

### 11.4 Key Observations
- **HPA Scaling:**  
  ```bash
  kubectl get hpa iris-classifier-hpa --watch
  ```
- **Logs:** Cloud Logging / `kubectl logs`  
- **Traces:** Cloud Trace / Jaeger  
- **Pod Rollouts:**  
  ```bash
  kubectl rollout restart deployment iris-classifier-deployment
  kubectl rollout status deployment iris-classifier-deployment
  ```
- **Metrics Dashboards:** CPU, memory, latency percentiles

---

## 12. Phase 10: CI/CD Workflows

### 12.1 Build & Deploy on Push (`ci-cd.yml`)
```yaml
name: CI/CD on Push
on:
  push:
    branches: [ main, dev ]

jobs:
  build-test-deploy:
    runs-on: ubuntu-latest
    permissions: { contents: write, id-token: write }
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with: { python-version: "3.11" }
      - run: pip install -r requirements.txt && pytest
      - uses: google-github-actions/auth@v2
        with: { credentials_json: ${{ secrets.CI_CD_SA_KEY }} }
      - uses: google-github-actions/setup-gcloud@v2
      - run: gcloud auth configure-docker ${{ secrets.REGISTRY_LOCATION }}-docker.pkg.dev --quiet
      - run: |
          IMAGE="${{ secrets.REGISTRY_LOCATION }}-docker.pkg.dev/${{ secrets.CLOUD_PROJECT_ID }}/${{ secrets.REGISTRY_REPO }}/iris:${{ github.sha }}"
          docker build -t $IMAGE .
          docker push $IMAGE
          sed -i "s|DOCKER_IMAGE_PLACEHOLDER|$IMAGE|g" k8s/deployment.yaml
      - run: |
          gcloud container clusters get-credentials ${{ secrets.CLUSTER_NAME }} --zone ${{ secrets.CLUSTER_ZONE }}
          kubectl apply -f k8s/
          kubectl rollout status deployment iris-classifier-deployment
```

### 12.2 Continuous Deployment on Pull Request
```yaml name=.github/workflows/continuous-deployment-to-gke.yml
name: Continuous Deployment to GKE

on:
  pull_request:
    branches: [ main ]

env:
  CLOUD_PROJECT_ID: ${{ secrets.CLOUD_PROJECT_ID }}
  CLUSTER_NAME: ${{ secrets.CLUSTER_NAME }}
  CLUSTER_ZONE: ${{ secrets.CLUSTER_ZONE }}
  REGISTRY_LOCATION: ${{ secrets.REGISTRY_LOCATION }}
  REGISTRY_REPO: ${{ secrets.REGISTRY_REPO }}

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write
      pull-requests: write

    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: google-github-actions/auth@v2
        with: { credentials_json: ${{ secrets.CI_CD_SA_KEY }} }
      - uses: google-github-actions/setup-gcloud@v2
      - run: gcloud components install gke-gcloud-auth-plugin --quiet
      - run: pip install -r requirements.txt
      - run: python train.py
      - run: gcloud auth configure-docker $REGISTRY_LOCATION-docker.pkg.dev --quiet
      - id: build-image
        run: |
          IMAGE="$REGISTRY_LOCATION-docker.pkg.dev/$CLOUD_PROJECT_ID/$REGISTRY_REPO/iris:${GITHUB_SHA}"
          docker build -t $IMAGE .
          docker push $IMAGE
          echo "IMAGE_NAME=$IMAGE" >> $GITHUB_OUTPUT
      - run: |
          gcloud container clusters get-credentials $CLUSTER_NAME --zone $CLUSTER_ZONE
          sed -i "s|DOCKER_IMAGE_PLACEHOLDER|${{ steps.build-image.outputs.IMAGE_NAME }}|g" k8s/deployment.yaml
          kubectl apply -f k8s/deployment.yaml
          kubectl apply -f k8s/service.yaml
          kubectl apply -f k8s/hpa.yaml
          kubectl rollout status deployment iris-classifier-deployment
      - run: |
          sleep 60
          IP=$(kubectl get svc iris-classifier-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
          cat <<EOF > report.md
          🚀 Deployment successful!  
          Service endpoint: http://$IP/predict  
          EOF
          npm install -g @dvcorg/cml
          cml comment create report.md
```

---

## 13. Phase 11: Cleanup & Pause Methods to Stop Charges

### Full Cleanup
```bash
kubectl delete -f k8s/
gcloud container clusters delete mlops-standard --region=us-central1 --quiet
gcloud artifacts repositories delete mlops-images --location=us-central1 --quiet
gcloud iam service-accounts delete cicd-deployer@my-mlops-project.iam.gserviceaccount.com --quiet
gcloud iam service-accounts delete telemetry-access@my-mlops-project.iam.gserviceaccount.com --quiet
```

### Pause Cluster (Keep Config)

- **Standard GKE:**  
  ```bash
  gcloud container clusters resize mlops-standard \
    --region=us-central1 --node-pool=default-pool --num-nodes=0 --quiet
  ```
- **Autopilot GKE:**  
  ```bash
  kubectl scale deployment iris-classifier-deployment --replicas=0
  ```

**Un-Pause:**  
- Standard: resize node pools back up  
- Managed: scale deployments/statefulsets back to desired replicas

---

## 14. Appendix A: Required Cloud APIs/Services

- **Kubernetes Engine / EKS / AKS**  
- **Compute / EC2 / VMs**  
- **Artifact Registry / ECR / ACR**  
- **IAM Credentials**  
- **Logging**  
- **Monitoring**  
- **Tracing**

---

## 15. Appendix B: Verification & Troubleshooting Commands

```bash
kubectl get nodes,deployments,services,pods
kubectl get hpa iris-classifier-hpa
kubectl logs deployment iris-classifier-deployment
gcloud logging read "resource.type=k8s_container" --limit=10
gcloud trace spans list --project=my-mlops-project
kubectl top pods
kubectl apply -f k8s/deployment.yaml --dry-run=client
```

**Common Issues & Solutions:**
- **API Not Enabled:** enable via console or CLI  
- **IAM Errors:** verify service account roles  
- **Pods Pending:** check resource requests, cluster capacity  
- **Health Probes Failing:** verify endpoints & delays  
- **ImagePullBackOff:** confirm image name/tag and registry auth  
- **Workflow YAML Errors:** validate with a linter  

---

> **Pro Tip:**  
> - Use Infrastructure-as-Code (Terraform, CloudFormation, ARM) for repeatable provisioning.  
> - Abstract environment-specific values into variables or CI/CD secrets.  
> - Modularize manifests with Helm or Kustomize for multi-project reuse.  
> - Maintain separate `dev`, `staging`, and `prod` configurations for safe promotion.  

Congratulations! You now have a fully detailed, generalizable MLOps CI/CD pipeline guide ready for any ML service on Kubernetes.  