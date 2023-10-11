import os
import re
import subprocess
import sys
import logging
import sqlite3

import pkg_resources
import torch

from django.http import FileResponse

from rest_framework.decorators import api_view, parser_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from webservice.api.serializers import ProjectUploadSerializer

log = logging.getLogger("deepview")


@swagger_auto_schema(
    methods=["post"],
    request_body=ProjectUploadSerializer,
    responses={
        status.HTTP_400_BAD_REQUEST: openapi.Response(
            description="Wrong project or request parameters",
            schema=openapi.Schema(
                type="object",
                properties={
                    "errors": openapi.Schema(
                        type="string", description="Profiler errors"
                    ),
                },
            ),
        ),
        status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
            description="Results cannot be retrieved",
            schema=openapi.Schema(
                type="object",
                properties={
                    "exit_code": openapi.Schema(
                        type="integer", description="Profiler exit code"
                    ),
                    "output": openapi.Schema(
                        type="string", description="Profiler output"
                    ),
                    "errors": openapi.Schema(
                        type="string", description="Profiler errors"
                    ),
                },
            ),
        ),
    },
)
@api_view(["POST"])
@parser_classes([MultiPartParser])
def run_profiling(request):
    """
    Execute profiling for uploaded project archive

    Project archive - zip archive containing project files
    Mode - profiling mode (time or memory)
    Entry point - Name of the entry point .py file. Must be in the root folder of the project (e.g. entry_point.py)
    Output - output format (json or sqlite)
    """
    serializer = ProjectUploadSerializer(data=request.data)

    if serializer.is_valid():
        # Save and unzip projcet archive
        tmp_dir_obj = serializer.save()
        tmp_dir = tmp_dir_obj.name

        # Look up for entry point file
        entry_point_path = ""
        for root, _, files in os.walk(tmp_dir):
            for file in files:
                if file == serializer.validated_data["entry_point"]:
                    entry_point_path = os.path.join(root, file)
                    log.debug("Found entry point file: %s", entry_point_path)
                    break

        if entry_point_path == "":
            return Response(
                {
                    "errors": "Entry point file is not found: "
                    + serializer.validated_data["entry_point"]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Important! Entry point file must be in the root of the project
        # This condition made because DeepView.Profile fails working with absolute paths
        work_dir = os.path.dirname(entry_point_path)

        # Running DeepView.Profile module
        deepview_output_file = "profile_output.sqlite"
        run_params = [
            "python",
            "-m",
            "deepview_profile",
            serializer.validated_data["mode"],
            serializer.validated_data["entry_point"],
            "-o",
            deepview_output_file,
        ]

        log.debug("Working directory: %s", work_dir)
        log.info("Running DeepView.Profile with params: %s", run_params)

        process_result = subprocess.run(
            run_params, cwd=work_dir, capture_output=True, check=False
        )
        exit_code = process_result.returncode
        output = process_result.stdout.decode("utf-8")
        error_output = process_result.stderr.decode("utf-8")

        log.debug("DeepView.Profile exit code: %s", exit_code)
        log.debug("DeepView.Profile output: %s", output)
        log.debug("DeepView.Profile error output: %s", error_output)

        # Put profiling result file to response
        deepview_output_file_path = os.path.join(work_dir, deepview_output_file)

        if not os.path.exists(deepview_output_file_path):
            log.error("Output file not found: %s", deepview_output_file_path)
            return Response(
                {
                    "error": "No output results found",
                    "exit_code": exit_code,
                    "output": output,
                    "errors": error_output,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Process sqlite output format
        if serializer.validated_data["output"] == "sqlite":
            file_name = os.path.basename(deepview_output_file_path)
            response = FileResponse(open(deepview_output_file_path, "rb"))
            response["Content-Disposition"] = f'attachment; filename="{file_name}"'

            # Remove special symbols from output
            output = re.sub(r"[^\w\s]", "", output).replace("\n", "")
            error_output = re.sub(r"[^\w\s]", "", error_output).replace("\n", "")

            response["X-Deepview-ExitCode"] = exit_code
            response["X-Deepview-Output"] = output
            response["X-Deepview-Errors"] = error_output

            return response

        # Else, process json output format
        db = sqlite3.connect(
            deepview_output_file_path
        )  # Replace with your actual database file path
        cursor = db.cursor()

        # Get all tables in output file
        log.debug("Loop through tables in output sqlite result file")
        query = "SELECT name FROM sqlite_master WHERE type='table';"
        cursor.execute(query)
        tables = cursor.fetchall()

        tables_dict = {}
        for row in tables:
            log.debug("Processing table: %s", {row[0]})
            query = f"SELECT * FROM {row[0]};"
            cursor.execute(query)
            results = cursor.fetchall()

            column_names = [description[0] for description in cursor.description]
            rows_as_dict = [dict(zip(column_names, row)) for row in results]
            tables_dict[row[0]] = rows_as_dict

        cursor.close()
        db.close()

        return Response(tables_dict)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view()
def get_status(request): 
    """
    Get service status

    ---
    """    
    expected_python_version = pkg_resources.parse_version("3.9")
    expected_cuda_version = pkg_resources.parse_version("11.7")
    expected_deepview_version = pkg_resources.parse_version("0.13.1")
    
    # Check Python version
    python_version = pkg_resources.parse_version(sys.version.split()[0])
    python_status = f"OK ({python_version})"
    if python_version < expected_python_version:
        python_status = f"FAIL -->> {python_version}"

    # Check CUDA version supported by PyTorch
    pytorch_status = "FAIL --> (No CUDA)"
    device_name = "No CUDA device found"
    if torch.cuda.is_available():
        pytorch_cuda_version = pkg_resources.parse_version(torch.version.cuda)
        device_name = torch.cuda.get_device_name(0)

        if pytorch_cuda_version < expected_cuda_version:
            pytorch_status = f"FAIL -->> {pytorch_cuda_version}"
        else:
            pytorch_status = f"OK ({pytorch_cuda_version})"

    # Check CUDA version supported by GPU driver
    driver_cuda_version = "0.0"
    gpu_driver = "FAIL -->> No device found"

    try:
        log.debug("Checking GPU driver version")
        process_output = subprocess.run(["nvidia-smi"], capture_output=True, text=True, check=False)

        match = re.search(r"CUDA Version:\s*([\d.]+)", process_output.stdout)
        if match:
            driver_cuda_version = match.group(1)

        installed_version = pkg_resources.parse_version(driver_cuda_version)

        if installed_version < expected_cuda_version:
            gpu_driver = f"FAIL -->> Driver suports CUDA version: {driver_cuda_version}"
        else:
            gpu_driver = f"OK ({driver_cuda_version})"

    except: # pylint: disable=bare-except
        log.exception("Error while checking GPU driver version")

    # Check DeepView.Profile package version
    try:
        package = pkg_resources.get_distribution("deepview-profile")
        installed_version = pkg_resources.parse_version(package.version)

        if installed_version < expected_deepview_version:
            deepview_package = f"FAIL -->> {package.version}"
        else:
            deepview_package = f"OK ({package.version})"
    except pkg_resources.DistributionNotFound:
        deepview_package = "FAIL -->> Not installed"

    return Response(
        {
            f"Python ({expected_python_version})": python_status,
            f"PyTorch CUDA ({expected_cuda_version})": pytorch_status,
            "CUDA device": device_name,
            f"GPU driver CUDA ({expected_cuda_version})": gpu_driver,
            f"DeepView.Profile (pypi: {expected_deepview_version})": deepview_package,
        }
    )
