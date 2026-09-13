resource "google_service_account_iam_member" "deployer_use_api_sa" {
  service_account_id = google_service_account.forecast_api.name
  role               = "roles/iam.serviceAccountUser"
  member             = google_service_account.github_deployer.member
}

resource "google_service_account_iam_member" "deployer_use_agent_sa" {
  service_account_id = google_service_account.agent.name
  role               = "roles/iam.serviceAccountUser"
  member             = google_service_account.github_deployer.member
}
