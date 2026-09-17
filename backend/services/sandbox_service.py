"""Fail-closed Docker execution for explicitly requested Python code."""

import json
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict

from backend.core.config import settings
from backend.services.conversation_service import conversation_service
from backend.schemas.tools import CodeExecutionRequest, CodeExecutionResponse


class SandboxUnavailableError(RuntimeError):
    pass


class SandboxService:
    def available(self) -> bool:
        docker = shutil.which("docker")
        if not docker:
            return False
        try:
            probe = subprocess.run(
                [docker, "info", "--format", "{{.ServerVersion}}"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if probe.returncode != 0:
                return False
            image = subprocess.run(
                [docker, "image", "inspect", settings.sandbox_image],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            return image.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False

    def execute(self, request: CodeExecutionRequest) -> CodeExecutionResponse:
        if request.language.lower() != "python":
            raise ValueError("The prototype sandbox currently supports Python only.")
        if not self.available():
            raise SandboxUnavailableError(
                f"Docker is unavailable or the local image '{settings.sandbox_image}' is not installed."
            )
        docker = shutil.which("docker")
        execution_id = str(uuid.uuid4())
        started = time.perf_counter()
        with tempfile.TemporaryDirectory(prefix="sovereign-sandbox-") as temp_dir:
            code_path = Path(temp_dir) / "main.py"
            code_path.write_text(request.code, encoding="utf-8")
            command = [
                docker,
                "run",
                "--rm",
                "--network",
                "none",
                "--memory",
                "256m",
                "--cpus",
                "0.5",
                "--pids-limit",
                "64",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--user",
                "65534:65534",
                "--tmpfs",
                "/tmp:rw,noexec,nosuid,size=16m",
                "--volume",
                f"{Path(temp_dir).resolve()}:/workspace:ro",
                settings.sandbox_image,
                "python",
                "-I",
                "/workspace/main.py",
            ]
            try:
                completed = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=request.timeout_seconds,
                    check=False,
                )
                stdout = completed.stdout[-20_000:]
                stderr = completed.stderr[-20_000:]
                status = "success" if completed.returncode == 0 else "error"
                exit_code = completed.returncode
            except subprocess.TimeoutExpired as exc:
                stdout = (exc.stdout or "")[-20_000:]
                stderr = "Execution stopped after reaching the configured timeout."
                status = "timeout"
                exit_code = 124
        duration = round((time.perf_counter() - started) * 1000, 2)
        response = CodeExecutionResponse(
            id=execution_id,
            status=status,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            execution_time_ms=duration,
        )
        conversation_service.record_tool_execution(
            "run_code_sandbox",
            status,
            response.model_dump(),
            request.conversation_id,
            "Explicit Python execution request",
        )
        return response


sandbox_service = SandboxService()
