# Vertex AI Training Pipeline

This directory contains the cloud-training layer for RetailOps AI.

Target flow:

BigQuery ML features -> Vertex AI Training Job -> LightGBM artifact -> GCS -> Vertex AI Model Registry

The first implementation will reuse the validated local LightGBM pipeline and move execution to managed cloud infrastructure.
