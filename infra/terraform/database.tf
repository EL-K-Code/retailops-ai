resource "google_sql_database_instance" "agent_state" {
  count            = var.enable_durable_agent_state ? 1 : 0
  name             = "retailops-agent-state"
  region           = var.region
  database_version = "POSTGRES_16"

  settings {
    tier              = var.cloud_sql_tier
    disk_size         = var.cloud_sql_disk_size_gb
    availability_type = "ZONAL"
    user_labels       = var.labels

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
    }
  }

  deletion_protection = true
  depends_on          = [google_project_service.required]
}

resource "google_sql_database" "agent_checkpoints" {
  count    = var.enable_durable_agent_state ? 1 : 0
  name     = "retailops_agent"
  instance = google_sql_database_instance.agent_state[0].name
}
