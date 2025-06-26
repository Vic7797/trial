import logging
from logging_loki import LokiHandler

loki_handler = LokiHandler(
    url="http://localhost:3100/loki/api/v1/push",  # adjust as needed
    tags={"application": "customer-support-platform"},
    version="1",
)

logger = logging.getLogger("loki")
logger.setLevel(logging.INFO)
logger.addHandler(loki_handler)
