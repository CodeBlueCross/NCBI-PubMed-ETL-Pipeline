import os
import gzip
import shutil
import logging


logger = logging.getLogger(__name__)

def decompress_gz_files():
    LOCAL_DIR = os.environ.get("LOCAL_DIR", "./pubmed_xml_gz")
    try:
        for fname in os.listdir(LOCAL_DIR):
            if fname.endswith('.xml.gz'):
                gz_path = os.path.join(LOCAL_DIR, fname)
                xml_path = gz_path[:-3]
                if not os.path.exists(xml_path):
                    logger.info(f'Decompressing {fname}')
                    try:
                        with gzip.open(gz_path, 'rb') as f_in:
                            with open(xml_path, 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                    except Exception as e:
                        logger.error(f"Failed to decompress {fname}: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Error accessing directory {LOCAL_DIR}: {e}", exc_info=True)
