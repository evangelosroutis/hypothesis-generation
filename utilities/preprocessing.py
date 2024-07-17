import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import pandas as pd
from typing import Any, Dict
import os
import dask.dataframe as dd

def get_go_term_description(go_id):
    """
    Retrieves the description of a Gene Ontology (GO) term based on its GO ID.
    Args:
        go_id (str): The GO ID of the term to retrieve the description for.
    Returns:
        dict: A dictionary containing the GO term's label and definition.
    """
    url = f"http://api.geneontology.org/api/ontology/term/{go_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        data = response.json()  
        return {'GO_label': data.get('label'), 'GO_definition': data.get('definition')}
    except (requests.exceptions.HTTPError, requests.exceptions.RequestException, ValueError) as e:
        return {'GO_label': None, 'GO_definition': None}


def kegg_symbols_and_names(url):
    """
    Extracts gene symbols and their corresponding names from a KEGG pathway webpage.
    Args:
        url (str): The URL of the KEGG pathway page to extract gene information from.
    Returns:
        dict: A dictionary where keys are gene symbols and values are gene names.
    """
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    #find all tables in the page
    tables = soup.find_all('table')
    genes = {}
    
    # Loop through tables and look for gene information
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) > 1:
                text = cells[1].get_text().strip()
                if ';' in text and '[' in text:
                    parts = text.split(';')
                    gene_symbol = parts[0].strip()
                    gene_name = parts[1].split('[')[0].strip()
                    genes[gene_symbol] = gene_name
    return genes


def parse_kgml(file_path):
    """
    Parses a KGML (KEGG XML) file to extract pathway information, including genes, compounds, and interactions.
    Args:
        file_path (str): The path to the KGML file to be parsed.
    Returns:
        dict: A dictionary containing the pathway ID, pathway name, lists of genes and compounds, 
              and a list of interactions.
    """
    tree = ET.parse(file_path)
    root = tree.getroot()
    pathway_id = root.get('number')
    pathway_name = root.get('title')
    entries = {
        'gene': [],
        'compound': []
    }
    interactions = []

    for entry in root.findall('entry'):
        entry_type = entry.get('type')
        if entry_type in ['gene', 'compound']:
            entry_id = entry.get('id')
            entry_names = entry.get('name').split()
            graphics = entry.find('graphics')
            entry_symbols = graphics.get('name').split(', ') if graphics is not None else []
            # Remove '...' from symbols if present
            entry_symbols = [symbol.rstrip('...') for symbol in entry_symbols]
            entries[entry_type].append({
                f'{entry_type}_id': entry_id,
                f'{entry_type}_names': entry_names,
                f'{entry_type}_symbols': entry_symbols
            })

    for relation in root.findall('relation'):
        entry1 = relation.get('entry1')
        entry2 = relation.get('entry2')
        relation_type = relation.get('type')
        subtypes = [subtype.get('name') for subtype in relation.findall('subtype')]
        interactions.append({
            'entry1': entry1,
            'entry2': entry2,
            'type': relation_type,
            'subtypes': subtypes
        })

    pathway_data = {
        'pathway_id': pathway_id,
        'pathway_name': pathway_name,
        'genes': entries['gene'],
        'compounds': entries['compound'],
        'interactions': interactions
    }
    return pathway_data


def parse_gaf(file_path):
    """
    Parses a GAF (Gene Annotation Format) file to extract gene annotation information into a DataFrame.
    Args:
        file_path (str): The path to the GAF file to be parsed.
    Returns:
        DataFrame: A pandas DataFrame containing the parsed gene annotation information.
    """
    # Define column names based on the GAF file format
    column_names = [
        'DB', 'DB_Object_ID', 'DB_Object_Symbol', 'Qualifier', 'GO_ID', 
        'DB:Reference', 'Evidence_Code', 'With_or_From', 'Aspect', 
        'DB_Object_Name', 'DB_Object_Synonym', 'DB_Object_Type', 'Taxon', 
        'Date', 'Assigned_By', 'Annotation_Extension', 'Gene_Product_Form_ID'
    ]

    # Read the GAF file into a DataFrame, skipping comment lines
    gaf_df = pd.read_csv(file_path, sep='\t', comment='!', header=None, names=column_names, dtype=str)

    # Process the columns that have multiple values separated by '|'
    gaf_df['DB_Object_Synonym'] = gaf_df['DB_Object_Synonym'].apply(lambda x: x.split('|') if pd.notna(x) else [])
    gaf_df['Taxon'] = gaf_df['Taxon'].apply(lambda x: x.split('|') if pd.notna(x) else [])

    return gaf_df


def go_id_description(df:pd.DataFrame)->pd.DataFrame:
    """
    Process a DataFrame to get GO term descriptions.
    
    Args:
        df (pd.DataFrame): DataFrame with at least one column 'GO_ID'.
    
    Returns:
        pd.DataFrame: DataFrame with 'GO_ID', 'GO_label', and 'GO_definition'.
    """
    if not pd.api.types.is_string_dtype(df['GO_ID']):
        raise ValueError("'GO_ID' column must be of type string.")
    
    go_df=df[['GO_ID']].drop_duplicates()

    # Convert the Pandas DataFrame to a Dask DataFrame
    num_cores = os.cpu_count()
    ddf = dd.from_pandas(go_df, npartitions=num_cores)

    # Define a function to apply to each partition
    def apply_go_term_description(partition):
        results = [get_go_term_description(go_id) for go_id in partition['GO_ID']]
        result_df = pd.DataFrame(results)
        return pd.concat([partition.reset_index(drop=True), result_df], axis=1)
    
    # define metadata structure for Dask computation
    meta = pd.DataFrame({
        'GO_ID': pd.Series(dtype='str'),
        'GO_label': pd.Series(dtype='str'),
        'GO_definition': pd.Series(dtype='str')
    })

    go_ddf = ddf.map_partitions(apply_go_term_description, meta=meta)
    
    return go_ddf.compute()


def kegg_go_integration(kgml_path: str, gaf_path: str, aspect_dict:dict) -> pd.DataFrame:
    """
    Integrates KEGG and GO data.

    Args:
        kgml_path (str): Path to the KEGG KGML file.
        gaf_path (str): Path to the GO GAF file.

    Returns:
        pd.DataFrame: Merged DataFrame with integrated KEGG and GO data.
    """
    # Parse KEGG data
    kegg_genes=parse_kgml(kgml_path)['genes']
    kegg_df=pd.DataFrame(kegg_genes,columns=['gene_id','gene_symbols'])
    kegg_exploded_df=kegg_df.explode('gene_symbols')

    # Parse GAF data
    gaf_df=parse_gaf(gaf_path)[['Qualifier','GO_ID','Aspect','DB_Object_Name','DB_Object_Synonym','DB_Object_Type']]
    gaf_exploded_df=gaf_df.explode('DB_Object_Synonym')

    # Merge KEGG and GAF on common synonyms
    merged_df=pd.merge(kegg_exploded_df,gaf_exploded_df,left_on='gene_symbols',right_on='DB_Object_Synonym',how='inner').drop_duplicates()

    # Aggregate all synonyms and names by gene_id
    agg_names_synonyms_df=merged_df[['gene_id','DB_Object_Name','DB_Object_Synonym']].groupby('gene_id').agg(lambda x:list(set(x))).reset_index()

    # Merge merged_df with agg_names_synonyms_df so that all gene_id entries have consistent names and symbols
    merged_df=pd.merge(merged_df[['gene_id','Qualifier','GO_ID','Aspect','DB_Object_Type']],agg_names_synonyms_df)

    #Get dataframe with GO_IDs and their descriptions
    go_df=go_id_description(merged_df)
    
    # Merge GO descriptions and replace aspect values
    merged_df=pd.merge(merged_df,go_df,on='GO_ID').replace({'Aspect':aspect_dict})

    return merged_df


def dict_to_frozenset(d: Dict[str, Any]) -> frozenset:
    """
    Convert a dictionary to a frozenset for consistency checks.

    Args:
        d (Dict[str, Any]): Dictionary to be converted.

    Returns:
        frozenset: Frozenset representation of the dictionary.
    """
    items = []
    for k, v in d.items():
        if isinstance(v, dict):
            items.append((k, dict_to_frozenset(v)))
        elif isinstance(v, list):
            items.append((k, tuple(dict_to_frozenset(i) if isinstance(i, dict) else i for i in v)))
        else:
            items.append((k, v))
    return frozenset(items)
