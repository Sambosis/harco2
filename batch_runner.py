import asyncio
import time
import sys
from dataclasses import dataclass
from typing import List
from game import Game
from llm_controller import get_action_plan

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
        print(f"\n🎮 Running Batch {batch_number} (10 games)...")
        
        batch_results = []
        
        for i in range(1, 11):
            print(f"Running game {i}/10...", end="")
            
            result = await self.run_single_game(len(self.all_results) + i)
            batch_results.append(result)
            
            # Quick status indicator
            if result.winner == "Blue":
                print(" Blue wins!")
            elif result.winner == "Red":
                print(" Red wins!")
            else:
                print(" Draw!")
        
        self.current_batch_results = batch_results
        self.all_results.extend(batch_results)
        
        return batch_results
    
    def display_results(self):
        """Display results with option to continue or exit"""
        print("\n" + "="*80)
        print(f"🏆 All Game Results (Total: {len(self.all_results)} games)")
        print("="*80)
        
        # Header
        print(f"{'Game':<6} {'Winner':<8} {'Turns':<6} {'Blue Units':<10} {'Red Units':<10} {'Blue Locs':<10} {'Red Locs':<10} {'Duration':<10}")
        print("-" * 80)
        
        # All game results
        for result in self.all_results:
            # Highlight most recent batch
            if result in self.current_batch_results:
                marker = "* "
            else:
                marker = "  "
            
            print(f"{marker}{result.game_number:<4} {result.winner:<8} {result.turns_taken:<6} "
                  f"{result.final_blue_units:<10} {result.final_red_units:<10} "
                  f"{result.final_blue_locations:<10} {result.final_red_locations:<10} "
                  f"{result.duration_seconds:.1f}s")
        
        # Cumulative statistics
        if len(self.all_results) > 0:
            print(f"\n📊 Cumulative Statistics")
            print("-" * 50)
            
            blue_wins = sum(1 for r in self.all_results if r.winner == "Blue")
            red_wins = sum(1 for r in self.all_results if r.winner == "Red")
            draws = sum(1 for r in self.all_results if r.winner == "Draw")
            
            avg_turns = sum(r.turns_taken for r in self.all_results) / len(self.all_results)
            avg_duration = sum(r.duration_seconds for r in self.all_results) / len(self.all_results)
            
            total_blue_wins_pct = (blue_wins / len(self.all_results)) * 100
            total_red_wins_pct = (red_wins / len(self.all_results)) * 100
            total_draws_pct = (draws / len(self.all_results)) * 100
            
            print(f"Blue Wins: {blue_wins} ({total_blue_wins_pct:.1f}%)")
            print(f"Red Wins: {red_wins} ({total_red_wins_pct:.1f}%)")
            print(f"Draws: {draws} ({total_draws_pct:.1f}%)")
            print(f"Average Turns: {avg_turns:.1f}")
            print(f"Average Duration: {avg_duration:.1f}s")
            
            # Show latest batch summary
            if len(self.current_batch_results) > 0:
                batch_blue_wins = sum(1 for r in self.current_batch_results if r.winner == "Blue")
                batch_red_wins = sum(1 for r in self.current_batch_results if r.winner == "Red")
                batch_draws = sum(1 for r in self.current_batch_results if r.winner == "Draw")
                
                print(f"\nLatest Batch Results (marked with *):")
                print(f"  Blue: {batch_blue_wins}, Red: {batch_red_wins}, Draws: {batch_draws}")
        
        print("\n" + "="*80)
        print("Controls:")
        print("  SPACE or ENTER - Run another batch of 10 games")
        print("  ESC or 'q' - Exit gracefully")
        print("="*80)
    
    def wait_for_input(self) -> str:
        """Wait for user input (space/enter to continue, esc/q to exit)"""
        try:
            import pygame
            pygame.init()
            screen = pygame.display.set_mode((200, 100))
            pygame.display.set_caption("Batch Runner - Press SPACE to continue, ESC to exit")
            
            while True:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        return "exit"
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            return "exit"
                        elif event.key in [pygame.K_SPACE, pygame.K_RETURN]:
                            return "continue"
                
                time.sleep(0.1)
        except ImportError:
            # Fallback to simple input if pygame is not available
            print("Enter 'c' to continue or 'q' to quit: ", end="")
            user_input = input().strip().lower()
            if user_input in ['q', 'quit', 'exit']:
                return "exit"
            else:
                return "continue"

async def main():
    runner = BatchGameRunner()
    batch_number = 1
    
    print("🎮 Harford County Strategy Game - Batch Runner 🎮")
    print("This will run games in batches of 10 and display results.")
    
    while True:
        # Run batch of 10 games
        await runner.run_batch(batch_number)
        
        # Display results
        runner.display_results()
        
        # Wait for user input
        user_choice = runner.wait_for_input()
        
        if user_choice == "exit":
            print("\nThanks for playing! Goodbye! 👋")
            break
        elif user_choice == "continue":
            batch_number += 1
            continue
    
    try:
        import pygame
        pygame.quit()
    except ImportError:
        pass
    
    sys.exit()

if __name__ == "__main__":
    asyncio.run(main())