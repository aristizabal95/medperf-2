import logging

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from fastapi import Request

from medperf.entities.benchmark import Benchmark
from medperf.entities.dataset import Dataset
from medperf.entities.cube import Cube
from medperf.account_management import get_medperf_user_data
from medperf.enums import Status
from medperf.web_ui.common import templates

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/ui", response_class=HTMLResponse)
def benchmarks_ui(request: Request, local_only: bool = False, mine_only: bool = False):
    filters = {}
    if mine_only:
        filters["owner"] = get_medperf_user_data()["id"]

    benchmarks = Benchmark.all(
        local_only=local_only,
        filters=filters,
    )
    return templates.TemplateResponse("benchmarks.html", {"request": request, "benchmarks": benchmarks})


@router.get("/ui/{benchmark_id}", response_class=HTMLResponse)
def benchmark_detail_ui(request: Request, benchmark_id: int):
    benchmark = Benchmark.get(benchmark_id)
    data_preparation_mlcube = Cube.get(cube_uid=benchmark.data_preparation_mlcube)
    reference_model_mlcube = Cube.get(cube_uid=benchmark.reference_model_mlcube)
    metrics_mlcube = Cube.get(cube_uid=benchmark.data_evaluator_mlcube)
    datasets_associations = Benchmark.get_datasets_associations(benchmark_uid=benchmark_id)
    models_associations = Benchmark.get_models_associations(benchmark_uid=benchmark_id)

    approval_status_order = {
        Status.PENDING: 0,
        Status.APPROVED: 1,
        Status.REJECTED: 2,
    }

    def assoc_sorting_key(assoc):
        # lower status - first
        status_order = approval_status_order.get(assoc.approval_status, -1)
        # recent associations - first
        date_order = -(assoc.approved_at or assoc.created_at).timestamp()
        return status_order, date_order

    datasets_associations = sorted(datasets_associations, key=assoc_sorting_key)
    models_associations = sorted(models_associations, key=assoc_sorting_key)

    # Fetch datasets and models information
    datasets = {assoc.dataset: Dataset.get(assoc.dataset) for assoc in datasets_associations if assoc.dataset}
    models = {assoc.model_mlcube: Cube.get(assoc.model_mlcube) for assoc in models_associations if assoc.model_mlcube}

    return templates.TemplateResponse(
        "benchmark_detail.html",
        {
            "request": request,
            "entity": benchmark,
            "entity_name": benchmark.name,
            "data_preparation_mlcube": data_preparation_mlcube,
            "reference_model_mlcube": reference_model_mlcube,
            "metrics_mlcube": metrics_mlcube,
            "datasets_associations": datasets_associations,
            "models_associations": models_associations,
            "datasets": datasets,
            "models": models
        }
    )
