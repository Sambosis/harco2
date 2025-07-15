import openai
import os
import json
import re
import random
import asyncio
from dotenv import load_dotenv
load_dotenv()
from icecream import ic
from datetime import datetime

# Configure icecream to log to file instead of console
def log_to_file(*args):
    with open('game_debug.log', 'a', encoding='utf-8') as f:
        f.write(' '.join(str(arg) for arg in args) + '\n')

ic.configureOutput(includeContext=True, outputFunction=log_to_file)

# Hardcoded map for prompt, assuming these connections based on Harford County layout
LOCATIONS = [
    "Bel Air", "Aberdeen Proving Ground", "Havre de Grace",
    "Edgewood", "Joppatowne", "Fallston"
]

ADJACENCIES = {
    "Bel Air": ["Fallston", "Joppatowne", "Edgewood", "Aberdeen Proving Ground"],
    "Aberdeen Proving Ground": ["Edgewood", "Havre de Grace", "Bel Air"],
    "Havre de Grace": ["Aberdeen Proving Ground"],
    "Edgewood": ["Bel Air", "Joppatowne", "Aberdeen Proving Ground"],
    "Joppatowne": ["Bel Air", "Edgewood"],
    "Fallston": ["Bel Air"]
}

TEAM_MODELS = {
    'Red': 'o4-mini',
    'Blue': 'gpt-4.1'
}

client = openai.AsyncOpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

def extract_json_from_markdown(response):
    """
    Extracts JSON content from markdown code blocks.
    
    :param response: str, the raw response from the LLM
    :return: str, the JSON content or the original response if no code blocks found
    """
    # Look for JSON in code blocks (```json or just ```)
    code_block_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
    match = re.search(code_block_pattern, response, re.DOTALL)
    
    if match:
        json_content = match.group(1).strip()
        ic(f"Extracted JSON from code block: {json_content}")
        return json_content
    
    # If no code blocks found, return original response
    return response.strip()

async def get_action_plan(team, visible_state):
    """
    Generates a prompt for the LLM based on the team's visible game state and retrieves a JSON action plan.
    Retries up to 3 times if the response is not valid JSON.

    :param team: str, 'Blue' or 'Red'
    :param visible_state: dict, the visible state
    :return: tuple (dict action_plan, str final_prompt, str response)
    """
    visible_state_str = json.dumps(visible_state, indent=2)
    action_limit = visible_state.get('opponent_unit_count', 1)

    # Build map description
    map_desc = "Locations: " + ", ".join(LOCATIONS) + "\n"
    map_desc += "Connections:\n"
    for loc, adj in ADJACENCIES.items():
        map_desc += f"- {loc}: {', '.join(adj)}\n"

    # Base prompt
    prompt = f"""
You are the commander of the {team.upper()} Team in a turn-based strategy game set in Harford County, Maryland.

Game Goal: Win by controlling at least 5 out of 6 locations or by eliminating all enemy units. The game ends after a maximum of 120 turns if no winner.

Map:
{map_desc}

Game Mechanics:
- Teams alternate turns.
- You start with 5 infantry units, each with health.
- Locations provide resources (points) when controlled.
- Each turn, you gain resources from controlled locations.
- Actions: Move units to adjacent locations or reinforce by adding new units.
- Moving a unit to an adjacent location:
  - If neutral or empty, you can take control.
  - If enemy-controlled or has enemy units, it initiates an attack. Combat is resolved by a simple dice-roll simulation based on unit strengths (attacker vs. defender). Winner takes the location; units may lose health or be eliminated.
- **IMPORTANT RULE**: Your number of actions this turn is limited. The number of actions you can take is equal to the number of units your opponent has. Your opponent currently has {action_limit} units, so you can perform a maximum of {action_limit} actions this turn.
- Reinforce: Spend 3 resources to add a new unit at one of your controlled locations.
- Visibility: You see your units, controlled locations, resources, and partial intel on enemy positions (e.g., from scouts).

Current Visible State:
{visible_state_str}

Plan your actions for this turn. You can specify multiple actions, but respect unit limits and resources. Remember, you are limited to {action_limit} actions.

Output ONLY a valid JSON object in this format:
{{
  "actions": [
    {{"type": "move", "unit_id": "<string unit ID>", "to": "<adjacent location>"}},
    {{"type": "reinforce", "location": "<controlled location>"}}
    // Add more actions as needed, up to your action limit.
  ]
}}

Moves to enemy locations are treated as attacks. Do not include any other text or explanations.
"""

    response = None
    model_for_team = TEAM_MODELS.get(team, 'gpt-4o')

    for attempt in range(3):
        try:
            completion = ic(await client.chat.completions.create(
                model=model_for_team,
                messages=[{'role': 'system', 'content': prompt}],
                # temperature=0,  # Deterministic
                # max_tokens=1000
            ))
            ic(f"Response: {completion.choices[0].message.content}")
            response = completion.choices[0].message.content
            
            # Extract JSON from markdown code blocks if present
            json_content = extract_json_from_markdown(response)
            action_plan = json.loads(json_content)
            
            if isinstance(action_plan, dict) and 'actions' in action_plan:
                ic(f"Action plan: {action_plan}")
                return action_plan, prompt, response
            else:
                ic(f"Action plan: {action_plan}")
                ic("Action plan is not a dict or does not have an 'actions' key")
                await asyncio.sleep(4)
                raise json.JSONDecodeError("Invalid JSON structure", "", 0)
        except (json.JSONDecodeError, openai.OpenAIError, Exception) as e:
            error_msg = f"Attempt {attempt + 1} failed. Error: {str(e)}. "
            ic(f"Error: {error_msg}")
            await asyncio.sleep(4)
            if response:
                error_msg += f"Previous response: {response[:200]}..."  # Truncate for brevity
                ic(f"Error message: {error_msg}")
                await asyncio.sleep(4)
            prompt += f"\n\n{error_msg}\nPlease correct and output ONLY valid JSON as specified."
            ic(f"Prompt: {prompt}")
    ic(f"Completion raw: {completion}")
    ic("Failed to get valid response from LLM. Using default empty actions.")
    await asyncio.sleep(4)
    
    action_plan = {"actions": []}
    return action_plan, prompt, response

def get_unique_game_id():
    """
    Generates a unique game ID based on the current timestamp.
    Returns: str, e.g., '20240607_153012'
    """
    return datetime.now().strftime('%Y%m%d_%H%M%S')


def save_game_move(game_id, game_log):
    """
    Saves the current game log (list of moves) to a uniquely identified file in the 'games/' directory.
    Each move should be a dict with at least: team, visible_state, actions.
    Args:
        game_id (str): Unique identifier for the game (timestamp-based).
        game_log (list): List of move dicts.
    """
    os.makedirs('games', exist_ok=True)
    file_path = os.path.join('games', f'game_{game_id}.json')
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(game_log, f, ensure_ascii=False, indent=2)