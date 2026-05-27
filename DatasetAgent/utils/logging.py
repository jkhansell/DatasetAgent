import logging
import sys

def get_logger(name: str) -> logging.Logger:
    """Get a properly configured logger for the given name."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            fmt="[%(levelname)s] %(asctime)s - %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
    return logger

# Shared logger for legacy helper functions
_logger = get_logger("DatasetAgent")

def log_section(title):
    _logger.info(f"\n{'='*20} {title} {'='*20}")

def debug_state(state):
    _logger.debug("\n--- STATE SNAPSHOT ---")
    _logger.debug(f"Phase: {state['phase']}")
    _logger.debug(f"Step: {state['step_count']}/{state['max_steps']}")
    _logger.debug(f"Candidate links: {len(state.get('candidate_links', []))}")
    _logger.debug(f"Downloaded: {len(state.get('downloaded_links', []))}")
    _logger.debug(f"Preprocessed: {state.get('preprocessed', False)}")
    _logger.debug("----------------------\n")

def debug_messages(result):
    if "messages" not in result:
        return

    log_section("AGENT TRACE")

    for msg in result["messages"]:
        _logger.debug(f"\n[{msg.type.upper()}]")
        if msg.content:
            _logger.debug(msg.content)
