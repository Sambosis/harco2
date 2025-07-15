import pygame
import sys
import asyncio
import json
from game import Game
from llm_controller import get_action_plan
from visualization import GameVisualizer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import print as rprint

console = Console()

async def main():
    # Initialize the enhanced visualizer
    visualizer = GameVisualizer(800, 600)
    clock = pygame.time.Clock()
    game = Game()
    
    console.print(Panel("🎮 [bold cyan]Harford County Strategy Game[/bold cyan] 🎮", style="bright_blue"))
    console.print("[green]Initial game state loaded successfully![/green]")
    
    # Initial draw
    visualizer.draw_game_state(game)
    await asyncio.sleep(1)

    winner = None
    for turn in range(1, 121):
        game.turn = turn  # Update the game's turn counter
        
        # Handle pygame events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        active_team = 'Blue' if turn % 2 == 1 else 'Red'
        team_color = "blue" if active_team == 'Blue' else "red"
        
        console.print(f"\n[bold {team_color}]{'='*50}[/bold {team_color}]")
        console.print(f"[bold {team_color}]Turn {turn}: {active_team}'s turn[/bold {team_color}]")
        console.print(f"[bold {team_color}]{'='*50}[/bold {team_color}]")

        state = game.get_visible_state(active_team)
        actions, prompt, response = await get_action_plan(active_team, state)

        console.print("\n[dim]Prompt sent to LLM:[/dim]")
        console.print("\n[dim]LLM Response received[/dim]")
        
        # New Twist: Limit actions based on the number of the OPPONENT'S units
        opponent_team = 'Red' if active_team == 'Blue' else 'Blue'
        num_opponent_units = len(game.teams[opponent_team].units)
        action_limit = max(1, num_opponent_units)  # Ensure at least 1 action is possible

        if len(actions['actions']) > action_limit:
            console.print(f"[bold yellow]Limiting actions from {len(actions['actions'])} to {action_limit} (based on opponent's {num_opponent_units} units)[/bold yellow]")
            actions['actions'] = actions['actions'][:action_limit]
            
        console.print("\n[yellow]📋 Parsed actions:[/yellow]")

        results = game.execute_actions(active_team, actions['actions'])
        
        # Process results for visual effects
        visualizer.process_action_results(results, active_team)
        
        # Create a table for action results
        results_table = Table(title=f"[bold green]⚔️  {active_team} Team Action Results[/bold green]", show_header=True, header_style="bold magenta")
        results_table.add_column("Action Type", style="cyan", width=12)
        results_table.add_column("Description", style="white", width=50)
        results_table.add_column("Status", style="green", width=15)
        
        for res in results:
            if "Moving" in res and "from" in res and "to" in res:
                # Extract unit and locations from move message
                parts = res.split()
                unit = parts[1] if len(parts) > 1 else "Unknown"
                action_type = "🚶 Move"
                description = res.replace("Moving ", "")
                status = "[yellow]In Progress[/yellow]"
                
            elif "Successfully moved" in res:
                action_type = "✅ Move"
                description = res.replace("Successfully moved to ", "Arrived at ")
                status = "[green]Success[/green]"
                
            elif "Combat at" in res:
                action_type = "⚔️  Combat"
                description = res
                status = "[red]Fighting[/red]"
                
            elif "eliminated" in res:
                action_type = "💀 Casualty"
                description = res
                status = "[bright_red]KIA[/bright_red]"
                
            elif "Combat result" in res:
                action_type = "📊 Result"
                description = res.replace("Combat result: ", "")
                status = "[yellow]Complete[/yellow]"
                
            elif "Reinforced" in res:
                action_type = "🛡️  Reinforce"
                description = res
                status = "[blue]Success[/blue]"
                
            elif "Gained" in res and "resources" in res:
                action_type = "💰 Resources"
                description = res
                status = "[yellow]Collected[/yellow]"
                
            elif "Failed" in res:
                action_type = "❌ Failed"
                description = res
                status = "[red]Error[/red]"
                
            else:
                action_type = "ℹ️  Info"
                description = res
                status = "[white]Info[/white]"
            
            results_table.add_row(action_type, description, status)
        
        console.print(results_table)

        console.print("\n[dim]Updated game state processed[/dim]")

        # Draw the game state with animations
        visualizer.draw_game_state(game)
        
        # Allow time for animations to play
        animation_time = 2.0  # 2 seconds for animations
        start_time = pygame.time.get_ticks() / 1000
        while pygame.time.get_ticks() / 1000 - start_time < animation_time:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
            
            visualizer.draw_game_state(game)
            clock.tick(60)  # 60 FPS for smooth animations
            await asyncio.sleep(0)  # Allow other async tasks to run

        winner = game.check_victory()
        if winner:
            winner_color = "blue" if winner == 'Blue' else "red"
            console.print(f"\n[bold {winner_color}]🏆 {winner} wins! 🏆[/bold {winner_color}]")
            visualizer.add_event(f"🏆 {winner} WINS! 🏆", "success")
            break

    if not winner:
        console.print("\n[bold yellow]⚖️  Draw! ⚖️[/bold yellow]")
        visualizer.add_event("⚖️ Game ended in a draw!", "info")

    # Keep the window open until quit
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        
        visualizer.draw_game_state(game)
        clock.tick(10)  # Low tick to not busy-wait
        await asyncio.sleep(0)

if __name__ == "__main__":
    asyncio.run(main())