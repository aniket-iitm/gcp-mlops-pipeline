# Hands-On Guide: Building a General MLOps CI/CD Pipeline for ML Model Deployment

This document is a comprehensive, step-by-step guide for building a reliable, automated MLOps pipeline. The goal: Take any machine learning model, package it as a web service, and deploy it seamlessly with full Continuous Integration and Continuous Deployment (CI/CD) to a cloud-based Kubernetes cluster.

---

## 1. Project Goal & Reference Architecture

**Objective:**  
Set up a system where a code update (via `git push` or Pull Request merge) triggers a pipeline to:
- Train and save a machine learning model (if needed)
- Package it within a web service (e.g., FastAPI, Flask, etc.)
- Build a Docker image for the service
- Push the image to a secure container registry (e.g., GCP Artifact Registry, AWS ECR, Azure Container Registry)
- Deploy the image to a managed Kubernetes cluster
- Report deployment status and live API endpoint to developers

**Core Technologies (Generalized):**
- **Cloud Platform:** GCP, AWS, Azure, or similar
- **Containerization & Orchestration:** Docker, Kubernetes Engine, Managed Container Registry
- **Application:** Python (FastAPI, Flask), R, Node.js, etc.
- **Automation (CI/CD):** Git, GitHub Actions, GitLab CI, Jenkins, etc.
- **Reporting:** CML, Slack notifications, GitHub PR comments
- **Python Tooling:** uv, pip, poetry, conda, etc.

---

## 2. Phase 1: Cloud Infrastructure Setup (Manual and CLI)

Setting up your cloud infrastructure is the first step. You can do this using your cloud provider’s web console (manual) or their command-line interface (CLI). Both approaches are described below.

---

### 2.1 Set Up Cloud Project & Region

#### Manual (Console/UI)
- Sign in to your cloud provider’s portal:
  - **GCP:** [Google Cloud Console](https://console.cloud.google.com/)
  - **AWS:** [AWS Console](https://console.aws.amazon.com/)
  - **Azure:** [Azure Portal](https://portal.azure.com/)
- Create a **new project** or select an existing one.
- Set your preferred **region/zone** for resources.

#### CLI Example
```bash
# GCP
gcloud projects create <project-id>
gcloud config set project <project-id>
gcloud config set compute/region <region>
gcloud config set compute/zone <zone>

# AWS
aws configure
# Follow prompts for region and output format

# Azure
az account set --subscription "<subscription-id>"
az configure --defaults location=<region>
```
---
### 2.2 Enable Required APIs/Services

#### Manual (Console/UI)
- Navigate to **APIs & Services** (GCP), **Service Catalog** (AWS), or **Resource Providers** (Azure).
- Enable services required for:
  - Kubernetes/Container orchestration
  - Container registry
  - Compute resources
  - IAM/Identity management

  **Examples:**
  - **GCP:** Enable "Kubernetes Engine API", "Artifact Registry API", "Compute Engine API", "IAM Service Account Credentials API"
  - **AWS:** Ensure "EKS", "ECR", "EC2", and "IAM" are activated
  - **Azure:** Enable "AKS", "Container Registry", "VM", "Managed Identities"

#### CLI Example
```bash
# GCP
gcloud services enable \
  compute.googleapis.com \
  container.googleapis.com \
  artifactregistry.googleapis.com \
  iamcredentials.googleapis.com

# AWS: Most services are enabled by default when resources are created
# Azure: Use az provider register if needed
```
---
### 2.3 Create a Managed Kubernetes Cluster
#### Manual (Console/UI)
- Go to **Kubernetes/Container Service**:
  - **GCP:** Kubernetes Engine → Clusters → Create
  - **AWS:** EKS → Clusters → Create
  - **Azure:** AKS → Create
- Specify:
  - Cluster name (e.g., `mlops-cluster`)
  - Location/zone/region
  - Node pool size (e.g., 2 nodes) - Optional.
  - Machine type (e.g., "e2-medium", "t3.medium", "Standard_DS2_v2") - Optional.

#### CLI Example
```bash
# GCP
gcloud container clusters create mlops-cluster \
  --num-nodes=2 \
  --machine-type=e2-medium \
  --zone=<zone> \
  --project=<project-id>

# AWS
eksctl create cluster --name mlops-cluster --region <region> --nodes 2

# Azure
az aks create --resource-group <rg> --name mlops-cluster --node-count 2 --node-vm-size Standard_DS2_v2
```
---
### 2.4 Create a Container Registry

#### Manual (Console/UI)
1. Navigate to **Container/Artifact Registry**:
  - **GCP:** Artifact Registry → Create Repository
  - **AWS:** ECR → Create Repository
  - **Azure:** Container Registry → Create
2. Click **Create Repository**.
3. Set the following options:
   - **Name:** (e.g., `iris-app-repo`)
   - **Format:** Docker
   - **Location:** Select your region (e.g., `us-central1`)
4. Click **Create**.

#### CLI Example
```bash
# GCP
gcloud artifacts repositories create mlops-app-repo \
  --repository-format=docker \
  --location=<region> \
  --project=<project-id>

# AWS
aws ecr create-repository --repository-name mlops-app-repo --region <region>

# Azure
az acr create --resource-group <rg> --name mlopsapprepo --sku Basic --location <region>
```

---

### 2.5 Create a Service Account/User for Automation

#### Manual (Console/UI)
- Go to **IAM & Admin → Service Accounts** (GCP), **IAM → Users/Roles** (AWS), or **Azure AD → App registrations/Managed Identities** (Azure)
- Create a new service account/user (e.g., `cicd-deployer`)
- Grant the following roles:
  - `Artifact Registry Writer`
  - `Kubernetes Engine Developer`
- After creation:
   - Go to the **Keys** tab for this service account.
   - Click **Add Key → Create new key**.
   - Choose **JSON** format and create it.
   - Download and save the JSON key file securely. **This is a critical secret!**

#### CLI Example
```bash
# GCP
gcloud iam service-accounts create cicd-deployer --project=<project-id>
gcloud projects add-iam-policy-binding <project-id> \
  --member="serviceAccount:cicd-deployer@<project-id>.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"
gcloud projects add-iam-policy-binding <project-id> \
  --member="serviceAccount:cicd-deployer@<project-id>.iam.gserviceaccount.com" \
  --role="roles/container.developer"
gcloud iam service-accounts keys create cicd-creds.json \
  --iam-account="cicd-deployer@<project-id>.iam.gserviceaccount.com" \
  --project=<project-id>

# AWS: Use IAM console to create user and assign ECR/EKS permissions, then download credentials

# Azure: Create service principal or managed identity, assign contributor roles
```

## 3. Phase 3: GitHub Repository Setup (Manual and CLI)

Your source code repository is the foundation for version control, collaboration, and automation. Set up GitHub (or similar platform) for your project, organize your workflow, and prepare for CI/CD integration.

---

### 3.1 Create and Initialize Repository

#### Manual (GitHub Web UI)
1. Go to [GitHub.com](https://github.com/) and sign in.
2. Click **New Repository**.
3. Fill in:
   - Repository name (e.g., `mlops-cicd-pipeline`)
   - Description
   - Public or Private visibility
   - Initialize with README (recommended)
4. Click **Create repository**.

#### CLI
```bash
# Locally
git init
git remote add origin https://github.com/<your-username>/<repo-name>.git
git add README.md
git commit -m "Initial commit"
git push -u origin main
```

---

### 3.2 Clone Repository Locally

```bash
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>
```

---

### 3.3 Organize Branches

- Create a development branch for feature work:
  ```bash
  git checkout -b dev
  git push -u origin dev
  ```
- Set up branch protection rules in GitHub:
  - Go to **Settings → Branches**
  - Add a protection rule to `main` (require PR before merging, require status checks, etc.)

---

### 3.4 Add Essential Files

- `.gitignore`  
  Add patterns to exclude artifacts, venvs, and sensitive data from the repository.
- `README.md`  
  Document your pipeline, setup steps, and project purpose.
- `LICENSE`  
  Add a license if you wish to make your code open-source.

---

### 3.5 Configure GitHub Secrets (for CI/CD)

Store sensitive credentials and configuration as GitHub repository secrets for use in your workflow.

**Steps:**
1. Go to your repository on GitHub.
2. Navigate to **Settings → Secrets and variables → Actions**.
3. Add the following secrets:
   - `GCP_PROJECT_ID`: Your GCP Project ID
   - `GCP_SA_KEY`: Paste the entire content of the downloaded JSON key file
   - `GKE_CLUSTER_NAME`: (e.g., `gke-test-cluster`)
   - `GKE_ZONE`: (e.g., `us-central1` or your cluster's location)
   - `ARTIFACT_REGISTRY_REPO`: (e.g., `iris-app-repo`)
   - `ARTIFACT_REGISTRY_LOCATION`: (e.g., `us-central1`)

---

### 3.6 Set Up Actions Workflow Directory

- Create `.github/workflows/` directory to store workflow YAML files.

---

## 4. Phase 4: Application & Pipeline Files

---

### 4.1 Directory Structure (General)
```
.
├── .github/workflows/ci-cd.yml           # CI/CD workflow
├── app/                                  # App code (FastAPI, Flask, etc.)
│   ├── __init__.py
│   └── main.py
├── data/                                 # Data files (optional)
│   └── <dataset>.csv
├── k8s/                                  # Kubernetes manifests
│   ├── deployment.yaml
│   └── service.yaml
├── .gitignore
├── Dockerfile
├── requirements.txt                      # Or environment.yml, pyproject.toml
└── train.py                              # Model training script (optional)
```

### 4.2 Core Files (Descriptions)
- **train.py**: Trains and exports model artifacts
- **app/main.py**: Web service, loads model, exposes endpoints (e.g., `/predict`)
- **requirements.txt**: Pin dependencies
- **Dockerfile**: Containerizes the app
- **k8s/deployment.yaml**: Kubernetes deployment spec (resources, image)
- **k8s/service.yaml**: Exposes your app (LoadBalancer/ClusterIP)
- **.gitignore**: Exclude venvs, artifacts, etc.

---

## Phase 5: Local Validation and Testing (With Troubleshooting)

Local validation and testing are essential steps to catch errors early, save cloud resources, and prevent CI/CD failures. This phase combines practical workflow steps for FastAPI apps and containerized ML services, along with troubleshooting for common issues that arise during development.

---

### 5.1 Test Model Training

**Purpose:** Ensure your model artifacts are generated correctly.

```bash
python train.py
# Verify model artifacts are created (e.g., artifacts/model.joblib)
```

**Error & Solution:**
- **Error:** `ModuleNotFoundError: No module named 'pandas'`
- **Solution:** Install all dependencies first (`pip install -r requirements.txt`) and confirm your training script runs without issues.

---

### 5.2 Test Application Locally

**Purpose:** Check your FastAPI (or other web app) endpoints before containerizing.

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```
- Visit [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for interactive API docs.
- Test endpoints using the UI or:
```bash
curl -X POST http://127.0.0.1:8000/predict -H "Content-Type: application/json" -d '{"feature1": 1, ...}'
```

**Error & Solution:**
- **Error:** App can't find model file or environment variables.
- **Solution:** Make sure model artifacts exist and environment variables are set (`export MODEL_PATH=...` or use a `.env` file).

---

### 5.3 Test Docker Build & Run

**Purpose:** Verify your application works in a container.

```bash
docker build -t my-api:local-test .
docker run -p 8000:8000 --rm my-api:local-test
```
- Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) or use curl to test endpoints.

**Common Docker Errors & Solutions:**
- **Error:** `COPY failed: file not found`
  - **Solution:** Check paths in your Dockerfile and run `docker build` from the repo root.
- **Error:** Permission denied
  - **Solution:** Validate permissions for copied files and use `.dockerignore` to exclude unnecessary files.
- **Error:** Application fails to start in container
  - **Solution:** Ensure all dependencies are installed in the Docker image and entrypoint is correct.

---

### 5.4 Validate Kubernetes Manifests

**Purpose:** Catch YAML syntax and resource errors before deploying.

```bash
kubectl apply -f k8s/deployment.yaml --dry-run=client
kubectl apply -f k8s/service.yaml --dry-run=client
```

**Common Kubernetes Errors & Solutions:**
- **Error:** YAML syntax error
  - **Solution:** Use [yamllint](https://github.com/adrienverge/yamllint) or online YAML validators.
- **Error:** Pods stuck in Pending state after deployment
  - **Solution:** Check resource requests in the manifest and cluster capacity. Lower resource requests if needed:
    ```yaml
    resources:
      requests:
        cpu: "100m"
        memory: "128Mi"
    ```
  - Run `kubectl describe pod <pod-name>` for more details.

---

### 5.5 Run Automated Tests

**Purpose:** Ensure your code and endpoints work as expected.

```bash
pytest  # or your test suite
```
- Place tests in a `tests/` directory.

**Error & Solution:**
- **Error:** Tests fail due to missing dependencies or misconfigured environment.
  - **Solution:** Set up all required environment variables and files before running tests.

---


## 6. Phase 6: CI/CD Workflow Automation

- Create `.github/workflows/ci-cd.yml` (or equivalent for your platform)
- Steps typically include:
  - Checkout code
  - Set up environment
  - Install dependencies
  - Run tests
  - Build Docker image
  - Push to registry
  - Deploy to Kubernetes
  - Report status

---

## 7. Phase 7: Troubleshooting Common Errors

Building and running a CI/CD pipeline for ML model deployment involves many moving parts. Here are common errors you may encounter, their symptoms, and proven solutions:

---

### **7.1 Missing Python Package**

**Symptom:**  
Pipeline fails with `ModuleNotFoundError: No module named 'xxx'` during training, testing, or serving.

**Root Cause:**  
The required Python package is not installed before running the script or service.

**Solution:**  
- Ensure a step to install dependencies (e.g., `pip install -r requirements.txt`) is present and runs **before** any Python command.
- In Docker, confirm your `requirements.txt` is copied into the image **before** `RUN pip install -r requirements.txt`.

---

### **7.2 Cloud Authentication / Plugin Errors**

**Symptom:**  
Deployment steps (e.g., `kubectl` commands) fail with authentication errors, or messages like `gke-gcloud-auth-plugin not found`.

**Root Cause:**  
Missing or misconfigured cloud CLI authentication plugin, or credentials not set up on the runner.

**Solution:**  
- For GKE: Add a step in your workflow to install the plugin:
  ```yaml
  - name: Install gke-gcloud-auth-plugin
    run: gcloud components install gke-gcloud-auth-plugin
  ```
- Ensure cloud credentials are provided as secrets and loaded into the pipeline environment.
- For AWS/Azure: Confirm correct IAM roles/service principals are set and CLI tools are installed.

---

### **7.3 Kubernetes Pods Pending**

**Symptom:**  
`kubectl rollout status` times out; `kubectl get pods` shows pods stuck in `Pending` state.

**Root Cause:**  
Insufficient resources in the cluster, incorrect resource requests, or quota limitations.

**Solution:**  
- Run `kubectl describe pod <pod-name>` and check the `Events` section for clues (e.g., `Insufficient cpu`, `Quota exceeded`).
- Reduce CPU and memory requests in your manifest to fit the available resources:
  ```yaml
  resources:
    requests:
      cpu: "100m"
      memory: "128Mi"
  ```
- Scale up your cluster or request higher quotas from your cloud provider.

---

### **7.4 Permissions Errors in Reporting/Notifications**

**Symptom:**  
Final reporting or notification steps (CML, GitHub comments, Slack, etc.) fail with permissions errors (e.g., `403 Forbidden`, `Resource not accessible by integration`).

**Root Cause:**  
The CI/CD pipeline’s token or identity lacks permission to perform the action (write comments, send notifications).

**Solution:**  
- Explicitly grant permissions in your workflow file:
  ```yaml
  jobs:
    build-and-deploy:
      permissions:
        contents: write
        id-token: write
  ```
- For Slack, ensure your webhook/token is correctly configured and valid.

---

### **7.5 Docker Build Fails (e.g., File Not Found, Permission Errors)**

**Symptom:**  
Docker build fails with errors such as `COPY failed: file not found`, or permission denied.

**Root Cause:**  
Incorrect Dockerfile paths or missing files; build context not set properly.

**Solution:**  
- Verify paths in your Dockerfile (`COPY` and `RUN` commands).
- Run `docker build` from the correct directory (root of the repo).
- Use `.dockerignore` to exclude unnecessary files.

---

### **7.6 Failed Kubernetes Manifest Apply (YAML Errors)**

**Symptom:**  
`kubectl apply` fails with YAML syntax errors.

**Root Cause:**  
Manifest files have incorrect indentation, missing keys, or invalid structure.

**Solution:**  
- Validate manifests locally using:
  ```bash
  kubectl apply -f k8s/deployment.yaml --dry-run=client
  ```
- Use [YAML linters](https://github.com/adrienverge/yamllint) and online validators.

---

### **7.7 Image Pull Errors in Kubernetes**

**Symptom:**  
Pod events show `ImagePullBackOff` or `ErrImagePull`.

**Root Cause:**  
- Docker image not pushed to registry
- Wrong image name/tag
- Authentication issues with registry

**Solution:**  
- Double-check that the image build and push steps succeed.
- Use the full registry path in your Kubernetes manifest (e.g., `gcr.io/project/image:tag`).
- Ensure the cluster has access to the registry (service account, secret).

---

### **7.8 CI/CD Workflow Syntax Errors**

**Symptom:**  
GitHub Actions or CI pipeline fails to start or shows YAML syntax errors.

**Root Cause:**  
Workflow YAML syntax is incorrect.

**Solution:**  
- Validate workflow files with [GitHub Actions Linter](https://github.com/rhysd/actionlint) or similar tools.
- Check indentation, required fields, and job/step formatting.

---

## 8. Phase 8: Execution and Verification

- Push changes:
  ```bash
  git add .
  git commit -m "Add MLOps CI/CD pipeline"
  git push origin dev
  ```
- Monitor CI/CD workflow execution
- Verify:
  - Successful workflow runs
  - Deployed pods/services in Kubernetes
  - Live endpoint returns predictions
  - Status/notifications/reporting

---

> **Tip:**  
> Adapting this guide to your stack (cloud, language, CI/CD tool) gives you a resilient MLOps workflow for rapid, reliable model delivery and scaling.
