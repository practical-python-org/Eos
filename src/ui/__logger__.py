import logging


def setup_logger(level, stream_logs) -> None:
    """
    Configures the logging for the service.

    This function sets up the logging configuration for the service, allowing
    logs to be output to the console if specified. It formats the logs with a
    specific format and sets the logging level.

    Parameters
    ----------
    level : int
        The logging level to be set for the logs. This determines the severity
        of the messages that will be logged.
    stream_logs : bool
        A flag indicating whether to stream the logs to the console. If True,
        logs will be output to the console.

    Returns
    -------
    None
        This function does not return any value.
    """
    log_formatter = logging.Formatter(
        ":: %(asctime)s :: %(levelname)s :: %(filename)s line %(lineno)s --- %(message)s",
        "%m-%d %H:%M.%S",
    )

    handlers: list[logging.Handler] = []
    if stream_logs:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(log_formatter)
        stream_handler.setLevel(level)
        handlers.append(stream_handler)

    logging.basicConfig(level=level, handlers=handlers)
