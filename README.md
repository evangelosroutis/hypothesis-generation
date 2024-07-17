# Hypothesis Generation

Hypothesis Generation is a Python project designed to interact with a Neo4j graph database, where we import data from KEGG and GO databases and generate responses to questions about genes and their interactions using agentic techniques. It includes functionalities for querying the database, generating Cypher queries, and producing meaningful responses based on the data retrieved.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Tools overview](#examples)

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

### Please refer to demo.ipynb for a detailed demonstration of how to import the data and use the agent

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
The `CustomAgent` class inherits from `BaseAgent` to handle questions related to disease associations and downstream interactions. It uses OpenAI to classify questions and selects the appropriate tool (`DiseaseAssociation` or `DownstreamInteraction`) to generate responses.

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
2. **Inspection and Evaluation:**: 
**Inspection**: Methods are designed to allow for detailed inspection and debugging. For example, the run_cypher_query method in BaseAgent can print the Cypher query if the verbose flag is set, facilitating debugging and query validation.
**Evaluation**: Custom evaluation functions can be designed to assess the performance of the agent’s methods. This allows for precise measurement of the agent’s accuracy and reliability, which is crucial for scientific and industrial applications. We have already implemented some of those in the evaluation.py module.


