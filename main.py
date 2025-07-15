import pygame
import sys
import asyncio
import json
import time
from dataclasses import dataclass
from typing import List, Dict, Optional
from game import Game
from llm_controller import get_action_plan
from visualization import GameVisualizer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from rich.align import Align
from rich.columns import Columns
from rich import print as rprint

console = Console()

@dataclass
class GameResult:
    game_number: int
    winner: str
    turns_taken: int
    final_blue_units: int
    final_red_units: int
    final_blue_locations: int
    final_red_locations: int
    duration_seconds: float

class BatchGameRunner:
    def __init__(self):
        self.all_results: List[GameResult] = []
        self.current_batch_results: List[GameResult] = []
        
    async def run_single_game(self, game_number: int) -> GameResult:
        """Run a single game without visualization for speed"""
        start_time = time.time()
        game = Game()
        
        winner = None
        turn = 0
        
        for turn in range(1, 121):  # Max 120 turns
            game.turn = turn
            
            active_team = 'Blue' if turn % 2 == 1 else 'Red'
            
            # Get state and actions from LLM
            state = game.get_visible_state(active_team)
            actions, _, _ = await get_action_plan(active_team, state)
            
            # Apply action limit based on opponent units
            opponent_team = 'Red' if active_team == 'Blue' else 'Blue'
            num_opponent_units = len(game.teams[opponent_team].units)
            action_limit = max(1, num_opponent_units)
            
            if len(actions['actions']) > action_limit:
                actions['actions'] = actions['actions'][:action_limit]
            
            # Execute actions
            game.execute_actions(active_team, actions['actions'])
            
            # Check for victory
            winner = game.check_victory()
            if winner:
                break
        
        end_time = time.time()
        
        # Collect final stats
        blue_team = game.teams['Blue']
        red_team = game.teams['Red']
        
        return GameResult(
            game_number=game_number,
            winner=winner or "Draw",
            turns_taken=turn,
            final_blue_units=len(blue_team.units),
            final_red_units=len(red_team.units),
            final_blue_locations=len(blue_team.controlled_locations),
            final_red_locations=len(red_team.controlled_locations),
            duration_seconds=end_time - start_time
        )
    
    async def run_batch(self, batch_number: int) -> List[GameResult]:
        """Run a batch of 10 games"""
        console.print(f"\n[bold cyan]🎮 Running Batch {batch_number} (10 games)...[/bold cyan]")
        
        batch_results = []
        
        for i in range(1, 11):
            console.print(f"[yellow]Running game {i}/10...[/yellow]", end="")
            
            result = await self.run_single_game(len(self.all_results) + i)
            batch_results.append(result)
            
            # Quick status indicator
            if result.winner == "Blue":
                console.print(" [blue]Blue wins![/blue]")
            elif result.winner == "Red":
                console.print(" [red]Red wins![/red]")
            else:
                console.print(" [yellow]Draw![/yellow]")
        
        self.current_batch_results = batch_results
        self.all_results.extend(batch_results)
        
        return batch_results
    
    def display_results(self):
        """Display results with option to continue or exit"""
        console.clear()
        
        # Display current batch results
        console.print(Panel(
            f"[bold green]🏆 Latest Batch Results (Games {len(self.all_results)-9}-{len(self.all_results)})[/bold green]",
            style="bright_green"
        ))
        
        # Current batch table
        batch_table = Table(show_header=True, header_style="bold magenta")
        batch_table.add_column("Game", style="cyan", width=6)
        batch_table.add_column("Winner", style="white", width=8)
        batch_table.add_column("Turns", style="yellow", width=6)
        batch_table.add_column("Blue Units", style="blue", width=10)
        batch_table.add_column("Red Units", style="red", width=10)
        batch_table.add_column("Blue Locations", style="blue", width=12)
        batch_table.add_column("Red Locations", style="red", width=12)
        batch_table.add_column("Duration", style="green", width=10)
        
        for result in self.current_batch_results:
            winner_style = "blue" if result.winner == "Blue" else "red" if result.winner == "Red" else "yellow"
            batch_table.add_row(
                str(result.game_number),
                f"[{winner_style}]{result.winner}[/{winner_style}]",
                str(result.turns_taken),
                str(result.final_blue_units),
                str(result.final_red_units),
                str(result.final_blue_locations),
                str(result.final_red_locations),
                f"{result.duration_seconds:.1f}s"
            )
        
        console.print(batch_table)
        
        # Display cumulative statistics
        if len(self.all_results) > 0:
            console.print(f"\n[bold cyan]📊 Cumulative Statistics (Total: {len(self.all_results)} games)[/bold cyan]")
            
            blue_wins = sum(1 for r in self.all_results if r.winner == "Blue")
            red_wins = sum(1 for r in self.all_results if r.winner == "Red")
            draws = sum(1 for r in self.all_results if r.winner == "Draw")
            
            avg_turns = sum(r.turns_taken for r in self.all_results) / len(self.all_results)
            avg_duration = sum(r.duration_seconds for r in self.all_results) / len(self.all_results)
            
            total_blue_wins_pct = (blue_wins / len(self.all_results)) * 100
            total_red_wins_pct = (red_wins / len(self.all_results)) * 100
            total_draws_pct = (draws / len(self.all_results)) * 100
            
            stats_table = Table(show_header=True, header_style="bold magenta")
            stats_table.add_column("Metric", style="cyan", width=20)
            stats_table.add_column("Value", style="white", width=15)
            stats_table.add_column("Percentage", style="yellow", width=15)
            
            stats_table.add_row("Blue Wins", str(blue_wins), f"{total_blue_wins_pct:.1f}%")
            stats_table.add_row("Red Wins", str(red_wins), f"{total_red_wins_pct:.1f}%")
            stats_table.add_row("Draws", str(draws), f"{total_draws_pct:.1f}%")
            stats_table.add_row("Average Turns", f"{avg_turns:.1f}", "")
            stats_table.add_row("Average Duration", f"{avg_duration:.1f}s", "")
            
            console.print(stats_table)
        
        # Instructions
        console.print(f"\n[bold yellow]{'='*60}[/bold yellow]")
        console.print("[bold green]Controls:[/bold green]")
        console.print("  [bold white]SPACE or ENTER[/bold white] - Run another batch of 10 games")
        console.print("  [bold white]ESC[/bold white] - Exit gracefully")
        console.print(f"[bold yellow]{'='*60}[/bold yellow]")
        
    def wait_for_input(self) -> str:
        """Wait for user input (space/enter to continue, esc to exit)"""
        pygame.init()
        screen = pygame.display.set_mode((1, 1))  # Minimal window for input
        pygame.display.set_caption("Input Handler")
        
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "exit"
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return "exit"
                    elif event.key in [pygame.K_SPACE, pygame.K_RETURN]:
                        return "continue"
            
            time.sleep(0.1)  # Small delay to prevent busy waiting

async def main():
    runner = BatchGameRunner()
    batch_number = 1
    
    console.print(Panel(
        "[bold cyan]🎮 Harford County Strategy Game - Batch Runner 🎮[/bold cyan]",
        style="bright_blue"
    ))
    
    while True:
        # Run batch of 10 games
        await runner.run_batch(batch_number)
        
        # Display results
        runner.display_results()
        
        # Wait for user input
        user_choice = runner.wait_for_input()
        
        if user_choice == "exit":
            console.print("\n[bold green]Thanks for playing! Goodbye! 👋[/bold green]")
            break
        elif user_choice == "continue":
            batch_number += 1
            continue
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    asyncio.run(main())