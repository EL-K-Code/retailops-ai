resource "google_service_account" "vertex" {
  account_id   = "retailops-vertex-sa"
  display_name = "RetailOps Vertex training"
}

resource "google_service_account" "forecast_api" {
  account_id   = "retailops-api-sa"
  display_name = "RetailOps forecast API"
}

resource "google_service_account" "agent" {
  account_id   = "retailops-agent-sa"
  display_name = "RetailOps decision agent"
}

resource "google_service_account" "github_deployer" {
  account_id   = "retailops-github-deployer"
  display_name = "RetailOps GitHub deployer"
}
