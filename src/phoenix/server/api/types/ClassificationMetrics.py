"""
GraphQL types for classification metrics and reports.

These types represent the structure of classification metrics including
per-class precision, recall, F1-score, and support, as well as aggregated
weighted averages.
"""

from typing import Optional

import strawberry


@strawberry.type
class ClassMetrics:
    """
    Metrics for a single class or aggregate (like weighted average).
    
    Represents precision, recall, F1-score, and support count.
    """
    
    precision: float = strawberry.field(
        description="Precision score (0.0 to 1.0)"
    )
    recall: float = strawberry.field(
        description="Recall score (0.0 to 1.0)"
    )
    f1: float = strawberry.field(
        description="F1-score (harmonic mean of precision and recall)"
    )
    support: int = strawberry.field(
        description="Number of instances for this class"
    )


@strawberry.type
class PerClassMetrics:
    """
    Metrics for a specific class in the classification report.
    
    Combines the class name with its associated metrics.
    """
    
    class_name: str = strawberry.field(
        description="Name of the class (e.g., 'Síndrome Febril (SF)')"
    )
    metrics: ClassMetrics = strawberry.field(
        description="Precision, recall, F1, and support for this class"
    )


@strawberry.type
class ClassificationReport:
    """
    Complete classification report including weighted averages and per-class metrics.
    
    This report provides a comprehensive view of model performance across all classes,
    including both aggregate metrics (weighted average) and detailed per-class breakdown.
    """
    
    weighted_avg: ClassMetrics = strawberry.field(
        description="Weighted average metrics across all classes"
    )
    per_class: list[PerClassMetrics] = strawberry.field(
        description="Detailed metrics for each individual class"
    )


def build_classification_report(
    metrics_data: dict,
) -> Optional[ClassificationReport]:
    """
    Convert raw metrics data from DataLoader into GraphQL ClassificationReport type.
    
    Args:
        metrics_data: Dictionary containing 'weighted_avg' and 'per_class' keys
        
    Returns:
        ClassificationReport object or None if data is invalid
        
    Example:
        >>> data = {
        ...     "weighted_avg": {
        ...         "precision": 0.82,
        ...         "recall": 0.72,
        ...         "f1": 0.74,
        ...         "support": 585
        ...     },
        ...     "per_class": {
        ...         "Class A": {
        ...             "precision": 0.90,
        ...             "recall": 0.85,
        ...             "f1": 0.87,
        ...             "support": 100
        ...         }
        ...     }
        ... }
        >>> report = build_classification_report(data)
    """
    if not metrics_data or not isinstance(metrics_data, dict):
        return None
    
    # Extract weighted average
    weighted_avg_data = metrics_data.get("weighted_avg")
    if not weighted_avg_data:
        return None
    
    try:
        weighted_avg = ClassMetrics(
            precision=float(weighted_avg_data["precision"]),
            recall=float(weighted_avg_data["recall"]),
            f1=float(weighted_avg_data["f1"]),
            support=int(weighted_avg_data["support"]),
        )
    except (KeyError, ValueError, TypeError):
        return None
    
    # Extract per-class metrics
    per_class_data = metrics_data.get("per_class", {})
    per_class_metrics = []
    
    for class_name, class_metrics_data in per_class_data.items():
        try:
            class_metrics = ClassMetrics(
                precision=float(class_metrics_data["precision"]),
                recall=float(class_metrics_data["recall"]),
                f1=float(class_metrics_data["f1"]),
                support=int(class_metrics_data["support"]),
            )
            per_class_metrics.append(
                PerClassMetrics(
                    class_name=class_name,
                    metrics=class_metrics,
                )
            )
        except (KeyError, ValueError, TypeError):
            # Skip invalid class metrics
            continue
    
    return ClassificationReport(
        weighted_avg=weighted_avg,
        per_class=per_class_metrics,
    )
