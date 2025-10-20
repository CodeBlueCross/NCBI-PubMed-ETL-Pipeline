import os
import gzip
import shutil

LOCAL_DIR = os.environ.get("LOCAL_DIR", "./pubmed_xml_gz")

def decompress_gz_files():
    for fname in os.listdir(LOCAL_DIR):
        if fname.endswith('.xml.gz'):
            gz_path = os.path.join(LOCAL_DIR, fname)
            xml_path = gz_path[:-3]
            if not os.path.exists(xml_path):
                print(f'Decompressing {fname}')
                with gzip.open(gz_path, 'rb') as f_in:
                    with open(xml_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
