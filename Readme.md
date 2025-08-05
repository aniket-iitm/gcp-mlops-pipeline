# Automated Data Poisoning Robustness Pipeline

This document details a robust, general-purpose MLOps pipeline for simulating, testing, and visualizing the impact of data poisoning attacks on a machine learning model. It is based on the scripts and workflow available in the [`aniket-iitm/gcp-mlops-pipeline`](https://github.com/aniket-iitm/gcp-mlops-pipeline) repository, but is designed so you can adapt these steps to any ML project.

---

## 1. Objective

The pipeline extends a classic CI/CD setup into a full experimentation platform that:

- Simulates label poisoning at multiple severity levels.
- Trains and validates a model on each variant of the dataset.
- Enforces a quality gate (accuracy threshold).
- Automatically generates and posts a consolidated, visual experiment report to the relevant GitHub commit/PR.

---

## 2. Architecture & Technology

- **Experiment Orchestration:** GitHub Actions (matrix strategy for parallel jobs)
- **Data Manipulation:** Python, pandas, numpy
- **Model Training & Testing:** scikit-learn, joblib, pytest
- **Visualization:** matplotlib, seaborn
- **Reporting:** Continuous Machine Learning (CML) for rich, visual GitHub PR comments

---

## 3. Scripts & Project Structure

Your repository should contain:

```
.
├── data/
│   └── iris.csv               # Original dataset
├── artifacts/
│   └── model.joblib           # Saved by training
├── poison_data.py             # Simulate label poisoning
├── train.py                   # Train model on poisoned data
├── tests/
│   └── test_data.py           # Validate + save results
├── generate_plots.py          # Generate accuracy/confusion matrix plots
├── plots/
│   └── *.png                  # Saved plots for each run
├── requirements.txt
├── .github/
│   └── workflows/
│       └── experiments.yml    # Automated workflow
```

Each script has a clear, single responsibility:
- **poison_data.py**: Flips a fraction of the data labels.
- **train.py**: Trains a model on a (potentially poisoned) dataset, writes `metrics.txt`.
- **tests/test_data.py**: Validates accuracy and saves predictions in `test_results.json`.
- **generate_plots.py**: Generates a bar chart and confusion matrix for each experiment.
- **(Optional) generate_summary_plot.py**: For a combined final report (if needed).

---

## 4. The Automated Experiment Workflow

### 4.1. Matrix Parallelization

The workflow file, `.github/workflows/experiments.yml`, orchestrates all runs.  
A **matrix strategy** runs multiple jobs in parallel, each with a different level of data poisoning:

```yaml
strategy:
  fail-fast: false
  matrix:
    poison_level: [0, 5, 10, 50]
```

- **fail-fast: false**: Ensures all experiments run, even if one fails.
- Each job uses its own `poison_level` (e.g., 0%, 5%, 10%, 50%).

---

### 4.2. Per-Experiment Execution Steps

Each matrix job proceeds as follows:

1. **Setup**
    - Checkout code.
    - Set up Python and install dependencies.

2. **Data Poisoning**
    - Run `poison_data.py --level X` (where X is `0.05` for 5%, etc).

3. **Model Training**
    - Train with `train.py --data-path data/iris_poisoned.csv`.

4. **Validation & Results**
    - Run `pytest tests/test_data.py` (with `continue-on-error: true` to allow failure).

5. **Plot Generation**
    - Call `generate_plots.py --poison-level X` to create per-experiment plots.

6. **Artifact Upload**
    - Upload `plots/`, `metrics.txt`, and `test_results.json` for aggregation.

**Example job snippet:**

```yaml
jobs:
  run-poisoning-experiment:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        poison_level: [0, 5, 10, 50]
    steps:
      ...
      - name: 🧪 Poison the data (${{ matrix.poison_level }}%)
        run: |
          level_float=$(echo "${{ matrix.poison_level }} / 100" | bc -l)
          python poison_data.py --level $level_float
      ...
      - name: Upload experiment artifacts
        uses: actions/upload-artifact@v4
        with:
          name: experiment-results-${{ matrix.poison_level }}
          path: |
            plots/
            metrics.txt
            test_results.json
```

---

### 4.3. Consolidated Reporting

A final reporting job runs **after all matrix jobs**, regardless of their pass/fail status.

#### Steps:

1. **Download All Artifacts**  
   - Use `actions/download-artifact` to fetch all experiment outputs.

2. **Build The Markdown Report**  
   - Generate a summary table: Poison Level | Accuracy | Validation Status.
   - For each experiment, display the accuracy and confusion matrix plots in collapsible `<details>` blocks.

3. **Post to GitHub**  
   - Use CML (`cml comment create`) to post the `report.md` as a comment on the triggering commit/PR.

**Example snippet:**

```yaml
publish-report:
  needs: run-poisoning-experiment
  if: always()
  runs-on: ubuntu-latest
  steps:
    ...
    - name: 📝 Generate Final CML Report
      env:
        REPO_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      run: |
        # ... Compose the report.md file ...
        npm install -g @dvcorg/cml
        cml comment create --commit-sha ${{ github.sha }} report.md
```

---

## 5. Execution and Review

- **Trigger the pipeline** by pushing to `dev` branch.
- **Monitor in GitHub Actions:**  
  - Four parallel jobs (for each poison level) run to completion.
- **Review the CML Report** (on the commit/PR):  
  - See summary table with accuracy and pass/fail status for each experiment.
  - Expand `<details>` to see plots for accuracy and confusion matrix.
  - Confirm that higher poisoning levels degrade performance and cause tests to fail.

---

## 6. Best Practices, Security, and Extensibility

- **Always use `fail-fast: false`** in the matrix for full experiment visibility.
- **Use parameterized scripts** for easy extension to new datasets, models, or attack types.
- **Store all secrets (tokens, credentials)** securely in GitHub Actions Secrets.
- **Apply the same pattern** for other robustness tests (e.g., feature poisoning, adversarial noise).
- **Organize artifacts per experiment** so results are reproducible and easy to audit.
- **Extend reporting** to notify via Slack/email or persist results in dashboards/databases.

---