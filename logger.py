# logger.py
import logging

def setup_logger(name, level=logging.DEBUG):
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(name)20s - %(levelname)8s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)
        logger.propagate = False
    return logger

def log_metadata_section(logger, section_title, metadata: dict, trim_description=True, max_description_len=20):
    logger.info(f"--- {section_title} ---")

    for key, value in metadata.items():
        label = key.capitalize().replace("_", " ")
        if not value:
            logger.info(f"{label:<15}: [Not found]")
        elif key == "description" and trim_description:
            short = (value[:max_description_len] + "...") if len(value) > max_description_len else value
            logger.info(f"{label:<15}: {short}")
        else:
            logger.info(f"{label:<15}: {value}")