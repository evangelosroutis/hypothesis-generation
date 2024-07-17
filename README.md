# Hypothesis Generation

Hypothesis Generation is a Python project designed to interact with a Neo4j graph database, where we import data from KEGG and GO databases and generate responses to questions about genes and their interactions using agentic techniques. It includes functionalities for querying the database, generating Cypher queries, and producing meaningful responses based on the data retrieved.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Data Importer Overview](#dataimporter)
- [Tools Overview](#tools)
- [Evaluation Overview](#evaluation)

## Installation

1. **Clone the repository**:
    ```sh
    git clone https://github.com/evangelosroutis/hypothesis-generation.git
    ```
2. **Create the conda environment**:
    ```sh
    conda env create -f environment.yml
    ```
3. **Activate the environment**:
    ```sh
    conda activate newenv
    ```
4. **Set up the environment variables**:
    Create a `.env` file in the root directory of the project and add the following:
    ```env
    OPENAI_API_KEY=your_openai_api_key
    NEO4J_URI=your_neo4j_uri
    NEO4J_USER=your_neo4j_username
    NEO4J_PASSWORD=your_neo4j_password
    ```

## Usage

### Please refer to demo.ipynb for a detailed demonstration of how to import the data and use the agent with concrete examples

### Import the data to Neo4j
```python
from neo4j import GraphDatabase
from data_importer import KGMLGAFImporter
import os
from dotenv import load_dotenv
load_dotenv()

#load config
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)
    
#Load and define global variables
uri = os.getenv('NEO4J_URI')
user = os.getenv('NEO4J_USER')
password = os.getenv('NEO4J_PASSWORD')
config_path = 'config.yaml'
#dictionary from aspect symbols to their explanation, ie aspect_dict={P: "Biological Process" F: "Molecular Function" C: "Cellular Component"}
aspect_dict=config['aspect_dict']
#list of .xml pathway files from KEGG
kgml_files = config['kgml']['files']
kgml_file_paths = [os.path.join(kgml_directory, file) for file in kgml_files]
#path to GAF file for human
gaf_path=config['gaf_path']

# Connect to the Neo4j database
driver = GraphDatabase.driver(uri, auth=(user, password))

# Import the data
importer = KGMLGAFImporter(driver)
importer.import_data(kgml_file_paths, gaf_path, aspect_dict)
importer.close()
```

### Running the Agent
Here's an example of how to instantiate and use the custom agent:

```python
from tools import CustomAgent

# Load environment variables
import os
from dotenv import load_dotenv
load_dotenv()

uri = os.getenv('NEO4J_URI')
user = os.getenv('NEO4J_USER')
password = os.getenv('NEO4J_PASSWORD')
api_key = os.getenv('OPENAI_API_KEY')
config_path = 'config.yaml'


# Instantiate the custom agent
custom_agent = CustomAgent(uri, user, password, api_key, config_path)

# Ask a question
response = custom_agent.ask("What are the downstream interactions of gene INS in the pathway Type II diabetes mellitus?")
print(response)
```

## Evaluating the Tools
You can evaluate the tool selection process of the CustonAgent and the correctness of the Cypher queries as follows:

### Tool Selection Evaluation
```python
from evaluation import evaluate_tool_selection

dataset = [
    {"question": "What disease is PRKN associated with?", "label": "disease_association"},
    {"question": "What are the downstream interactions of gene PARK7?", "label": "downstream_interaction"}
]

df = evaluate_tool_selection(custom_agent, dataset)
print(df)
```

### Cypher Query Evaluation
```python
from evaluation import evaluate_run_cypher_query

dataset = [
    {
        "question": "What are the downstream interactions of gene PARK7?",
        "expected_cypher_query": """
            MATCH (start: Gene)
            WHERE ('PARK7' IN start.names) OR ('PARK7' IN start.synonyms)
            CALL apoc.path.expandConfig(start, {relationshipFilter: 'INTERACTS_WITH>', minLevel: 1, uniqueness: 'NODE_PATH', bfs: false}) 
            YIELD path
            WITH path
            WHERE NOT EXISTS {
                MATCH (lastNode)-[:INTERACTS_WITH]->(:Gene)
                WHERE lastNode = last(nodes(path))
            }
            WITH path, [rel IN relationships(path) | {start: startNode(rel), end: endNode(rel), type: rel.type, subtypes: rel.subtypes}] AS relationships
            RETURN collect(relationships) AS interactions
        """
    },
    #add more examples as needed
]
context='downstream_interaction'
df = evaluate_run_cypher_query(custom_agent, dataset, context)
print(df)
```



## Data Importer Overview

The `data_importer.py` module's purpose is to import data from KGML and GAF files into a Neo4j graph database. This script utilizes the Neo4j Python driver, Pydantic models for data validation, and custom utility functions for preprocessing. The primary class in this module, `KGMLGAFImporter`, provides methods for creating nodes and relationships in the Neo4j database based on gene-disease associations and gene-gene interactions.

### Classes and Methods

#### GeneData (Pydantic Model)

**Purpose**:
Represents and validates gene data, handling default values and NaN values.

**Attributes**:
- `gene_id`: Unique identifier for the gene.
- `Qualifier`: Qualifier for the gene annotation.
- `GO_ID`: Gene Ontology ID.
- `Aspect`: Aspect of the gene ontology.
- `DB_Object_Type`: Type of the database object.
- `DB_Object_Name`: List of names for the database object.
- `DB_Object_Synonym`: List of synonyms for the database object.
- `GO_label`: Label for the Gene Ontology term.
- `GO_definition`: Definition for the Gene Ontology term.

#### Disease (Pydantic Model)

**Purpose**:
Represents and validates disease data.

**Attributes**:
- `disease_id`: Unique identifier for the disease.
- `name`: Name of the disease.

#### GeneInteraction (Pydantic Model)

**Purpose**:
Represents and validates gene interaction data.

**Attributes**:
- `entry1`: Identifier for the first gene in the interaction.
- `entry2`: Identifier for the second gene in the interaction.
- `type`: Type of interaction.
- `subtypes`: List of subtypes for the interaction.

### KGMLGAFImporter (Class)

**Purpose**:
Handles the import of KGML and GAF data into a Neo4j database, creating necessary nodes and relationships.

**Methods**:

- `__init__(self, driver: GraphDatabase.driver)`:
  Initializes the importer with a Neo4j driver.
  
  **Args**:
  - `driver`: Neo4j driver for database connection.

- `close(self)`:
  Closes the Neo4j driver connection.

- `create_gene_node(self, tx: Transaction, gene: Dict[str, Any], disease_id: str)`:
  Creates a Gene node in the Neo4j database.

  **Args**:
  - `tx`: Neo4j transaction object.
  - `gene`: Dictionary containing gene data.
  - `disease_id`: ID of the associated disease.

- `create_disease_node(self, tx: Transaction, disease: Dict[str, Any])`:
  Creates a Disease node in the Neo4j database.

  **Args**:
  - `tx`: Neo4j transaction object.
  - `disease`: Dictionary containing disease data.

- `create_go_node(self, tx: Transaction, gene: Dict[str, Any])`:
  Creates a GO Annotation node in the Neo4j database.

  **Args**:
  - `tx`: Neo4j transaction object.
  - `gene`: Dictionary containing gene data.

- `create_gene_interaction(self, tx: Transaction, interaction: Dict[str, Any], disease_id: str)`:
  Creates an INTERACTS_WITH relationship between Gene nodes in the Neo4j database.

  **Args**:
  - `tx`: Neo4j transaction object.
  - `interaction`: Dictionary containing interaction data.
  - `disease_id`: ID of the associated disease.

- `create_disease_association(self, tx: Transaction, gene: Dict[str, Any], disease_id: str, evidence: str)`:
  Creates an ASSOCIATED_WITH relationship between Gene and Disease nodes in the Neo4j database.

  **Args**:
  - `tx`: Neo4j transaction object.
  - `gene`: Dictionary containing gene data.
  - `disease_id`: ID of the associated disease.
  - `evidence`: Evidence for the association.

- `create_go_association(self, tx: Transaction, gene: Dict[str, Any], disease_id: str)`:
  Creates a HAS_GO_ANNOTATION relationship between Gene and GO Annotation nodes in the Neo4j database.

  **Args**:
  - `tx`: Neo4j transaction object.
  - `gene`: Dictionary containing gene data.
  - `disease_id`: ID of the associated disease.

- `import_data(self, kgml_files: List[str], gaf_path: str, aspect_dict: dict)`:
  Imports data from KGML files and a merged DataFrame into the Neo4j database.

  **Args**:
  - `kgml_files`: List of file paths to KGML files.
  - `gaf_path`: Path to the GAF file.
  - `aspect_dict`: Dictionary for mapping aspects.

**Example Usage**:
```python
from neo4j import GraphDatabase
from data_importer import KGMLGAFImporter

# Connect to the Neo4j database
uri = "bolt://localhost:7687"
user = "your_neo4j_username"
password = "your_neo4j_password"

# Initialize the Neo4j driver
driver = GraphDatabase.driver(uri, auth=(user, password))

# Define KGML files and GAF file path
kgml_files = [
    'data/KGML/hsa04930.xml',
    'data/KGML/hsa05010.xml',
    'data/KGML/hsa05012.xml',
    'data/KGML/hsa05210.xml'
]
gaf_path = 'data/GAF/goa_human.gaf'
aspect_dict = {"P": "biological_process", "F": "molecular_function", "C": "cellular_component"}

# Import data
importer = KGMLGAFImporter(driver)
importer.import_data(kgml_files, gaf_path, aspect_dict)

# Close the connection
importer.close()
```

### Benefits of `data_importer.py`

1. **Structured Data Import**:
   - Provides a systematic approach to importing complex biological data into a Neo4j database, ensuring data integrity and consistency.
   
2. **Validation and Error Handling**:
   - Uses Pydantic models to validate data, handle default values, and manage NaN values, reducing the risk of data corruption.

3. **Reusability and Maintainability**:
   - Encapsulates data import logic in a class with well-defined methods, making the codebase easier to maintain and extend.

4. **Enhanced Query Capabilities**:
   - By structuring data in a graph database, it allows for complex queries and analyses that can reveal insights into gene-disease associations and gene-gene interactions.


## Tools Overview

The `tools.py` module is a core component of this project, designed to provide a flexible and powerful system for querying a Neo4j graph database and generating responses using OpenAI's API. This module includes several classes that together form a system for interacting with a Neo4j database and generating intelligent responses to questions about gene interactions.

### Classes

#### 1. BaseAgent

**Purpose**: 
The `BaseAgent` class serves as the foundational class for interacting with a Neo4j graph database and generating responses using the OpenAI API. 

**Key Functionalities**:
- **Connecting to Neo4j**: Connects to a Neo4j graph database using provided credentials.
- **Configuration Management**: Loads configuration settings from a YAML file.
- **Query Generation and Execution**: Generates and executes Cypher queries.
- **Error Handling**: Handles retries for Cypher queries with syntax errors by generating corrected queries.
- **Prompt Formatting**: Formats and sends prompts to the OpenAI API to generate responses based on the data retrieved from the database.

**Methods**:
- `load_config(path: str) -> dict`: Loads configuration settings from a YAML file.
- `generate(prompt_template: str, temperature: float = 0, **kwargs) -> str`: Generates a response using the OpenAI API based on a given prompt template and additional arguments.
- `run_cypher_query(cypher_statement: str, retry: bool = True, verbose: bool = False) -> dict`: Executes a Cypher query against the Neo4j database and handles retries in case of syntax errors.
- `generate_cypher_retry(cypher_statement: str, error_message: str) -> str`: Generates a corrected Cypher query in case of a syntax error.
- `set_prompt_context(context: str)`: Sets the current prompt context based on the configuration settings.

#### 2. DiseaseAssociation

**Purpose**:
The `DiseaseAssociation` class extends the `BaseAgent` class to handle specific queries related to disease-gene associations in a Neo4j graph database.

**Key Functionalities**:
- **Context Setting**: Sets the context for disease association-related prompts.
- **Query Generation**: Generates initial Cypher statements to query the graph database.
- **Data Retrieval**: Executes Cypher queries to fetch disease association data.
- **Response Generation**: Generates responses using the OpenAI API based on the queried data and predefined prompt templates.

**Methods**:
- `generate_response(question: str, verbose: bool = False) -> str`: Generates a response for a given question about disease associations by querying the graph database and formatting the result using OpenAI.

#### 3. DownstreamInteraction

**Purpose**:
The `DownstreamInteraction` class extends the `BaseAgent` class to handle specific queries related to downstream interactions in a Neo4j graph database.

**Key Functionalities**:
- **Context Setting**: Sets the context for downstream interaction-related prompts.
- **Query Generation**: Generates initial Cypher statements to query the graph database.
- **Data Retrieval**: Executes Cypher queries to fetch downstream interaction data.
- **Similarity Search**: Performs similarity searches to enhance interaction descriptions.
- **Response Generation**: Generates responses using the OpenAI API based on the queried data and predefined prompt templates.

**Methods**:
- `get_go_ids(unique_id: str) -> List[str]`: Retrieves GO IDs associated with a gene unique ID.
- `perform_similarity_search(interaction: Dict[str, Any], go_list: List[str]) -> str`: Performs a similarity search using the interaction details and GO IDs.
- `process_interaction(interaction: Dict[str, Any]) -> str`: Processes an interaction to generate a descriptive response.
- `generate_response(question: str, verbose: bool = False) -> List[List[str]]`: Generates a response for a given question about downstream interactions by querying the graph database, performing similarity searches, and formatting the results using the OpenAI API.

#### 4. CustomAgent

**Purpose**:
The `CustomAgent` class inherits from `BaseAgent` to handle questions related to disease associations and downstream interactions. It uses prompt fine-tuning and OpenAI to classify questions and selects the appropriate tool (`DiseaseAssociation` or `DownstreamInteraction`) to generate responses.

**Methods**:
- `classify_question(question: str) -> str`: Uses OpenAI to classify questions and determine which tool to use.
- `select_tool(question: str) -> Callable[[str], str]`: Selects the appropriate tool based on the classified question.
- `ask(question: str, verbose: bool = False) -> str`: Routes the question to the selected method and returns the response.

**Example Usage**:
```python
from custom_agent import CustomAgent

# Load environment variables
import os
from dotenv import load_dotenv
load_dotenv()

uri = os.getenv('NEO4J_URI')
user = os.getenv('NEO4J_USER')
password = os.getenv('NEO4J_PASSWORD')
api_key = os.getenv('OPENAI_API_KEY')
config_path = 'config.yaml'

# Instantiate the custom agent
custom_agent = CustomAgent(uri, user, password, api_key, config_path)

# Ask a question
response = custom_agent.ask("What are the downstream interactions of gene INS in the pathway Type II diabetes mellitus?")
print(response)
```

### Benefits of `tools.py` Over Off-the-Shelf Packages

1. **Customizability**: Allows fine-grained control over the querying and response generation processes, necessary for specific use cases.
2. **Inspection**: Methods are designed to allow for detailed inspection and debugging. For example, the run_cypher_query method in BaseAgent can print the Cypher query if the verbose flag is set, facilitating debugging and query validation.
3. **Evaluation**: Custom evaluation functions can be designed to assess the performance of the agent’s methods. This allows for precise measurement of the agent’s accuracy and reliability, which is crucial for scientific and industrial applications. We have already implemented some of those in the evaluation.py module.



## Evaluation Overview

The `evaluation.py` module provides essential functions for evaluating the performance and accuracy of the custom agents developed in this project. This script includes methods for assessing the tool selection process, the accuracy of generated Cypher queries, and the final response correctness. These evaluations help ensure that the agents are performing as expected and producing reliable results.

### Functions

#### 1. `evaluate_tool_selection`

**Purpose**:
Evaluates the tool selection performance of the `CustomAgent` by comparing the agent's selected tool against the expected tool label for a given dataset of questions.

**Arguments**:
- `agent (CustomAgent)`: The custom agent to be evaluated.
- `dataset (List[Dict[str, str]])`: A labeled dataset containing questions and expected tool labels.

**Returns**:
- `float`: The accuracy of the tool selection.
- `pd.DataFrame`: A DataFrame containing the results of the evaluation.

**Example Usage**:
```python
from evaluation import evaluate_tool_selection

dataset = [
    {"question": "What disease is PRKN associated with?", "label": "disease_association"},
    {"question": "What are the downstream interactions of gene PARK7?", "label": "downstream_interaction"}
]

df = evaluate_tool_selection(custom_agent, dataset)
print(df)
```

#### 2. `evaluate_run_cypher_query`

**Purpose**:
Evaluates the `run_cypher_query` method of the `CustomAgent` by comparing the agent's generated Cypher queries and results with manually labeled Cypher queries and their results.

**Arguments**:
- `agent (CustomAgent)`: The custom agent to be tested.
- `dataset (list)`: List of questions and their expected Cypher queries.
- `context (str)`: The prompt context to set for the agent (ie 'disease_association' or 'downstream_interaction').

**Returns**:
- `pd.DataFrame`: A DataFrame containing the questions, generated Cypher queries, labeled Cypher queries, agent results, manual results, and whether the results match.

**Example Usage**:
```python
from evaluation import evaluate_run_cypher_query

dataset = [
    {
        "question": "What are the downstream interactions of gene PARK7?",
        "expected_cypher_query": """
            MATCH (start: Gene)
            WHERE ('PARK7' IN start.names) OR ('PARK7' IN start.synonyms)
            CALL apoc.path.expandConfig(start, {relationshipFilter: 'INTERACTS_WITH>', minLevel: 1, uniqueness: 'NODE_PATH', bfs: false}) 
            YIELD path
            WITH path
            WHERE NOT EXISTS {
                MATCH (lastNode)-[:INTERACTS_WITH]->(:Gene)
                WHERE lastNode = last(nodes(path))
            }
            WITH path, [rel IN relationships(path) | {start: startNode(rel), end: endNode(rel), type: rel.type, subtypes: rel.subtypes}] AS relationships
            RETURN collect(relationships) AS interactions
        """
    },
    # Add more examples as needed
]

df = evaluate_run_cypher_query(custom_agent, dataset, context='downstream_interaction')
print(df)
```

#### 3. `evaluate_final_response`

**Purpose**:
Evaluates the final response generated by the `CustomAgent` for correctness and relevance using an LLM as a judge. This function compares the agent's responses with manually obtained results.

**Arguments**:
- `agent (CustomAgent)`: The custom agent to be tested.
- `dataset (list)`: List of questions and their expected Cypher queries.
- `context (str)`: The prompt context to set for the agent.

**Returns**:
- `pd.DataFrame`: A DataFrame containing the questions, final responses, manual results, and correctness judgments.

**Example Usage**:
```python
from evaluation import evaluate_final_response

dataset = [
    {
        "question": "What are the downstream interactions of gene PARK7?",
        "expected_cypher_query": """
            MATCH (start: Gene)
            WHERE ('PARK7' IN start.names) OR ('PARK7' IN start.synonyms)
            CALL apoc.path.expandConfig(start, {relationshipFilter: 'INTERACTS_WITH>', minLevel: 1, uniqueness: 'NODE_PATH', bfs: false}) 
            YIELD path
            WITH path
            WHERE NOT EXISTS {
                MATCH (lastNode)-[:INTERACTS_WITH]->(:Gene)
                WHERE lastNode = last(nodes(path))
            }
            WITH path, [rel IN relationships(path) | {start: startNode(rel), end: endNode(rel), type: rel.type, subtypes: rel.subtypes}] AS relationships
            RETURN collect(relationships) AS interactions
        """
    },
    # Add more examples as needed
]

df = evaluate_final_response(custom_agent, dataset, context='downstream_interaction')
print(df)
```

### Benefits of `evaluation.py`

1. **Performance Assessment**: Provides a structured way to measure the accuracy and performance of the custom agents, ensuring they meet the expected standards.
2. **Debugging and Improvement**: Identifies areas where the agent's performance can be improved by highlighting discrepancies between the expected and actual results.
3. **Transparency and Reliability**: Enhances the reliability of the agents by systematically evaluating their outputs against known benchmarks.
4. **Comparison to Off-the-Shelf Solutions**:
 - Allows for detailed inspection and evaluation of each step in the query and response generation process.

The `evaluation.py` module is an essential part of ensuring the custom agents developed in this project are accurate, reliable, and performant.

