locals {
  job_users = {
    vertex = google_service_account.vertex.member
    api    = google_service_account.forecast_api.member
    agent  = google_service_account.agent.member
  }
}

resource "google_project_iam_member" "bigquery_job_user" {
  for_each = local.job_users
  project  = var.project_id
  role     = "roles/bigquery.jobUser"
  member   = each.value
}

resource "google_bigquery_dataset_iam_member" "api_ml_viewer" {
  project    = var.project_id
  dataset_id = "${var.dbt_dataset}_ml"
  role       = "roles/bigquery.dataViewer"
  member     = google_service_account.forecast_api.member
}

resource "google_bigquery_dataset_iam_member" "agent_ml_viewer" {
  project    = var.project_id
  dataset_id = "${var.dbt_dataset}_ml"
  role       = "roles/bigquery.dataViewer"
  member     = google_service_account.agent.member
}

resource "google_bigquery_dataset_iam_member" "agent_gold_viewer" {
  project    = var.project_id
  dataset_id = "${var.dbt_dataset}_gold"
  role       = "roles/bigquery.dataViewer"
  member     = google_service_account.agent.member
}

resource "google_storage_bucket_iam_member" "vertex_model_writer" {
  bucket = google_storage_bucket.models.name
  role   = "roles/storage.objectAdmin"
  member = google_service_account.vertex.member
}

resource "google_storage_bucket_iam_member" "api_model_reader" {
  bucket = google_storage_bucket.models.name
  role   = "roles/storage.objectViewer"
  member = google_service_account.forecast_api.member
}
