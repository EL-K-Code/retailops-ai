"""
RetailOps AI - Vertex AI training entrypoint.

This file is the cloud execution entrypoint for the LightGBM forecasting model.
The first version keeps the training contract explicit; the validated local
training pipeline logic will be migrated here without changing evaluation rules.
"""

import argparse
import json
import os
from datetime import datetime, timezone


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-lookback-days", type=int, default=180)
    parser.add_argument("--num-boost-round", type=int, default=100)
    parser.add_argument("--model-dir", default="/tmp/model")
    parser.add_argument("--model-name", default="lightgbm_global_v1")
    return parser.parse_args()


def main():
    args = parse_args()

    os.makedirs(args.model_dir, exist_ok=True)

    metadata = {
        "model_name": args.model_name,
        "train_lookback_days": args.train_lookback_days,
        "num_boost_round": args.num_boost_round,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "vertex_training_scaffold"
    }

    with open(os.path.join(args.model_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
