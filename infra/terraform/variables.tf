variable "project_id" {
  description = "Google Cloud project ID."
  type        = string
}

variable "region" {
  description = "Primary Google Cloud region."
  type        = string
  default     = "us-central1"
}

variable "dbt_dataset" {
  description = "Base dbt dataset name."
  type        = string
  default     = "retailops"
}

variable "artifact_repository" {
  description = "Artifact Registry Docker repository."
  type        = string
  default     = "retailops-ml"
}

variable "model_bucket_name" {
  description = "Optional explicit model artifact bucket name."
  type        = string
  default     = ""
}

variable "github_repository" {
  description = "GitHub repository allowed to use Workload Identity Federation."
  type        = string
  default     = "EL-K-Code/retailops-ai"
}

variable "enable_durable_agent_state" {
  description = "Create Cloud SQL Postgres for durable LangGraph checkpoints. This incurs cost."
  type        = bool
  default     = false
}

variable "cloud_sql_tier" {
  description = "Cloud SQL machine tier used when durable state is enabled."
  type        = string
  default     = "db-f1-micro"
}

variable "cloud_sql_disk_size_gb" {
  description = "Cloud SQL disk size."
  type        = number
  default     = 10
}

variable "labels" {
  description = "Common resource labels."
  type        = map(string)
  default = {
    project     = "retailops-ai"
    environment = "portfolio"
    managed_by  = "terraform"
  }
}
