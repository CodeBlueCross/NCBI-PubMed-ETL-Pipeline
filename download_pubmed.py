import os
from ftplib import FTP

LOCAL_DIR = os.environ.get("LOCAL_DIR", "./pubmed_xml_gz")
FTP_URL = os.environ.get("FTP_URL", "ftp.ncbi.nlm.nih.gov")
FTP_DIR = os.environ.get("FTP_DIR", "pubmed/baseline")

def download_pubmed_files():
    os.makedirs(LOCAL_DIR, exist_ok=True)
    ftp = FTP(FTP_URL)
    ftp.login()
    ftp.cwd(FTP_DIR)
    filenames = ftp.nlst()
    xml_gz_files = [f for f in filenames if f.endswith('.xml.gz')]
    for fname in xml_gz_files:
        local_path = os.path.join(LOCAL_DIR, fname)
        if not os.path.exists(local_path):
            print(f'Downloading {fname}')
            with open(local_path, 'wb') as fp:
                ftp.retrbinary(f'RETR {fname}', fp.write)
    ftp.quit()
