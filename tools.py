from neo4j.exceptions import CypherSyntaxError
import textwrap
from openai import OpenAI
from typing import Callable
from langchain_community.graphs.neo4j_graph import Neo4jGraph
import yaml
from neo4j.exceptions import CypherSyntaxError
from langchain.vectorstores.neo4j_vector import Neo4jVector
from langchain.embeddings.openai import OpenAIEmbeddings
from typing import Any, Dict, List
from utilities.preprocessing import dict_to_frozenset


class BaseAgent:
    """
    The BaseAgent class serves as a foundational class for interacting with a Neo4j graph database
    and generating responses using the OpenAI API. This class provides methods for querying the database,
    handling Cypher query retries in case of syntax errors, and formatting prompts for the OpenAI API.

    Key functionalities include:
    - Connecting to a Neo4j graph database using provided credentials.
    - Loading configuration settings from a YAML file.
    - Generating and executing Cypher queries.
    - Handling retries for Cypher queries with syntax errors by generating corrected queries.
    - Formatting and sending prompts to the OpenAI API to generate responses based on the data retrieved from the database.

    Methods:
        load_config(path: str) -> dict:
            Loads configuration settings from a specified YAML file.
        
        generate(prompt_template: str, temperature: float = 0, **kwargs) -> str:
            Generates a response using the OpenAI API based on a given prompt template and additional arguments.
        
        run_cypher_query(cypher_statement: str, retry: bool = True) -> dict:
            Executes a Cypher query against the Neo4j database and handles retries in case of syntax errors.
        
        generate_cypher_retry(cypher_statement: str, error_message: str) -> str:
            Generates a corrected Cypher query in case of a syntax error.
        
        set_prompt_context(context: str):
            Sets the current prompt context based on the configuration settings.

    Usage:
        This class is intended to be extended by other classes that require interaction with a Neo4j database
        and OpenAI API. Subclasses can leverage the provided methods to execute database queries and generate
        meaningful responses based on those queries.

    """

    def __init__(self, uri: str, user: str, password: str, api_key: str, config_path: str):
        """
        Initialize the BaseAgent with Neo4jGraph, OpenAI API key, and configuration.

        Args:
            uri (str): URI for the Neo4j database.
            user (str): Username for the Neo4j database.
            password (str): Password for the Neo4j database.
            api_key (str): API key for OpenAI.
            config_path (str): Path to the configuration YAML file.
        """
        self.kg = Neo4jGraph(url=uri, username=user, password=password)
        self.api_key = api_key
        self.config = self.load_config(config_path)
        self.schema = textwrap.fill(self.kg.schema, 60)

    def load_config(self, path: str) -> dict:
        """
        Load configuration from a YAML file.

        Args:
            path (str): Path to the YAML configuration file.

        Returns:
            dict: Configuration dictionary.
        """
        with open(path, 'r') as file:
            return yaml.safe_load(file)

    def generate(self, prompt_template: str, temperature: float = 0, **kwargs) -> str:
        """
        Generate a response using the OpenAI API.

        Args:
            prompt_template (str): Template for the prompt to be sent to OpenAI.
            temperature (float, optional): Sampling temperature for OpenAI completion. Defaults to 0.
            **kwargs: Additional keyword arguments for formatting the prompt.

        Returns:
            str: Generated response from OpenAI.
        """
        prompt = prompt_template.format(**kwargs)
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": kwargs.get('question', '')},
        ]

        client = OpenAI(api_key=self.api_key)

        completions = client.chat.completions.create(
            model="gpt-4o",
            temperature=temperature,
            messages=messages,
            max_tokens=500
        )
        return completions.choices[0].message.content

    def run_cypher_query(self, cypher_statement: str, retry: bool = True, verbose: bool = False) -> dict:
        """
        Execute a Cypher query against the Neo4j database.

        Args:
            cypher_statement (str): Cypher query to be executed.
            retry (bool, optional): Whether to retry the query in case of a Cypher syntax error. Defaults to True.

        Returns:
            dict: Result of the Cypher query.

        Raises:
            CypherSyntaxError: If the Cypher query has a syntax error and retry is False.
        """
        try:
            if verbose:
                print(cypher_statement)
            return self.kg.query(cypher_statement)
        except CypherSyntaxError as e:
            if retry:
                print("Retrying due to Cypher syntax error...")
                return self.generate_cypher_retry(cypher_statement, str(e))
            else:
                raise e

    def generate_cypher_retry(self, cypher_statement: str, error_message: str) -> str:
        """
        Generate a corrected Cypher query in case of a syntax error.

        Args:
            cypher_statement (str): Original Cypher query that caused the syntax error.
            error_message (str): Error message from the Cypher syntax error.

        Returns:
            str: Corrected Cypher query.
        """
        retry_prompt = self.current_prompts['retry_prompt']
        return self.generate(retry_prompt, cypher_statement=cypher_statement, error_message=error_message)
    
    def set_prompt_context(self, context: str):
        """
        Set the current prompt context based on the configuration.

        Args:
            context (str): Context key to set the current prompts.

        Raises:
            ValueError: If the context is not found in the configuration.
        """
        if context in self.config['prompts']:
            self.current_prompts = self.config['prompts'][context]
        else:
            raise ValueError(f"Context '{context}' not found in configuration.")
 

class DiseaseAssociation(BaseAgent):
    """
    The DiseaseAssociation class extends the BaseAgent class to handle specific queries related to disease associations
    in a Neo4j graph database. This class focuses on generating and executing Cypher queries to retrieve information
    about gene-disease associations and using the OpenAI API to format the retrieved information into meaningful responses.

    Key functionalities include:
    - Setting the context for disease association-related prompts.
    - Generating initial Cypher statements to query the graph database.
    - Executing Cypher queries to fetch disease association data.
    - Generating responses using the OpenAI API based on the queried data and predefined prompt templates.

    Methods:
        generate_response(question: str) -> str:
            Generates a response for a given question about disease associations by querying the graph database
            and formatting the result using the OpenAI API.

    Usage:
        This class is designed to be instantiated and used to answer questions related to disease associations.
        It leverages the functionalities provided by the BaseAgent class to interact with the Neo4j database
        and the OpenAI API, making it easier to generate meaningful and contextually accurate responses.
    """
    def __init__(self, uri: str, user: str, password: str, api_key: str, config_path: str):
        """
        Initialize the DiseaseAssociation with Neo4jGraph, OpenAI API key, and configuration.

        Args:
            uri (str): URI for the Neo4j database.
            user (str): Username for the Neo4j database.
            password (str): Password for the Neo4j database.
            api_key (str): API key for OpenAI.
            config_path (str): Path to the configuration YAML file.
        """        
        super().__init__(uri, user, password, api_key, config_path)
        
    def generate_response(self, question: str, verbose: bool =False) -> str:
        """
        Generate a response for a given question about disease associations.

        Args:
            question (str): The question to be answered.

        Returns:
            str: The generated response from OpenAI.
        """
        # Generate initial Cypher statement
        self.set_prompt_context('disease_association')
        initial_prompt = self.current_prompts['initial_prompt']
        cypher_statement = self.generate(initial_prompt, schema=self.schema, question=question)
        
        # Execute Cypher query and get results
        cypher_result = self.run_cypher_query(cypher_statement, verbose=verbose)

        # Generate final response
        final_prompt = self.current_prompts['final_prompt']
        final_response = self.generate(final_prompt, question=question, information=cypher_result)
        
        return final_response


class DownstreamInteraction(BaseAgent):
    """
    The DownstreamInteraction class extends the BaseAgent class to handle specific queries related to downstream interactions
    in a Neo4j graph database. This class focuses on generating and executing Cypher queries to retrieve information about
    gene-gene interactions and using the OpenAI API to format the retrieved information into meaningful responses.

    Key functionalities include:
    - Setting the context for downstream interaction-related prompts.
    - Generating initial Cypher statements to query the graph database.
    - Executing Cypher queries to fetch downstream interaction data.
    - Performing similarity searches to enhance interaction descriptions.
    - Generating responses using the OpenAI API based on the queried data and predefined prompt templates.

    Methods:
        get_go_ids(unique_id: str) -> List[str]:
            Retrieve GO IDs associated with a gene unique ID.
        
        perform_similarity_search(interaction: Dict[str, Any], go_list: List[str]) -> str:
            Perform a similarity search using the interaction details and GO IDs.
        
        process_interaction(interaction: Dict[str, Any]) -> str:
            Process an interaction to generate a descriptive response.
        
        generate_response(question: str) -> List[List[str]]:
            Generate a response for a given question about downstream interactions by querying the graph database,
            performing similarity searches and formatting the results using the OpenAI API.

    Usage:
        This class is designed to be instantiated and used to answer questions related to downstream interactions.
        It leverages the functionalities provided by the BaseAgent class to interact with the Neo4j database
        and the OpenAI API, making it easier to generate meaningful and contextually accurate responses.

    Example:
        downstream_agent = DownstreamInteraction(uri, user, password, api_key, config_path='config.yaml')
        response = downstream_agent.generate_response("What are the downstream interactions of gene Y?")
        print(response)
    """
    vector_index = None

    def __init__(self, uri: str, user: str, password: str, api_key: str, config_path: str):
        """
        Initialize the DownstreamInteraction with Neo4jGraph, OpenAI API key, and configuration.

        Args:
            uri (str): URI for the Neo4j database.
            user (str): Username for the Neo4j database.
            password (str): Password for the Neo4j database.
            api_key (str): API key for OpenAI.
            config_path (str): Path to the configuration YAML file.
        """
        super().__init__(uri, user, password, api_key, config_path)
        if DownstreamInteraction.vector_index is None:
            DownstreamInteraction.vector_index = Neo4jVector.from_existing_graph(
                OpenAIEmbeddings(api_key=api_key),
                url=uri,
                username=user,
                password=password,
                index_name='go_ids',
                node_label="GO_Annotation",
                text_node_properties=['qualifier', 'name', 'definition','aspect'],
                embedding_node_property='embedding',
            )

    def get_go_ids(self, unique_id: str) -> List[str]:
        """
        Retrieve GO IDs associated with a gene unique ID.

        Args:
            unique_id (str): Unique ID of the gene.

        Returns:
            List[str]: List of GO IDs associated with the gene.
        """
        go_result = self.kg.query(
            """
            MATCH (g: Gene {unique_id:$unique_id})-[:HAS_GO_ANNOTATION]->(a: GO_Annotation)
            RETURN collect(a.GO_ID) as GO_ID
            """,
            params={'unique_id': unique_id} 
        )
        go_list = go_result[0]['GO_ID']
        return go_list

    def perform_similarity_search(self, interaction: Dict[str, Any], go_list: List[str]) -> str:
        """
        Perform a similarity search using the interaction details and GO IDs.

        Args:
            interaction (Dict[str, Any]): Interaction details.
            go_list (List[str]): List of GO IDs.

        Returns:
            str: Description of the interaction from the similarity search.
        """
        start_node_names=interaction['start'].get('names')
        end_node_names=interaction['end'].get('names')
        subtype=interaction['subtypes']
        interaction_type=self.config['interaction_type_dict'].get(interaction['type'])

        #Form crude search query consisting of start and end node gene names, as well as (sub)type of the interaction connecting them (eg activation, inhibition etc).
        search_query = f"{start_node_names}, {subtype}, {end_node_names}, {interaction_type}"

        #Perform similarity search based on the search_query- filter for GO_IDs in go_list.
        response = DownstreamInteraction.vector_index.similarity_search(
            search_query, k=1,
            filter={'GO_ID': {"$in": go_list}}
        )
        return response[0].page_content

    def process_interaction(self, interaction: Dict[str, Any]) -> str:
        """
        Process an interaction to generate a descriptive response.

        Args:
            interaction (Dict[str, Any]): Interaction details.

        Returns:
            str: Generated response describing the interaction.
        """
        unique_id = interaction['start'].get('unique_id')

        #Retrieve the list of GO_IDs that are connected to the start node
        go_list = self.get_go_ids(unique_id)

        #Perform similarity search between the interaction and the go_list of GO_IDs of the first node
        interaction_description = self.perform_similarity_search(interaction,go_list)
        
        #Form a suitable prompt and question based on the interaction data to generate the final response.
        final_prompt = self.current_prompts['final_prompt']
        start_node_names=[interaction['start'].get('names')]
        end_node_names=[interaction['end'].get('names')]
        question=f"Please describe the interaction of {start_node_names} with {end_node_names} using the description {interaction_description}."
        final_response = self.generate(
            final_prompt,
            temperature=0,
            question=question
        )
        return final_response

    def generate_response(self, question: str, verbose: bool =False) -> List[List[str]]:
        """
        Generate a response for a given question about downstream interactions.

        Args:
            question (str): The question to be answered.

        Returns:
            List[List[str]]: List of all distinct downstream interaction paths from the specified gene node.
        """
        # Set the context for downstream interaction prompts
        self.set_prompt_context('downstream_interaction')
        
        # Generate initial Cypher statement
        initial_prompt = self.current_prompts['initial_prompt']
        cypher_statement = self.generate(initial_prompt, schema=self.schema, question=question)
        
        # Execute Cypher query and get results
        cypher_result = self.run_cypher_query(cypher_statement, verbose=verbose)
        
        processed_interactions = {}
        all_paths_list = []
        for path in cypher_result[0]['interactions']:
            path_list=[]
            for interaction in path:
                interaction_frozenset = dict_to_frozenset(interaction)
        
                # Check if this interaction has already been processed
                if interaction_frozenset in processed_interactions:
                    # Retrieve the result from the dictionary and append it to path_description
                    path_list.append(processed_interactions[interaction_frozenset])
                    continue
                interaction_result=self.process_interaction(interaction)
                path_list.append(interaction_result)
                processed_interactions[interaction_frozenset] = interaction_result
            all_paths_list.append(path_list)

        if not all_paths_list:
            return "I could not find the answer in the database. Please try again."
        
        print("The following are the distinct downstream interaction paths from the specified gene node:")
        return all_paths_list


class CustomAgent(BaseAgent):
    """
    CustomAgent class that inherits from BaseAgent to handle questions related to disease associations 
    and downstream interactions. It uses OpenAI to classify questions and selects the appropriate tool 
    (DiseaseAssociation or DownstreamInteraction) to generate responses.

    Example usage:
    config_path = 'config.yaml'
    custom_agent = CustomAgent(uri, user, password, api_key, config_path)
    response = custom_agent.ask("What are the downstream interactions of gene INS in the pathway Type II diabetes mellitus?")
    print(response)
    """
    def __init__(self, uri: str, user: str, password: str, api_key: str, config_path: str):
        """
        Initialize the CustomAgent with Neo4jGraph, OpenAI API key, and configuration.

        Args:
            uri (str): URI for the Neo4j database.
            user (str): Username for the Neo4j database.
            password (str): Password for the Neo4j database.
            api_key (str): API key for OpenAI.
            config_path (str): Path to the configuration YAML file.
        """
        super().__init__(uri, user, password, api_key, config_path)
        self.disease_association_agent = DiseaseAssociation(uri, user, password, api_key,config_path)
        self.downstream_interaction_agent = DownstreamInteraction(uri, user, password, api_key,config_path)

    def classify_question(self, question: str) -> str:
        """
        Classify the question using OpenAI to determine which tool to use.

        Args:
            question (str): The question to be classified.

        Returns:
            str: The classification result.
        """
        classification_prompt = self.config['prompts']['classification_prompt']
        prompt = classification_prompt.format(question=question)
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": question},
        ]
        client = OpenAI(api_key=self.api_key)
        completions = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0,
            max_tokens=10
        )
        return completions.choices[0].message.content.strip().lower()

    def select_tool(self, question: str) -> Callable[[str], str]:
        """
        Select the appropriate tool based on the classified question.

        Args:
            question (str): The question to be answered.

        Returns:
            Callable: The selected tool's generate_response method.
        
        Raises:
            ValueError: If the classification result is neither 'disease' nor 'downstream' is found in the classification result.
        """
        category = self.classify_question(question)
        if "disease" in category:
            return self.disease_association_agent.generate_response
        elif "downstream" in category:
            return self.downstream_interaction_agent.generate_response
        else:
            raise ValueError("No appropriate tool found for the given question.")

    def ask(self, question: str, verbose: bool = False) -> str:
        """
        Generate a response for a given question by selecting the appropriate tool.

        Args:
            question (str): The question to be answered.

        Returns:
            str: The generated response.
        """
        tool_func = self.select_tool(question)
        return tool_func(question, verbose=verbose)


