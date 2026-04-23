import logging


logger = logging.getLogger(__name__)


def is_cuda_available() -> bool:
    try:
        import torch

        available = bool(torch.cuda.is_available())
        logger.info("CUDA availability checked", extra={"cuda_available": available})
        return available
    except Exception as exc:
        logger.warning("Failed to check CUDA availability: %s", exc)
        return False
