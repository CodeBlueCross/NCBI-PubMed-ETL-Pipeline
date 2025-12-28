import os
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import xml.etree.ElementTree as ET
import logging


logger = logging.getLogger(__name__)

def parse_and_partition_xml():
    LOCAL_DIR = os.environ.get("LOCAL_DIR", "./pubmed_xml_gz")
    PARQUET_OUT = os.environ.get("PARQUET_OUT", "./pubmed_parquet/")
    try:
        os.makedirs(PARQUET_OUT, exist_ok=True)
        if not os.path.exists(LOCAL_DIR):
            logger.warning(f"Directory {LOCAL_DIR} does not exist. Skipping parsing.")
            return

        for fname in os.listdir(LOCAL_DIR):
            if fname.endswith('.xml'):
                xml_path = os.path.join(LOCAL_DIR, fname)
                logger.info(f'Parsing {fname}')
                try:
                    records = []
                    tree = ET.parse(xml_path)
                    root = tree.getroot()
                    for article in root.findall(".//MedlineCitation"):
                        pmid = article.findtext("PMID")
                        title = article.findtext(".//ArticleTitle")
                        
                        # Extract Abstract (handling multiple parts for structured abstracts)
                        abstract_elements = article.findall(".//Abstract/AbstractText")
                        abstract_text = " ".join([elem.text for elem in abstract_elements if elem.text])
                        if not abstract_text:
                            abstract_text = None

                        # Authors
                        authors_list = []
                        for author in article.findall(".//AuthorList/Author"):
                            last = author.findtext("LastName")
                            fore = author.findtext("ForeName")
                            if last and fore:
                                authors_list.append(f"{last} {fore}")
                            elif last:
                                authors_list.append(last)
                        authors_str = "; ".join(authors_list) if authors_list else None

                        # Journal
                        journal = article.findtext(".//Journal/Title")

                        # DOI
                        doi = None
                        for eloc in article.findall(".//ELocationID"):
                            if eloc.get("EIdType") == "doi":
                                doi = eloc.text
                                break
                        
                        # MeSH Terms
                        mesh_terms = []
                        for mesh in article.findall(".//MeshHeadingList/MeshHeading"):
                            descriptor = mesh.findtext("DescriptorName")
                            if descriptor:
                                mesh_terms.append(descriptor)
                        mesh_str = "; ".join(mesh_terms) if mesh_terms else None

                        pubdate = article.findtext(".//PubDate/Year")
                        year = pubdate if pubdate else 'unknown'
                        
                        records.append({
                            "pmid": pmid,
                            "title": title,
                            "abstract": abstract_text,
                            "authors": authors_str,
                            "journal": journal,
                            "doi": doi,
                            "mesh_terms": mesh_str,
                            "publication_year": year,
                            "embedding": None
                        })
                    
                    if not records:
                        logger.warning(f"No records found in {fname}")
                        continue

                    df = pd.DataFrame(records)
                    for year, group in df.groupby("publication_year"):
                        year_folder = os.path.join(PARQUET_OUT, f'year={year}')
                        os.makedirs(year_folder, exist_ok=True)
                        out_path = os.path.join(year_folder, f'{fname.replace(".xml", "")}_{year}.parquet')
                        table = pa.Table.from_pandas(group)
                        pq.write_table(table, out_path)
                        
                except ET.ParseError as e:
                    logger.error(f"XML Parse Error in {fname}: {e}", exc_info=True)
                except Exception as e:
                    logger.error(f"Error processing {fname}: {e}", exc_info=True)
                    
    except Exception as e:
        logger.error(f"Critical error in parse_and_partition_xml: {e}", exc_info=True)
        raise
