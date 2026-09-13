resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "retailops-github"
  display_name              = "RetailOps GitHub"
}
