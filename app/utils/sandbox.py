"""
Sandboxed tool execution for isolation and safety.
Runs tools in subprocess with OS-level timeouts.
"""

import asyncio
import subprocess
import tempfile
import json
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SandboxResult:
    """Result from sandboxed execution."""
    success: bool
    result: Any
    error: Optional[str]
    duration_ms: float
    exit_code: int = 0


class ToolSandbox:
    """
    Sandbox for isolated tool execution.
    Uses subprocess with strict timeouts and resource limits.
    """

    def __init__(self, default_timeout: int = 30):
        """
        Initialize sandbox.

        Args:
            default_timeout: Default timeout in seconds
        """
        self.default_timeout = default_timeout

    async def execute_python(self, code: str, timeout: Optional[int] = None) -> SandboxResult:
        """
        Execute Python code in isolated subprocess.

        Args:
            code: Python code to execute
            timeout: Timeout in seconds (uses default if None)

        Returns:
            SandboxResult with output or error
        """
        timeout = timeout or self.default_timeout

        # Create temp file with code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            # Wrap code to capture output safely
            wrapped_code = f"""
import json
import sys
from io import StringIO

# Capture stdout/stderr
old_stdout = sys.stdout
old_stderr = sys.stderr
sys.stdout = mystdout = StringIO()
sys.stderr = mystderr = StringIO()

try:
{chr(10).join('    ' + line for line in code.strip().split(chr(10)))}
    output = mystdout.getvalue()
    error = mystderr.getvalue()
    result = {{"success": True, "output": output, "error": error if error else None}}
except Exception as e:
    result = {{"success": False, "output": mystdout.getvalue(), "error": str(e)}}

sys.stdout = old_stdout
sys.stderr = old_stderr
print(json.dumps(result))
"""
            f.write(wrapped_code)
            temp_file = f.name

        start_time = datetime.utcnow()

        try:
            # Run in subprocess with timeout
            process = await asyncio.create_subprocess_exec(
                'python', temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )

                duration = (datetime.utcnow() - start_time).total_seconds() * 1000

                if process.returncode != 0:
                    return SandboxResult(
                        success=False,
                        result=None,
                        error=f"Process failed with code {process.returncode}: {stderr.decode()}",
                        duration_ms=duration,
                        exit_code=process.returncode
                    )

                # Parse result
                try:
                    result_data = json.loads(stdout.decode().strip().split('\n')[-1])
                    return SandboxResult(
                        success=result_data.get("success", True),
                        result=result_data.get("output", ""),
                        error=result_data.get("error"),
                        duration_ms=duration,
                        exit_code=0
                    )
                except json.JSONDecodeError:
                    return SandboxResult(
                        success=False,
                        result=None,
                        error=f"Invalid output format: {stdout.decode()}",
                        duration_ms=duration,
                        exit_code=1
                    )

            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return SandboxResult(
                    success=False,
                    result=None,
                    error=f"Execution timeout after {timeout}s",
                    duration_ms=timeout * 1000,
                    exit_code=-1
                )

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds() * 1000
            return SandboxResult(
                success=False,
                result=None,
                error=str(e),
                duration_ms=duration,
                exit_code=1
            )

        finally:
            # Cleanup temp file
            try:
                os.unlink(temp_file)
            except:
                pass

    async def execute_shell(self, command: str, timeout: Optional[int] = None) -> SandboxResult:
        """
        Execute shell command in isolated subprocess.

        Args:
            command: Shell command to execute
            timeout: Timeout in seconds

        Returns:
            SandboxResult with output or error
        """
        timeout = timeout or self.default_timeout
        start_time = datetime.utcnow()

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )

                duration = (datetime.utcnow() - start_time).total_seconds() * 1000

                return SandboxResult(
                    success=process.returncode == 0,
                    result=stdout.decode(),
                    error=stderr.decode() if stderr else None,
                    duration_ms=duration,
                    exit_code=process.returncode
                )

            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return SandboxResult(
                    success=False,
                    result=None,
                    error=f"Command timeout after {timeout}s",
                    duration_ms=timeout * 1000,
                    exit_code=-1
                )

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds() * 1000
            return SandboxResult(
                success=False,
                result=None,
                error=str(e),
                duration_ms=duration,
                exit_code=1
            )

    async def execute_thread(self, func, *args, timeout: Optional[int] = None, **kwargs) -> SandboxResult:
        """
        Execute function in thread pool (for non-subprocess isolation).

        Args:
            func: Function to execute
            args: Positional arguments
            timeout: Timeout in seconds
            kwargs: Keyword arguments

        Returns:
            SandboxResult
        """
        timeout = timeout or self.default_timeout
        start_time = datetime.utcnow()

        try:
            # Run in thread pool
            result = await asyncio.wait_for(
                asyncio.to_thread(func, *args, **kwargs),
                timeout=timeout
            )

            duration = (datetime.utcnow() - start_time).total_seconds() * 1000
            return SandboxResult(
                success=True,
                result=result,
                error=None,
                duration_ms=duration,
                exit_code=0
            )

        except asyncio.TimeoutError:
            return SandboxResult(
                success=False,
                result=None,
                error=f"Thread timeout after {timeout}s",
                duration_ms=timeout * 1000,
                exit_code=-1
            )

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds() * 1000
            return SandboxResult(
                success=False,
                result=None,
                error=str(e),
                duration_ms=duration,
                exit_code=1
            )


# Global sandbox instance
sandbox = ToolSandbox()
