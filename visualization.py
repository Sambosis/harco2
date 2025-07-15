import pygame
import time
import math
from collections import deque

# Fixed positions for locations
LOCATIONS = {
    'Bel Air': (300, 200),
    'Aberdeen Proving Ground': (500, 300),
    'Havre de Grace': (600, 200),
    'Edgewood': (400, 300),
    'Joppatowne': (200, 300),
    'Fallston': (200, 100)
}

# Hardcoded connections based on game map
CONNECTIONS = {
    'Bel Air': ['Fallston', 'Joppatowne', 'Edgewood', 'Aberdeen Proving Ground'],
    'Aberdeen Proving Ground': ['Edgewood', 'Havre de Grace', 'Bel Air'],
    'Havre de Grace': ['Aberdeen Proving Ground'],
    'Edgewood': ['Aberdeen Proving Ground', 'Joppatowne', 'Bel Air'],
    'Joppatowne': ['Edgewood', 'Bel Air'],
    'Fallston': ['Bel Air']
}

# Animation and event system
class GameVisualizer:
    def __init__(self, width=800, height=600):
        pygame.init()
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Harford County Strategy Game")
        self.clock = pygame.time.Clock()
        
        # Fonts
        self.font = pygame.font.Font(None, 20)
        self.unit_font = pygame.font.Font(None, 18)
        self.event_font = pygame.font.Font(None, 24)
        
        # Event system
        self.events = deque(maxlen=10)  # Store last 10 events
        self.event_display_time = 3000  # 3 seconds
        
        # Animation system
        self.animations = []
        self.combat_effects = []
        
    def add_event(self, event_text, event_type="info"):
        """Add an event to the display queue"""
        colors = {
            "move": (0, 150, 255),
            "combat": (255, 100, 100),
            "success": (0, 200, 0),
            "info": (100, 100, 100)
        }
        self.events.append({
            'text': event_text,
            'color': colors.get(event_type, colors['info']),
            'time': pygame.time.get_ticks()
        })
    
    def add_move_animation(self, from_loc, to_loc, unit_id, team):
        """Add a move animation"""
        if from_loc in LOCATIONS and to_loc in LOCATIONS:
            color = (0, 0, 255) if team == 'Blue' else (255, 0, 0)
            self.animations.append({
                'type': 'move',
                'from': LOCATIONS[from_loc],
                'to': LOCATIONS[to_loc],
                'unit_id': unit_id,
                'color': color,
                'start_time': pygame.time.get_ticks(),
                'duration': 1000  # 1 second
            })
    
    def add_combat_effect(self, location):
        """Add a combat effect at a location"""
        if location in LOCATIONS:
            self.combat_effects.append({
                'pos': LOCATIONS[location],
                'start_time': pygame.time.get_ticks(),
                'duration': 2000  # 2 seconds
            })
    
    def draw_animations(self):
        """Draw all active animations"""
        current_time = pygame.time.get_ticks()
        
        # Draw move animations
        for anim in self.animations[:]:
            if anim['type'] == 'move':
                elapsed = current_time - anim['start_time']
                if elapsed >= anim['duration']:
                    self.animations.remove(anim)
                    continue
                
                # Calculate position
                progress = elapsed / anim['duration']
                start_x, start_y = anim['from']
                end_x, end_y = anim['to']
                
                current_x = start_x + (end_x - start_x) * progress
                current_y = start_y + (end_y - start_y) * progress
                
                # Draw moving unit
                pygame.draw.circle(self.screen, anim['color'], (int(current_x), int(current_y)), 8)
                pygame.draw.circle(self.screen, (255, 255, 255), (int(current_x), int(current_y)), 8, 2)
                
                # Draw trail
                for i in range(5):
                    trail_progress = max(0, progress - i * 0.1)
                    if trail_progress > 0:
                        trail_x = start_x + (end_x - start_x) * trail_progress
                        trail_y = start_y + (end_y - start_y) * trail_progress
                        alpha = max(0, 255 - i * 50)
                        color = (*anim['color'], alpha)
                        pygame.draw.circle(self.screen, anim['color'], (int(trail_x), int(trail_y)), max(1, 8 - i))
        
        # Draw combat effects
        for effect in self.combat_effects[:]:
            elapsed = current_time - effect['start_time']
            if elapsed >= effect['duration']:
                self.combat_effects.remove(effect)
                continue
            
            # Pulsing red circle for combat
            progress = elapsed / effect['duration']
            radius = 40 + math.sin(progress * math.pi * 8) * 10
            alpha = max(0, 255 - int(progress * 255))
            
            # Create surface for alpha blending
            combat_surface = pygame.Surface((100, 100), pygame.SRCALPHA)
            pygame.draw.circle(combat_surface, (255, 0, 0, alpha), (50, 50), int(radius))
            self.screen.blit(combat_surface, (effect['pos'][0] - 50, effect['pos'][1] - 50))
    
    def draw_events(self):
        """Draw the event log"""
        current_time = pygame.time.get_ticks()
        
        # Calculate starting position from bottom
        screen_height = self.screen.get_height()
        event_height = 30
        max_events = 5
        total_height = max_events * event_height + 20  # 20px padding
        start_y = screen_height - total_height
        
        # Draw event background
        if self.events:
            visible_count = min(len([e for e in self.events if current_time - e['time'] <= self.event_display_time]), max_events)
            if visible_count > 0:
                bg_height = visible_count * event_height + 20
                event_bg = pygame.Surface((self.screen.get_width(), bg_height), pygame.SRCALPHA)
                event_bg.fill((0, 0, 0, 180))  # Slightly more opaque for better contrast
                self.screen.blit(event_bg, (0, screen_height - bg_height))
        
        # Draw events from bottom up
        y_offset = start_y + 10
        visible_events = 0
        
        for event in reversed(self.events):
            if current_time - event['time'] > self.event_display_time:
                continue
            
            if visible_events >= max_events:  # Show max 5 events
                break
            
            # Fade out over time
            age = current_time - event['time']
            alpha = max(0, 255 - int((age / self.event_display_time) * 255))
            
            # Choose icon/prefix based on event type
            prefix = ""
            if event['color'] == (0, 150, 255):  # move
                prefix = "🚶 "
            elif event['color'] == (255, 100, 100):  # combat
                prefix = "⚔️  "
            elif event['color'] == (0, 200, 0):  # success
                prefix = "✅ "
            else:
                prefix = "ℹ️  "
            
            # Render white text for max contrast
            text_surface = self.event_font.render(prefix + event['text'], True, (255, 255, 255))
            text_surface.set_alpha(alpha)
            
            # Optional: Draw a subtle shadow for even better readability
            shadow = self.event_font.render(prefix + event['text'], True, (0, 0, 0))
            shadow.set_alpha(int(alpha * 0.7))
            self.screen.blit(shadow, (12, y_offset + 2))
            
            self.screen.blit(text_surface, (10, y_offset))
            y_offset += event_height
            visible_events += 1
    
    def draw_game_state(self, game):
        """Draw the current game state with enhanced visuals"""
        state = game.get_full_state()

        # Clear the screen
        self.screen.fill((240, 240, 240))

        # Draw connections (lines between locations)
        drawn = set()
        for loc, data in state['locations'].items():
            pos1 = LOCATIONS[loc]
            for conn in data['connections']:
                if conn in LOCATIONS:
                    pos2 = LOCATIONS[conn]
                    key = tuple(sorted((loc, conn)))
                    if key not in drawn:
                        pygame.draw.line(self.screen, (150, 150, 150), pos1, pos2, 3)
                        drawn.add(key)

        # Draw locations (circles with control colors, names, and unit counts)
        for loc, data in state['locations'].items():
            pos = LOCATIONS[loc]
            control = data['control']
            
            # Base circle color
            if control is None:
                color = (200, 200, 200)
            elif control == 'Blue':
                color = (100, 150, 255)
            else:  # Red
                color = (255, 100, 100)
            
            # Draw main circle
            pygame.draw.circle(self.screen, color, pos, 35)
            pygame.draw.circle(self.screen, (0, 0, 0), pos, 35, 3)
            
            # Draw inner circle for better visibility
            pygame.draw.circle(self.screen, (255, 255, 255), pos, 25, 2)

            # Location name (above the circle)
            name_text = self.font.render(loc, True, (0, 0, 0))
            text_rect = name_text.get_rect(center=(pos[0], pos[1] - 50))
            self.screen.blit(name_text, text_rect)

            # Unit counts (blue left, red right inside circle)
            blue_units = data['units'].get('Blue', 0)
            red_units = data['units'].get('Red', 0)
            
            if blue_units > 0:
                blue_text = self.unit_font.render(str(blue_units), True, (0, 0, 150))
                self.screen.blit(blue_text, (pos[0] - 25, pos[1] - 5))
            
            if red_units > 0:
                red_text = self.unit_font.render(str(red_units), True, (150, 0, 0))
                self.screen.blit(red_text, (pos[0] + 10, pos[1] - 5))

        # Draw turn number and team resources
        turn_text = self.font.render(f"Turn: {state['turn']}", True, (0, 0, 0))
        self.screen.blit(turn_text, (10, 10))

        blue_res = state['teams']['Blue']['resources']
        blue_model_name = state['teams']['Blue'].get('model', 'Blue')
        blue_text = self.font.render(f"{blue_model_name} Resources: {blue_res}", True, (0, 0, 255))
        self.screen.blit(blue_text, (10, 40))

        red_res = state['teams']['Red']['resources']
        red_model_name = state['teams']['Red'].get('model', 'Red')
        red_text = self.font.render(f"{red_model_name} Resources: {red_res}", True, (255, 0, 0))
        self.screen.blit(red_text, (10, 70))
        
        # Draw animations and effects
        self.draw_animations()
        self.draw_events()

        pygame.display.flip()
    
    def process_action_results(self, results, team):
        """Process action results and create appropriate visual effects"""
        for result in results:
            if "Moving" in result and "from" in result and "to" in result:
                # Extract move information
                parts = result.split()
                unit_id = parts[1] if len(parts) > 1 else "Unknown"
                from_loc = None
                to_loc = None
                
                # Parse "Moving Unit-1 from Location1 to Location2"
                try:
                    from_idx = parts.index("from")
                    to_idx = parts.index("to")
                    from_loc = " ".join(parts[from_idx + 1:to_idx])
                    to_loc = " ".join(parts[to_idx + 1:])
                except:
                    pass
                
                if from_loc and to_loc:
                    self.add_move_animation(from_loc, to_loc, unit_id, team)
                    self.add_event(f"{unit_id} moving to {to_loc}", "move")
            
            elif "Combat at" in result:
                # Extract combat location
                parts = result.split("Combat at ")
                if len(parts) > 1:
                    location = parts[1].split(":")[0]
                    self.add_combat_effect(location)
                    self.add_event(f"Combat at {location}!", "combat")
            
            elif "eliminated" in result:
                self.add_event(result, "combat")
            
            elif "Successfully moved" in result:
                self.add_event(result, "success")
            
            elif "Reinforced" in result:
                self.add_event(result, "success")
            
            elif "Gained" in result and "resources" in result:
                self.add_event(result, "info")

# Legacy functions for backward compatibility
def init_visualization(width=800, height=600):
    """Legacy function - creates a basic screen"""
    pygame.init()
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Harford County Strategy Game")
    return screen

def draw_game_state(screen, game):
    """Legacy function - basic drawing without animations"""
    # Create a temporary visualizer for basic drawing
    temp_viz = GameVisualizer(screen.get_width(), screen.get_height())
    temp_viz.screen = screen
    temp_viz.draw_game_state(game)