import os
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import xml.etree.ElementTree as ET

LOCAL_DIR = os.environ.get("LOCAL_DIR", "./pubmed_xml_gz")
PARQUET_OUT = os.environ.get("PARQUET_OUT", "./pubmed_parquet/")

def parse_and_partition_xml():
    os.makedirs(PARQUET_OUT, exist_ok=True)
    for fname in os.listdir(LOCAL_DIR):
        if fname.endswith('.xml'):
            xml_path = os.path.join(LOCAL_DIR, fname)
            print(f'Parsing {fname}')
            records = []
            tree = ET.parse(xml_path)
            root = tree.getroot()
            for article in root.findall(".//MedlineCitation"):
                pmid = article.findtext("PMID")
                title = article.findtext(".//ArticleTitle")
                pubdate = article.findtext(".//PubDate/Year")
                year = pubdate if pubdate else 'unknown'
                records.append({
                    "pmid": pmid,
                    "title": title,
                    "publication_year": year,
                    "embedding": None
                })
            df = pd.DataFrame(records)
            for year, group in df.groupby("publication_year"):
                year_folder = os.path.join(PARQUET_OUT, f'year={year}')
                os.makedirs(year_folder, exist_ok=True)
                out_path = os.path.join(year_folder, f'{fname.replace(".xml", "")}_{year}.parquet')
                table = pa.Table.from_pandas(group)
                pq.write_table(table, out_path)
