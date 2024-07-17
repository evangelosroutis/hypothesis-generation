# Hypothesis Generation

Hypothesis Generation is a Python project designed to interact with a Neo4j graph database, where we import data from KEGG and GO databases and generate responses to questions about genes and their interactions using agentic techniques. It includes functionalities for querying the database, generating Cypher queries, and producing meaningful responses based on the data retrieved.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Examples](#examples)
- [Contributing](#contributing)
- [License](#license)
- [Contact Information](#contact-information)

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
