resource "google_project_iam_member" "vertex_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = google_service_account.vertex.member
}

resource "google_project_iam_member" "agent_vertex_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = google_service_account.agent.member
}

resource "google_project_iam_member" "agent_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = google_service_account.agent.member
}

resource "google_artifact_registry_repository_iam_member" "runtime_readers" {
  for_each = {
    api   = google_service_account.forecast_api.member
    agent = google_service_account.agent.member
  }
  project    = var.project_id
  location   = var.region
  repository = google_artifact_registry_repository.docker.name
  role       = "roles/artifactregistry.reader"
  member     = each.value
}
