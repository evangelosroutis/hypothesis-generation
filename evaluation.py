from typing import List, Dict
from tools import CustomAgent

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

    for data in dataset:
        question = data["question"]
        label = data["label"]
        
        try:
            selected_tool_func = agent.select_tool(question)
            selected_tool = "disease_association" if selected_tool_func == agent.disease_association_agent.generate_response else "downstream_interaction"
        except ValueError:
            selected_tool = "none"

        # Determine if the tool selection was correct
        if selected_tool == label:
            correct_count += 1

    accuracy = correct_count / len(dataset)
    return accuracy
