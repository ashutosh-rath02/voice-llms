import logging

import structlog


def configure_logging(level: str, json_output: bool) -> None:
    """Configure structured logging for the whole process.

    Dev renders human-readable colored lines; staging/prod render JSON so a
    log aggregator can filter on fields (conversation_id, provider, latency…)
    instead of grepping text.
    """
    numeric_level = logging.getLevelName(level.upper())
    logging.basicConfig(format="%(message)s", level=numeric_level)

    renderer: structlog.typing.Processor
    if json_output:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            # Merge request/call-scoped fields bound via structlog.contextvars
            # (e.g. conversation_id) into every log line automatically.
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        cache_logger_on_first_use=True,
    )
