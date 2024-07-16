
from neo4j import GraphDatabase
from utilities.preprocessing import parse_kgml
import pandas as pd
from pydantic import BaseModel, Field, ValidationError, field_validator
from typing import List, Optional, Dict, Any
from neo4j import GraphDatabase,Transaction


class GeneData(BaseModel):
    """
    Pydantic model for Gene data with fields validated and default values handled.

    Attributes:
        gene_id: Unique identifier for the gene.
        Qualifier: Qualifier for the gene annotation.
        GO_ID: Gene Ontology ID.
        Aspect: Aspect of the gene ontology.
        DB_Object_Type: Type of the database object.
        DB_Object_Name: List of names for the database object.
        DB_Object_Synonym: List of synonyms for the database object.
        GO_label: Label for the Gene Ontology term.
        GO_definition: Definition for the Gene Ontology term.
    """
    gene_id: str
    Qualifier: Optional[str]
    GO_ID: Optional[str]
    Aspect: Optional[str]
    DB_Object_Type: Optional[str]
    DB_Object_Name: Optional[List[str]] = Field(default_factory=list)
    DB_Object_Synonym: Optional[List[str]] = Field(default_factory=list)
    GO_label: Optional[str]
    GO_definition: Optional[str]

    @field_validator('*', mode='before')
    def handle_nan(cls, v: Any) -> Any:
        """
        Handle NaN values by converting them to None.
        If the value is a list, it iterates over the elements and replaces NaN with None.
        
        Args:
            v: The value to check and potentially modify.
        
        Returns:
            The modified value with NaN values handled.
        """
        if isinstance(v, list):
            return [None if pd.isna(i) else i for i in v]
        if pd.isna(v):
            return None
        return v

    @field_validator('DB_Object_Name', 'DB_Object_Synonym', mode='before')
    def convert_to_list(cls, v:Optional[Any]) -> List[Any]:
        """
        Convert None values to an empty list for specific fields.
        
        Args:
            v: The value to check and potentially modify.
        
        Returns:
            An empty list if the value is None, otherwise the original value.
        """
        if v is None:
            return []
        return v


class Disease(BaseModel):
    """
    Pydantic model for Disease data with required fields.

    Attributes:
        disease_id: Unique identifier for the disease.
        name: Name of the disease.
    """
    disease_id: str
    name: str


class GeneInteraction(BaseModel):
    """
    Pydantic model for Gene Interaction data with fields validated and default values handled.

    Attributes:
        entry1: Identifier for the first gene in the interaction.
        entry2: Identifier for the second gene in the interaction.
        type: Type of interaction.
        subtypes: List of subtypes for the interaction.
    """
    entry1: str
    entry2: str
    type: str
    subtypes: Optional[List[str]] = Field(default_factory=list)


class KGMLGAFImporter:
    """
    Class to import data from KGML and GAF files into a Neo4j database.
    
    Example usage:
    # Connect to the Neo4j database
    uri = "bolt://localhost:7687"  
    user = user 
    password = password

    # Initialize the Neo4j driver 
    driver = GraphDatabase.driver(uri, auth=(user, password))

    kgml_files = [
                'data/KGML/hsa04930.xml',
                'data/KGML/hsa05010.xml',
                'data/KGML/hsa05012.xml',
                'data/KGML/hsa05210.xml'
                ]

    # import data
    importer = KGMLGAFImporter(driver)
    importer.import_data(kgml_files)

    # Close the connection
    importer.close()
    """
    def __init__(self, driver: GraphDatabase.driver):
        """
        Initialize the importer with a Neo4j driver.

        Args:
            driver: Neo4j driver for database connection.
        """
        self.driver = driver

    def close(self):
        """
        Close the Neo4j driver connection.
        """
        self.driver.close()

    def create_gene_node(self, tx: Transaction, gene: Dict[str, Any], disease_id: str):
        """
        Create a Gene node in the Neo4j database.

        Args:
            tx: Neo4j transaction object.
            gene: Dictionary containing gene data.
            disease_id: ID of the associated disease.
        """
        try:
            gene_model = GeneData(**gene)
        except ValidationError as e:
            print(f"Validation error for gene {gene['gene_id']}: {e}")
            return

        tx.run(
            """
            MERGE (g:Gene {unique_id: $unique_id})
            SET g.synonyms = $synonyms,
                g.names = $names
            """,
            unique_id=f"{disease_id}_{gene_model.gene_id}",
            names=gene_model.DB_Object_Name,
            synonyms=gene_model.DB_Object_Synonym,
        )

    def create_disease_node(self, tx: Transaction, disease: Dict[str, Any]):
        """
        Create a Disease node in the Neo4j database.

        Args:
            tx: Neo4j transaction object.
            disease: Dictionary containing disease data.
        """
        try:
            disease_model = Disease(**disease)
        except ValidationError as e:
            print(f"Validation error for disease {disease['disease_id']}: {e}")
            return

        tx.run(
            """
            MERGE (d:Disease {disease_id: $disease_id})
            SET d.name = $name
            """,
            disease_id=disease_model.disease_id,
            name=disease_model.name
        )

    def create_go_node(self, tx: Transaction, gene: Dict[str, Any]):
        """
        Create a GO Annotation node in the Neo4j database.

        Args:
            tx: Neo4j transaction object.
            gene: Dictionary containing gene data.
        """
        try:
            gene_model = GeneData(**gene)
        except ValidationError as e:
            print(f"Validation error for gene {gene['gene_id']}: {e}")
            return

        tx.run(
            """
            MERGE (a:GO_Annotation {qualifier: $qualifier, GO_ID: $GO_ID})
            SET a.aspect = $aspect,
                a.object_type = $object_type,
                a.name = $GO_label,
                a.definition = $GO_definition
            """,
            qualifier=gene_model.Qualifier,
            GO_ID=gene_model.GO_ID,
            aspect=gene_model.Aspect,
            object_type=gene_model.DB_Object_Type,
            GO_label=gene_model.GO_label,
            GO_definition=gene_model.GO_definition
        )

    def create_gene_interaction(self, tx: Transaction, interaction: Dict[str, Any], disease_id: str):
        """
        Create an INTERACTS_WITH relationship between Gene nodes in the Neo4j database.

        Args:
            tx: Neo4j transaction object.
            interaction: Dictionary containing interaction data.
            disease_id: ID of the associated disease.
        """
        try:
            interaction_model = GeneInteraction(**interaction)
        except ValidationError as e:
            print(f"Validation error for interaction {interaction['entry1']} -> {interaction['entry2']}: {e}")
            return

        tx.run(
            """
            MATCH (g1:Gene {unique_id: $entry_1})
            MATCH (g2:Gene {unique_id: $entry_2})
            MERGE (g1)-[r:INTERACTS_WITH {type: $interaction_type, subtypes: $subtypes}]->(g2)
            """,
            entry_1=f"{disease_id}_{interaction_model.entry1}",
            entry_2=f"{disease_id}_{interaction_model.entry2}",
            interaction_type=interaction_model.type,
            subtypes=interaction_model.subtypes
        )

    def create_disease_association(self, tx: Transaction, gene: Dict[str, Any], disease_id: str, evidence: str):
        """
        Create an ASSOCIATED_WITH relationship between Gene and Disease nodes in the Neo4j database.

        Args:
            tx: Neo4j transaction object.
            gene: Dictionary containing gene data.
            disease_id: ID of the associated disease.
            evidence: Evidence for the association.
        """
        try:
            gene_model = GeneData(**gene)
        except ValidationError as e:
            print(f"Validation error for gene {gene['gene_id']}: {e}")
            return

        tx.run(
            """
            MATCH (g:Gene {unique_id: $unique_id})
            MATCH (d:Disease {disease_id: $disease_id})
            MERGE (g)-[r:ASSOCIATED_WITH {evidence: $evidence}]->(d)
            """,
            unique_id=f"{disease_id}_{gene_model.gene_id}",
            disease_id=disease_id,
            evidence=evidence
        )

    def create_go_association(self, tx: Transaction, gene: Dict[str, Any], disease_id: str):
        """
        Create a HAS_GO_ANNOTATION relationship between Gene and GO Annotation nodes in the Neo4j database.

        Args:
            tx: Neo4j transaction object.
            gene: Dictionary containing gene data.
            disease_id: ID of the associated disease.
        """
        try:
            gene_model = GeneData(**gene)
        except ValidationError as e:
            print(f"Validation error for gene {gene['gene_id']}: {e}")
            return

        tx.run(
            """
            MATCH (g:Gene {unique_id: $unique_id})
            MATCH (a:GO_Annotation {qualifier: $qualifier, GO_ID: $GO_ID})
            MERGE (g)-[r:HAS_GO_ANNOTATION]->(a)
            """,
            unique_id=f"{disease_id}_{gene_model.gene_id}",
            qualifier=gene_model.Qualifier,
            GO_ID=gene_model.GO_ID
        )

    def import_data(self, kgml_files: List[str]):
        """
        Import data from KGML files and a merged DataFrame into the Neo4j database.

        Args:
            kgml_files: List of file paths to KGML files.
            merged: DataFrame containing merged data.
        """
        with self.driver.session() as session:
            for kgml_file_path in kgml_files:
                pathway_data = parse_kgml(kgml_file_path)
                disease_id = pathway_data['pathway_id']
                disease_name = pathway_data['pathway_name']
                
                # Create disease node
                session.write_transaction(self.create_disease_node, {
                    'disease_id': disease_id,
                    'name': disease_name
                })

                #Create dataframe integrating KGML genes and associated GO terms
                merged=kegg_go_integration(kgml_file_path,gaf_path)

                # Create gene nodes and their associations with the disease
                for _, df in merged.groupby('gene_id'):
                    for _, gene in df.iterrows():
                        session.write_transaction(self.create_gene_node, gene.to_dict(), disease_id)
                        session.write_transaction(self.create_go_node, gene.to_dict())
                        session.write_transaction(self.create_disease_association, gene.to_dict(), disease_id, evidence="from KGML")
                        session.write_transaction(self.create_go_association, gene.to_dict(), disease_id)
                        
                # Create interactions between genes
                for interaction in pathway_data['interactions']:
                    session.write_transaction(self.create_gene_interaction, interaction, disease_id)




