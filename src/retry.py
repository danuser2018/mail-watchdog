import logging

logger = logging.getLogger(__name__)

def get_backoff_delay(attempts: int, base: float) -> float:
    """
    Calculates the backoff delay in seconds for a given retry attempt.
    Formula: base ** (attempts - 1)
    For base = 2.0:
      - Attempt 1 (first failure): 2.0 ** 0 = 1.0 second
      - Attempt 2: 2.0 ** 1 = 2.0 seconds
      - Attempt 3: 2.0 ** 2 = 4.0 seconds
    """
    if attempts <= 0:
        return 0.0
    
    # Calculate simple exponential backoff
    delay = float(base ** (attempts - 1))
    
    logger.debug(f"Calculated backoff delay for attempt {attempts} (base={base}): {delay}s")
    return delay
