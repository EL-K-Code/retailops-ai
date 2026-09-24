resource "google_logging_metric" "cloud_run_errors" {
  name        = "retailops_cloud_run_errors"
  description = "RetailOps Cloud Run error log entries"
  filter      = "resource.type=\"cloud_run_revision\" AND severity>=ERROR"

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    unit        = "1"
  }
}

resource "google_logging_metric" "agent_approval_required" {
  name        = "retailops_agent_approval_required"
  description = "Agent runs paused for human approval"
  filter      = "resource.type=\"cloud_run_revision\" AND textPayload:\"agent_run status=approval_required\""

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    unit        = "1"
  }
}


resource "google_logging_metric" "request_latency_ms" {
  name        = "retailops_request_latency_ms"
  description = "Distribution of RetailOps Cloud Run request latency parsed from application logs"
  filter      = "resource.type=\"cloud_run_revision\" AND textPayload:\"latency_ms=\""

  value_extractor = "REGEXP_EXTRACT(textPayload, \"latency_ms=([0-9]+\\\\.[0-9]+)\")"

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "DISTRIBUTION"
    unit        = "ms"
  }

  bucket_options {
    exponential_buckets {
      num_finite_buckets = 12
      growth_factor      = 2
      scale              = 50
    }
  }
}
