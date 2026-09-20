import logging


logger = logging.getLogger(__name__)

DEFAULT_MOUNTS = ["/", "/var", "/home"]

def collect(path: str | None = None) :
    
        
    logger.info(f"system")    
