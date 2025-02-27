import json
import traceback
from ast import literal_eval
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, Literal, Optional, cast

import pandas as pd
from cachetools import LFUCache, TTLCache
from sklearn.metrics import classification_report
from sklearn.preprocessing import MultiLabelBinarizer
from sqlalchemy import select
from strawberry.dataloader import AbstractCache, DataLoader
from typing_extensions import TypeAlias

from phoenix.db import models
from phoenix.server.api.dataloaders.cache import TwoTierCache
from phoenix.server.api.input_types.TimeRange import TimeRange
from phoenix.server.types import DbSessionFactory
from phoenix.trace.dsl import SpanFilter

MetricType: TypeAlias = Literal["precision", "recall", "f1", "support"]
ProjectRowId: TypeAlias = int
TimeInterval: TypeAlias = tuple[Optional[datetime], Optional[datetime]]
FilterCondition: TypeAlias = Optional[str]
MetricValue: TypeAlias = float

Segment: TypeAlias = tuple[TimeInterval, FilterCondition]
Param: TypeAlias = tuple[ProjectRowId, MetricType]

Key: TypeAlias = tuple[ProjectRowId, Optional[TimeRange], FilterCondition, MetricType]
Result: TypeAlias = Optional[MetricValue]
ResultPosition: TypeAlias = int
DEFAULT_VALUE: Result = None


def _cache_key_fn(key: Key) -> tuple[Segment, Param]:
    project_rowid, time_range, filter_condition, metric_type = key
    interval = (
        (time_range.start, time_range.end)
        if isinstance(time_range, TimeRange)
        else (None, None)
    )
    return (interval, filter_condition), (project_rowid, metric_type)


_Section: TypeAlias = ProjectRowId
_SubKey: TypeAlias = tuple[TimeInterval, FilterCondition, MetricType]


class ClassificationMetricsCache(
    TwoTierCache[Key, Result, _Section, _SubKey],
):
    def __init__(self) -> None:
        super().__init__(
            # TTL=3600 (1-hour) cache
            main_cache=TTLCache(maxsize=64, ttl=3600),
            sub_cache_factory=lambda: LFUCache(maxsize=2 * 2 * 4),
        )

    def _cache_key(self, key: Key) -> tuple[_Section, _SubKey]:
        (interval, filter_condition), (project_rowid, metric_type) = _cache_key_fn(key)
        return project_rowid, (interval, filter_condition, metric_type)


class ClassificationMetricsDataLoader(DataLoader[Key, Result]):
    def __init__(
        self,
        db: DbSessionFactory,
        cache_map: Optional[AbstractCache[Key, Result]] = None,
    ) -> None:
        super().__init__(
            load_fn=self._load_fn,
            cache_key_fn=_cache_key_fn,
            cache_map=cache_map,
        )
        self._db = db

    async def _load_fn(self, keys: list[Key]) -> list[Result]:
        results: list[Result] = [DEFAULT_VALUE] * len(keys)
        arguments: defaultdict[
            Segment,
            defaultdict[Param, list[ResultPosition]],
        ] = defaultdict(lambda: defaultdict(list))

        for position, key in enumerate(keys):
            segment, param = _cache_key_fn(key)
            arguments[segment][param].append(position)

        async with self._db() as session:
            for segment, params in arguments.items():
                # Group projects by metrics
                project_ids = {project_id for (project_id, _) in params.keys()}

                # Calculate metrics for each project
                for project_id in project_ids:
                    metrics = await self._calculate_classification_metrics(
                        session, project_id, segment
                    )

                    if metrics:
                        # Assign results to the correct positions
                        for metric_type in ["precision", "recall", "f1", "support"]:
                            for position in params.get(
                                (project_id, cast(MetricType, metric_type)), []
                            ):
                                results[position] = metrics.get(metric_type)

        return results

    async def _calculate_classification_metrics(
        self, session: Any, project_id: int, segment: Segment
    ) -> Optional[Dict[str, float]]:
        """Calculate precision, recall, and F1 score for project executions."""
        try:
            # Get the data required for metric calculation
            (start_time, end_time), filter_condition = segment

            project_query = select(models.Project.name).where(
                models.Project.id == project_id
            )
            project_name = await session.scalar(project_query)
            print("Calculating metrics for project:", project_name)

            if not project_name:
                return None

            stmt = (
                select(
                    models.DatasetExampleRevision.dataset_version_id,
                    models.ExperimentRun.dataset_example_id,
                    models.DatasetExampleRevision.output["GROUND_TRUTH"].label(
                        "reference"
                    ),
                    models.ExperimentRun.output["task_output"].label("output"),
                )
                .select_from(models.ExperimentRun)
                .join(
                    models.DatasetExampleRevision,
                    models.ExperimentRun.dataset_example_id
                    == models.DatasetExampleRevision.dataset_example_id,
                    isouter=True,
                )
                .join(
                    models.Experiment,
                    models.ExperimentRun.experiment_id == models.Experiment.id,
                )
                .where(models.Experiment.project_name == project_name)
            )

            if start_time:
                stmt = stmt.where(start_time <= models.ExperimentRun.start_time)
            if end_time:
                stmt = stmt.where(models.ExperimentRun.start_time < end_time)
            if filter_condition:
                sf = SpanFilter(filter_condition)
                stmt = sf(stmt)

            results = []
            data = await session.stream(stmt)

            async for dataset_version_id, dataset_example_id, reference, output in data:
                if reference is not None and output is not None:
                    results.append(
                        {
                            "dataset_version_id": dataset_version_id,
                            "dataset_example_id": dataset_example_id,
                            "reference": reference,
                            "output": output,
                        }
                    )

            if not results:
                return None

            # Convert to DataFrame to match original code format
            df = pd.DataFrame(results)

            # Process the data following the original code approach
            return self._compute_metrics_with_sklearn(df)

        except:
            # Log the exception for debugging
            print(f"Error calculating classification metrics: {traceback.format_exc()}")
            return None

    def _compute_metrics_with_sklearn(self, data: pd.DataFrame) -> Dict[str, float]:
        """Compute metrics using sklearn, following the original code approach."""
        try:
            # Process reference data using literal_eval as in original code
            data["reference"] = data.reference.apply(
                lambda item: (literal_eval(item) if isinstance(item, str) else item)
            )

            data["output"] = data.output.apply(
                lambda item: (
                    item["sindrome"]
                    if "sindrome" in item
                    else (
                        json.loads(item["messages"][0]["content"])["sindrome"]
                        if "messages" in item
                        else []
                    )
                )
            )

            # Define classes exactly as in original code
            classes = [
                "Síndrome Febril Respiratória (SFR)",
                "Síndrome Febril (SF)",
                "Síndrome Diarreica (SD)",
                "Síndrome Febril Exantemática (SFE)",
                "Síndrome Neurológica (SN)",
                "Síndrome Febril Icterohemorrágica (SFIH)",
                "Outros",
            ]

            # Use MultiLabelBinarizer from sklearn
            mlb = MultiLabelBinarizer(classes=classes)
            y_true = data.reference.to_list()
            y_pred = data.output.to_list()

            y_true = mlb.fit_transform(y_true)
            y_pred = mlb.transform(y_pred)

            # Generate the classification report using sklearn with output_dict=True
            cr = classification_report(
                y_true,
                y_pred,
                target_names=mlb.classes_,
                zero_division=0,
                output_dict=True,
            )

            # Extract the metrics from the weighted avg
            if "weighted avg" in cr:
                metrics = cr["weighted avg"]
                return {
                    "precision": float(metrics["precision"]),
                    "recall": float(metrics["recall"]),
                    "f1": float(metrics["f1-score"]),
                    "support": float(metrics["support"]),
                }

            return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "support": 0.0}

        except:
            print(f"Error in sklearn metrics computation: {traceback.format_exc()}")
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "support": 0.0}
