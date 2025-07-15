import pygame
import sys
import asyncio
import json
import time
from dataclasses import dataclass
from typing import List
from game import Game
from llm_controller import get_action_plan, get_unique_game_id, save_game_move
from visualization import GameVisualizer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
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

class BatchGameRunner:
    def __init__(self):
        self.all_results: List[GameResult] = []
        self.current_batch_results: List[GameResult] = []
        
    async def run_single_game(self, game_number: int, visualizer: GameVisualizer, clock: pygame.time.Clock) -> GameResult:
        """Run a single game with full visualization"""
        game = Game()
        game_id = get_unique_game_id()
        game_log = []
        
        console.print(f"\n[bold cyan]Game {game_number} (ID: {game_id})[/bold cyan]")
        console.print(Panel("🎮 [bold cyan]Harford County Strategy Game[/bold cyan] 🎮", style="bright_blue"))
        console.print("[green]Initial game state loaded successfully![/green]")
        
        # Initial draw
        visualizer.draw_game_state(game)
        await asyncio.sleep(1)

        winner = None
        for turn in range(1, 121):
            game.turn = turn
            
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

            # Log the move
            move_data = {
                "turn": turn,
                "team": active_team,
                "visible_state": state,
                "actions": actions.get('actions', []),
                "raw_response": response
            }
            game_log.append(move_data)
            save_game_move(game_id, game_log)

            console.print("\n[dim]Prompt sent to LLM:[/dim]")
            console.print("\n[dim]LLM Response received[/dim]")
            
            # Apply action limit based on opponent units
            opponent_team = 'Red' if active_team == 'Blue' else 'Blue'
            num_opponent_units = len(game.teams[opponent_team].units)
            action_limit = max(1, num_opponent_units)

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
            winner = "Draw"

        # Collect final stats
        blue_team = game.teams['Blue']
        red_team = game.teams['Red']
        
        return GameResult(
            game_number=game_number,
            winner=winner,
            turns_taken=turn,
            final_blue_units=len(blue_team.units),
            final_red_units=len(red_team.units),
            final_blue_locations=len(blue_team.controlled_locations),
            final_red_locations=len(red_team.controlled_locations)
        )

    async def run_batch(self, batch_number: int, visualizer: GameVisualizer, clock: pygame.time.Clock):
        """Run a batch of 10 games"""
        console.print(f"\n[bold cyan]🎮 Starting Batch {batch_number} (10 games)...[/bold cyan]")
        
        batch_results = []
        
        for i in range(1, 11):
            game_number = len(self.all_results) + i
            result = await self.run_single_game(game_number, visualizer, clock)
            batch_results.append(result)
            
            # Brief pause between games
            await asyncio.sleep(2)
        
        self.current_batch_results = batch_results
        self.all_results.extend(batch_results)

    def show_results_screen(self, visualizer: GameVisualizer, clock: pygame.time.Clock):
        """Show results screen in Pygame and wait for user input"""
        waiting_for_input = True
        
        while waiting_for_input:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return "exit"
                    elif event.key in [pygame.K_SPACE, pygame.K_RETURN]:
                        return "continue"
            
            # Draw results screen
            screen = visualizer.screen
            screen.fill((30, 30, 30))  # Dark background
            
            # Title
            title_font = pygame.font.Font(None, 48)
            title_text = title_font.render("Game Results", True, (255, 255, 255))
            title_rect = title_text.get_rect(center=(screen.get_width() // 2, 50))
            screen.blit(title_text, title_rect)
            
            # Calculate statistics
            blue_wins = sum(1 for r in self.all_results if r.winner == "Blue")
            red_wins = sum(1 for r in self.all_results if r.winner == "Red")
            draws = sum(1 for r in self.all_results if r.winner == "Draw")
            total_games = len(self.all_results)
            
            # Latest batch stats
            batch_blue_wins = sum(1 for r in self.current_batch_results if r.winner == "Blue")
            batch_red_wins = sum(1 for r in self.current_batch_results if r.winner == "Red")
            batch_draws = sum(1 for r in self.current_batch_results if r.winner == "Draw")
            
            # Display stats
            font = pygame.font.Font(None, 36)
            y_pos = 120
            
            # Latest batch results
            latest_text = font.render(f"Latest Batch Results:", True, (255, 255, 0))
            screen.blit(latest_text, (50, y_pos))
            y_pos += 40
            
            batch_text = font.render(f"Blue: {batch_blue_wins}  Red: {batch_red_wins}  Draws: {batch_draws}", True, (255, 255, 255))
            screen.blit(batch_text, (50, y_pos))
            y_pos += 60
            
            # Cumulative results
            cumulative_text = font.render(f"Cumulative Results ({total_games} games):", True, (255, 255, 0))
            screen.blit(cumulative_text, (50, y_pos))
            y_pos += 40
            
            total_text = font.render(f"Blue: {blue_wins} ({blue_wins/total_games*100:.1f}%)", True, (100, 150, 255))
            screen.blit(total_text, (50, y_pos))
            y_pos += 35
            
            total_text = font.render(f"Red: {red_wins} ({red_wins/total_games*100:.1f}%)", True, (255, 100, 100))
            screen.blit(total_text, (50, y_pos))
            y_pos += 35
            
            total_text = font.render(f"Draws: {draws} ({draws/total_games*100:.1f}%)", True, (200, 200, 200))
            screen.blit(total_text, (50, y_pos))
            y_pos += 80
            
            # Instructions
            instruction_font = pygame.font.Font(None, 32)
            instruction_text = instruction_font.render("SPACE/ENTER: Run another 10 games", True, (0, 255, 0))
            screen.blit(instruction_text, (50, y_pos))
            y_pos += 35
            
            instruction_text = instruction_font.render("ESC: Exit", True, (255, 0, 0))
            screen.blit(instruction_text, (50, y_pos))
            
            pygame.display.flip()
            clock.tick(60)

async def main():
    # Initialize the enhanced visualizer
    visualizer = GameVisualizer(800, 600)
    clock = pygame.time.Clock()
    runner = BatchGameRunner()
    batch_number = 1
    
    while True:
        # Run batch of 10 games
        await runner.run_batch(batch_number, visualizer, clock)
        
        # Show results screen and wait for input
        user_choice = runner.show_results_screen(visualizer, clock)
        
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