# Retail decision policy

## Decision boundary
RetailOps AI is a decision-support system. A demand forecast is evidence about expected sales, not
automatically an order quantity. Reorder and safety-stock decisions require inventory position,
lead time, service-level objectives, existing purchase orders, and operational constraints that are
not present in the M5 dataset.

## Human approval
Recommendations to review a reorder, change safety stock, investigate an anomaly, or escalate a
planning decision require explicit human approval. Approval authorizes human follow-up only. The
V5 agent has no mutating tool and must never claim that it changed an operational system.

## Inventory semantics
The public M5 dataset does not contain true Walmart inventory levels. Any later stockout-risk demo
that introduces simulated inventory must label it as simulated and must never present it as real
retailer inventory.
