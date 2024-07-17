# Hypothesis Generation

Hypothesis Generation is a Python project designed to interact with a Neo4j graph database with imported data from KEGG and GO databases and generate responses to questions about genes and their interactions using agentic techniques. It includes functionalities for querying the database, generating Cypher queries, and producing meaningful responses based on the data retrieved.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Examples](#examples)
- [Contributing](#contributing)
- [License](#license)
- [Contact Information](#contact-information)

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

### Running the Agent
Here's an example of how to instantiate and use the custom agent:

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

## Evaluating the Tools
You can evaluate the tool selection process and the correctness of the Cypher queries as follows:

Tool Selection Evaluation
```python
Copy code
from evaluation import evaluate_tool_selection

dataset = [
    {"question": "What disease is PRKN associated with?", "label": "disease_association"},
    {"question": "What are the downstream interactions of gene PARK7?", "label": "downstream_interaction"}
]

accuracy, df = evaluate_tool_selection(custom_agent, dataset)
print(f"Accuracy: {accuracy}")
print(df)
Cypher Query Evaluation
python
Copy code
from evaluation import evaluate_cypher_queries

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

accuracy, df = evaluate_cypher_queries(custom_agent, dataset)
print(f"Accuracy: {accuracy}")
print(df)
```
