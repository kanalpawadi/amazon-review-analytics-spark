# Phase 5 - Big data run on Google Dataproc

A real cluster in Google Cloud with **HDFS, Hive and Spark** (Dataproc image 2.2: Spark 3.5.3,
Hadoop 3.3.6, Hive 3.1.3). Everything is run from **Cloud Shell** (a terminal in the browser) -
nothing is installed on the laptop.

```
UCSD website --(stream)--> Cloud Storage bucket (permanent)
                               |  copy
                               v
              Dataproc cluster: HDFS --> Spark --> Parquet (by year) --> Hive tables
              1 master + 3 workers        |
                                          v
                               results + Parquet copy back to the bucket
```

**HDFS and Hive tables live on the cluster and are deleted with it.** The bucket keeps the raw
files, the Parquet copy and all results, so a new cluster is ready again in a few minutes
(`run_ingest.sh restore`).

---

## Money - read this first

| Item | Rough cost |
|---|---|
| Cluster (4 x n2-standard-2, 8 vCPUs) | about **US$0.5-0.7 per hour** while it exists |
| Bucket storage (~20 GB) | well under US$1 per month |
| Free trial credit | **US$300 for 90 days** |

The whole Phase 5 should use a few dollars of credit. Safety built in:
- the cluster **deletes itself after 30 idle minutes** and **after 8 hours** at most (`config.sh`)
- always finish a session with `bash cluster_delete.sh`
- recommended: in the Console set a **budget alert** (Billing -> Budgets & alerts, e.g. US$20)

---

## Step 1 - account and project (once, in the browser)

1. Go to https://console.cloud.google.com and sign in with your Google account.
2. Start the **Free Trial** (US$300). Google asks for a card for identity; the trial does not
   charge it unless you choose to upgrade the account later.
3. Create a project, e.g. **amazon-review-analytics**, and note its **Project ID**.

## Step 2 - open Cloud Shell and upload the scripts

1. In the Console click the **Cloud Shell** icon (`>_`, top right). A terminal opens at the bottom.
2. Set your project (use your Project ID):
   ```
   gcloud config set project YOUR_PROJECT_ID
   ```
3. In Cloud Shell click **More (⋮) -> Upload** and upload `dataproc.zip`
   (from `D:\PROJECTS\BIG_DATA_project\dataproc.zip`). Then:
   ```
   unzip -o dataproc.zip && cd dataproc
   ```

## Step 3 - setup and data (once)

```
bash 00_setup_project.sh        # APIs, bucket, permissions            (~2 min)
bash 01_download_to_gcs.sh      # 7.8 GB + 5-core files into the bucket (~10-20 min)
```
No cluster exists yet, so this costs almost nothing.

## Step 4 - cluster and ingestion

```
bash cluster_create.sh          # ~2-3 min
bash run_ingest.sh              # first time: ~30-45 min
```
`run_ingest.sh` does: raw files GCS -> **HDFS** -> **Parquet partitioned by year** -> **Hive tables**
`amazon.reviews_raw` and `amazon.products_raw`, then queries the table with **Hive itself** and
lists the HDFS folders. Send back its output (counts, years table, Hive result, HDFS sizes).

Look at the cluster in the browser: Console -> Dataproc -> Clusters -> amazon-cluster ->
**Web Interfaces** -> *HDFS NameNode* (files and blocks) and *YARN ResourceManager* (running jobs).
Screenshots of these are good figures for the report.

## Step 5 - always at the end

```
bash cluster_delete.sh
```

## Step 6 - full-scale pipeline and scalability (3 sessions)

Every result is saved in the bucket, so the work can be split over sessions. A session = create
cluster -> run -> delete cluster. Times are rough estimates for the 8-vCPU cluster.

| Session | Commands | Time |
|---|---|---|
| **A** | `bash cluster_create.sh` · `bash run_ingest.sh` · `bash run_pipeline.sh clean sentiment` · `bash cluster_delete.sh` | 2.5-3.5 h |
| **B** | `bash cluster_create.sh` · `bash run_ingest.sh restore` · `bash run_pipeline.sh fake recommend` · `bash cluster_delete.sh` | 1.5-3 h |
| **C** | `bash cluster_create.sh` · `bash run_ingest.sh restore` · `bash run_scalability.sh` · `bash cluster_delete.sh` | 2.5-3.5 h |

Then, any time (no cluster needed): `bash collect_results.sh` -> download `results_full.zip`.

| Job | What it does at full scale | Main output (in the bucket) |
|---|---|---|
| `clean.py` | Phase 2 cleaning on all reviews | Hive `amazon.reviews_clean`, `results/full/cleaning_log.csv` |
| `sentiment.py` | trains on 2 M reviews, scores **all** reviews | `results/full/sentiment_model_comparison.csv`, model `models/sentiment_lr_full` |
| `fake_reviews.py` | all 8 signals + KMeans on all reviews | `results/full/fake_signal_prevalence.csv`, `fake_report.json` |
| `recommend.py` | explicit + implicit ALS on the **full** 5-core split | `results/full/recommend_ranking.csv`, `recommend_rmse.csv` |
| `scalability.py` | 4 workloads x data 10/25/50/100 % x 2/4/6 cores | `results/scalability/runs/*.json` |

Options:
- the near-duplicate search is the slowest part of `fake`; skip it with
  `FAKE_ARGS="--lsh off" bash run_pipeline.sh fake`
- implicit ALS uses `alpha 10` by default; if the Colab re-run of `04c` chose another value:
  `RECOMMEND_ARGS="--alpha 40" bash run_pipeline.sh recommend`
- a job that failed can be re-run alone, e.g. `bash run_pipeline.sh recommend`

**Cloud Shell closes after about 1 hour without typing.** Jobs that were already submitted keep
running on the cluster (Console -> Dataproc -> Jobs), but the script stops submitting the next one.
Press a key now and then, or run one step at a time.

## If something fails

| Message contains | Fix |
|---|---|
| `Quota 'CPUS' exceeded` | set `NUM_WORKERS=2` in `config.sh` |
| `No project selected` | `gcloud config set project YOUR_PROJECT_ID` |
| `Permission denied` on the bucket | run `bash 00_setup_project.sh` again |
| Cloud Shell disconnected during a job | the job keeps running on the cluster: Console -> Dataproc -> Jobs |
