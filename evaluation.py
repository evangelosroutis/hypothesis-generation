from typing import List, Dict
from tools import CustomAgent
import json
import pandas as pd
from openai import OpenAI


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
        include_final_response (bool): Whether to include the agent's final response in the DataFrame.

    Returns:
        pd.DataFrame: DataFrame containing the questions, generated Cypher queries, labeled Cypher queries,
                      agent results, manual results, and whether the results match.
    """
    results = []

    for item in dataset:
        question = item["question"]
        labeled_cypher_query = item["expected_cypher_query"].strip()

        # Set the appropriate context
        agent.set_prompt_context(context)

        # Generate Cypher query using the agent
        generated_cypher_query = agent.generate(agent.current_prompts['initial_prompt'], schema=agent.schema, question=question).strip()

        # Run the Cypher query using run_cypher_query method
        agent_result = agent.run_cypher_query(generated_cypher_query)

        # Run the expected Cypher query manually using kg.query
        manual_result = agent.kg.query(labeled_cypher_query)

        # Compare the results
        results.append({
            "question": question,
            "generated_cypher_query": generated_cypher_query,
            "labeled_cypher_query": labeled_cypher_query,
            "agent_result": json.dumps(agent_result, indent=4),
            "manual_result": json.dumps(manual_result, indent=4),
            "match": agent_result == manual_result,
        })

    return pd.DataFrame(results)

def evaluate_final_response(agent: CustomAgent, dataset: list, context:str) -> pd.DataFrame:
    """
    Evaluate the final response of the CustomAgent for correctness and relevance using an LLM as a judge.

    Args:
        agent (CustomAgent): The CustomAgent to be tested.
        dataset (list): List of questions and their expected Cypher queries.
        context (str): The prompt context to set for the agent.
        llm_judge_api_key (str): API key for the LLM used as a judge.

    Returns:
        pd.DataFrame: DataFrame containing the questions, final responses, manual results, and correctness judgments.
    """
    results = []

    for item in dataset:
        question = item["question"]
        expected_cypher_query = item["expected_cypher_query"].strip()
        
        # Set the appropriate context
        agent.set_prompt_context(context)

        # Generate the final response using the agent
        final_response = agent.ask(question).strip()

        # Run the expected Cypher query manually using kg.query
        manual_result = agent.kg.query(expected_cypher_query)

        # Load the evaluation prompt from the config
        evaluation_prompt_template = agent.current_prompts['evaluation_prompt']
        evaluation_prompt = evaluation_prompt_template.format(
            manual_result=json.dumps(manual_result, indent=4),
            question=question,
            final_response=final_response
        )

        # Use LLM as a judge to evaluate the correctness and relevance of the final response
        judge_client = OpenAI(api_key=agent.api_key)
        judge_response = judge_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an assistant that evaluates the correctness and relevance of responses."},
                {"role": "user", "content": evaluation_prompt}
            ],
            temperature=0,
            max_tokens=200
        )
        correctness_judgment = judge_response.choices[0].message.content.strip()

        # Append the results
        results.append({
            "question": question,
            "final_response": final_response,
            "manual_result": json.dumps(manual_result, indent=4),
            "correctness_judgment": correctness_judgment
        })
    
    return pd.DataFrame(results)