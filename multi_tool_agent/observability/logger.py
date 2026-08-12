from __future__ import annotations

import logging


class AgentLogger:
    """
    Central logging interface for the autonomous agent.
    """

    def __init__(
        self,
        name: str = "multi_tool_agent",
    ) -> None:

        self.logger = logging.getLogger(
            name
        )

        if not self.logger.handlers:

            handler = logging.StreamHandler()

            formatter = logging.Formatter(
                "[%(levelname)s] "
                "%(asctime)s "
                "%(message)s",
                datefmt="%H:%M:%S",
            )

            handler.setFormatter(
                formatter
            )

            self.logger.addHandler(
                handler
            )

            self.logger.setLevel(
                logging.INFO
            )

    def info(
        self,
        message: str,
    ) -> None:

        self.logger.info(message)

    def warning(
        self,
        message: str,
    ) -> None:

        self.logger.warning(message)

    def error(
        self,
        message: str,
    ) -> None:

        self.logger.error(message)

    def debug(
        self,
        message: str,
    ) -> None:

        self.logger.debug(message)