# Harford County Strategy Game

A turn-based strategy game set in Harford County, Maryland, where two AI-controlled teams compete for territorial control using infantry units.

## Game Overview

This is a tactical strategy game where two teams (Blue and Red) battle for control of six locations in Harford County. Each team is controlled by an AI powered by OpenAI's language models, making strategic decisions based on the current game state.

## Objective

**Win by either:**
- Controlling at least 5 out of 6 locations
- Eliminating all enemy units

**Game Length:** Maximum of 120 turns (if no winner is determined)

## Map Layout

The game takes place across six locations in Harford County:

- **Bel Air** (Blue starting location)
- **Aberdeen Proving Ground** (Red starting location)
- **Havre de Grace**
- **Edgewood**
- **Joppatowne**
- **Fallston**

### Location Connections

Each location connects to specific adjacent locations:

- **Bel Air** ↔ Fallston, Joppatowne, Edgewood, Aberdeen Proving Ground
- **Aberdeen Proving Ground** ↔ Edgewood, Havre de Grace, Bel Air
- **Havre de Grace** ↔ Aberdeen Proving Ground
- **Edgewood** ↔ Aberdeen Proving Ground, Joppatowne, Bel Air
- **Joppatowne** ↔ Edgewood, Bel Air
- **Fallston** ↔ Bel Air

## Unit System

### Initial Setup
- Each team starts with **5 infantry units**
- Blue team starts at **Bel Air**
- Red team starts at **Aberdeen Proving Ground**

### Unit Properties
- **Health:** 3 HP (units are eliminated when health reaches 0)
- **Strength:** 1 (used in combat calculations)
- **Type:** Infantry (all units are currently infantry)
- **Movement:** Units can move multiple times per turn and can chain movements

## Combat System

### Combat Resolution
When units move to a location with enemy units, combat is initiated:

1. **Strength Calculation:** Total strength = sum of all unit strengths
2. **Dice Roll:** Each side rolls 1d6 + total strength
3. **Damage:** Higher roll wins, losing side takes 1 damage to a random unit
4. **Elimination:** Units with 0 health are removed from the game
5. **Victory:** Combat continues until one side has no units remaining

### Movement Rules
- Units can only move to **adjacent locations**
- Units can **move multiple times per turn** (chain movements)
- Moving to an **empty/neutral location** = automatic capture
- Moving to an **enemy location** = initiates combat
- **Winner takes control** of the location

## Resource System

### Resource Generation
- Each controlled location provides **1 resource per turn**
- Resources are collected at the end of each turn
- Resources carry over between turns

### Resource Usage
- **Reinforcement:** Spend 3 resources to add a new infantry unit at any controlled location

## Turn Structure

### Turn Order
1. **Blue team** moves on odd turns (1, 3, 5, ...)
2. **Red team** moves on even turns (2, 4, 6, ...)

### Action Limits
- **Dynamic Action Limit:** Each team can perform a maximum number of actions per turn equal to the number of opponent units (minimum 1)
- This creates a strategic balance where eliminating enemy units reduces their action capacity

### Turn Actions
Each turn, teams can perform multiple actions:

#### 1. Move Actions
```json
{"type": "move", "unit_id": "Blue-1", "to": "Edgewood"}
```
- Move a specific unit to an adjacent location
- Same unit can move multiple times in one turn
- Moving to enemy locations triggers combat

#### 2. Reinforce Actions
```json
{"type": "reinforce", "location": "Bel Air"}
```
- Costs 3 resources
- Adds a new infantry unit to a controlled location
- Unit spawns with full health (3 HP)

### Action Processing Order
1. **Reinforcements** are processed first
2. **Movements** are processed by destination location
3. **Resource collection** happens at turn end

## Visibility System

Teams have **limited visibility**:
- **Full visibility:** Own units, controlled locations, resources
- **Partial visibility:** Enemy units in locations adjacent to your units
- **No visibility:** Enemy units in distant locations

## Victory Conditions

### Immediate Victory
- **Territorial Control:** Control 5+ out of 6 locations
- **Total Elimination:** Eliminate all enemy units

### Draw Conditions
- **Turn Limit:** Game ends in draw after 120 turns with no winner
- **Stalemate:** No meaningful progress possible

## Game Execution

### Batch Mode
The game runs in continuous batches of 10 games each:
- After each batch, results are displayed
- Players can choose to run another batch or exit
- Statistics are tracked across all games

### AI Models
- **Blue Team:** GPT-4.1
- **Red Team:** o4-mini (OpenAI's optimized model)

## How to Run the Game

### Prerequisites
```bash
# Install dependencies
uv sync

# Set up OpenAI API key
echo "OPENAI_API_KEY=your_api_key_here" > .env
```

### Running the Game
```bash
uv run main.py
```

### Game Interface
- **Visual Display:** Pygame window showing the map, units, and current state
- **Console Output:** Detailed turn-by-turn actions and results
- **Real-time Updates:** Game state updates after each action with animations
- **Batch Results:** Summary statistics after each 10-game batch

### Controls
- **Close Window:** Click the X button or press Ctrl+C in terminal
- **After Batch:** Press SPACE/ENTER to continue with next batch, ESC to exit
- **Game Speed:** Includes 2-second animation delays between turns

## Technical Details

### AI Decision Making
- Each team uses different OpenAI models to make strategic decisions
- AI receives current game state and generates action plans
- Actions are validated and executed by the game engine
- Action limits prevent overwhelming strategies

### File Structure
- `main.py` - Game loop, batch management, and visualization control
- `game.py` - Core game logic and state management
- `llm_controller.py` - AI decision making and OpenAI integration
- `visualization.py` - Pygame-based visual interface with animations
- `batch_runner.py` - Batch game execution and statistics
- `pyproject.toml` - Dependencies and project configuration

### Dependencies
- `openai` - AI decision making
- `pygame` - Game visualization
- `python-dotenv` - Environment configuration
- `icecream` - Debug logging
- `rich` - Console formatting and tables

## Game Features

### Strategic Elements
- **Territorial Control:** Balance expansion vs. defense
- **Resource Management:** Invest in reinforcements vs. save for future
- **Unit Positioning:** Multi-turn movement planning
- **Combat Tactics:** Concentrate forces vs. spread control
- **Action Economy:** Limited actions based on opponent strength

### AI Capabilities
- **Adaptive Strategy:** AI learns from game state
- **Multi-turn Planning:** Can execute complex movement chains
- **Resource Optimization:** Balances expansion and reinforcement
- **Tactical Combat:** Considers unit strengths in battle planning
- **Dynamic Constraints:** Adapts to changing action limits

### Performance Tracking
- **Batch Statistics:** Win rates, average game length
- **Model Comparison:** Performance metrics for different AI models
- **Game Logging:** Detailed move-by-move analysis
- **Real-time Visualization:** Animated combat and movement

## Future Enhancements

Potential improvements could include:
- Different unit types with unique abilities
- Terrain modifiers affecting combat
- Special abilities or cards
- Extended campaign mode
- Human vs. AI gameplay option
- Adjustable difficulty levels
- Tournament mode with elimination brackets
