from typing import List, Dict
from tools import CustomAgent
import json
import pandas as pd


def evaluate_tool_selection(agent: CustomAgent, dataset: List[Dict[str, str]]) -> float:
    """
    Evaluate the tool selection performance of the CustomAgent.

    Args:
        agent (CustomAgent): The CustomAgent to be evaluated.
        dataset (List[Dict[str, str]]): The labeled dataset containing questions and expected tool labels.

    Returns:
        float: The accuracy of the tool selection.
    """
    correct_count = 0
    results = []

    for data in dataset:
        question = data["question"]
        label = data["label"]
        
        try:
            selected_tool_func = agent.select_tool(question)
            selected_tool = "disease_association" if selected_tool_func == agent.disease_association_agent.generate_response else "downstream_interaction"
        except ValueError:
            selected_tool = "none"
        
        # Determine if the tool selection was correct
        is_correct = (selected_tool == label)
        if is_correct:
            correct_count += 1

        # Append the result to the list
        results.append({
            "question": question,
            "expected_label": label,
            "predicted_label": selected_tool,
            "is_correct": is_correct
        })

    accuracy = correct_count / len(dataset)
    
    print(f"Accuracy={accuracy}")
    return(pd.DataFrame(results))



def evaluate_run_cypher_query(agent: CustomAgent, dataset: list, context: str) -> pd.DataFrame:
    """
    Evaluate the run_cypher_query method of the CustomAgent.

    Args:
        agent (CustomAgent): The CustomAgent to be tested.
        dataset (list): List of questions and their expected Cypher queries.
        context (str): The prompt context to set for the agent.

    Returns:
        pd.DataFrame: DataFrame containing the questions, generated Cypher queries, expected Cypher queries,
                      agent results, manual results, and whether the results match.
    """
    results = []

    for item in dataset:
        question = item["question"]
        expected_cypher_query = item["expected_cypher_query"].strip()

        # Set the appropriate context
        agent.set_prompt_context(context)

        # Generate Cypher query using the agent
        generated_cypher_query = agent.generate(agent.current_prompts['initial_prompt'], schema=agent.schema, question=question).strip()

        # Run the Cypher query using run_cypher_query method
        agent_result = agent.run_cypher_query(generated_cypher_query)

        # Run the expected Cypher query manually using kg.query
        manual_result = agent.kg.query(expected_cypher_query)

        # Compare the results
        results.append({
            "question": question,
            "generated_cypher_query": generated_cypher_query,
            "expected_cypher_query": expected_cypher_query,
            "agent_result": json.dumps(agent_result, indent=4),
            "manual_result": json.dumps(manual_result, indent=4),
            "match": agent_result == manual_result
        })

    # Create a DataFrame from the results
    df = pd.DataFrame(results)
    return df

