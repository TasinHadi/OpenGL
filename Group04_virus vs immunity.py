
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import random
import math
import time

# Import font constants
try:
    from OpenGL.GLUT import GLUT_BITMAP_HELVETICA_18
except ImportError:
    GLUT_BITMAP_HELVETICA_18 = 7  # Fallback value

# Camera-related variables
camera_pos = (0, 800, 800)

fovY = 60
GRID_LENGTH = 600

# Game state variables
game_time = 100.0  # 100 seconds per level (4 waves × 25 seconds)
start_time = None
pause_start_time = None  # Track when pause started
total_pause_time = 0.0   # Total time spent paused
heart_health = 100
player_energy = 100
score = 0
wave_number = 1
max_waves = 4  # Total of 4 waves
wave_interval = 25.0  # 25 seconds per wave
game_over = False
game_won = False
paused = False

# Game objects
viruses = []
immune_cells = []
heart_pos = (0, 0, 50)
placement_radius = 400  # Bigger radius around heart where immune cells can be placed

# Virus management for 20-virus system
MAX_VIRUSES = 20
viruses_per_corner = 5
corner_virus_counts = [0, 0, 0, 0]  # Track viruses from each corner

# Timing variables
last_virus_spawn = 0
last_energy_regen = 0
virus_spawn_interval = 2.0  # seconds - faster spawning for one-by-one effect

# Wave system variables (as per requirements - 30 sec intervals)
wave_start_time = None
wave_flash_time = 0
wave_flash_duration = 2.0  # Show "Wave X!" for 2 seconds

# Boost variables
immune_boost_time = 0
immune_boost_duration = 10.0  # 10 seconds

# Click marker for debugging
click_marker_pos = None
click_marker_time = 0

# View mode system
view_mode_enabled = False  # V key toggles this

# Medicine card system
medicine_card_active = True  # True when medicine card is available to click
medicine_card_uses_remaining = 4  # Can be used 4 times per game
medicine_card_max_uses = 4  # Maximum uses per game
medicine_boost_duration = 5.0  # 5 seconds boost duration
medicine_boost_active = False  # True when medicine boost is currently active
medicine_boost_end_time = 0.0  # When the current medicine boost ends

class Virus:
    def __init__(self, x, y, corner_index=0):
        # Start at exact spawn point initially
        self.x = float(x)
        self.y = float(y)
        self.z = 10.0
        self.base_speed = 15.0  # Base speed
        self.speed = self.base_speed + (wave_number * 8)  # +8 speed per wave
        self.radius = 15
        self.health = 1
        self.corner_index = corner_index  # Track which corner this virus came from
        
        # Add scattering behavior
        self.scatter_time = random.uniform(1.0, 3.0)  # Time to scatter before moving to heart
        self.spawn_time = time.time()
        self.has_scattered = False
        
        # Random scatter destination within grid bounds
        self.scatter_target_x = random.uniform(-GRID_LENGTH + 100, GRID_LENGTH - 100)
        self.scatter_target_y = random.uniform(-GRID_LENGTH + 100, GRID_LENGTH - 100)

    def update(self, dt):
        current_time = time.time()
        time_since_spawn = current_time - self.spawn_time
        
        # First phase: scatter to random position
        if time_since_spawn < self.scatter_time and not self.has_scattered:
            # Move to scatter position
            dx = self.scatter_target_x - self.x
            dy = self.scatter_target_y - self.y
            distance = math.sqrt(dx*dx + dy*dy)
            
            if distance > 5:  # Still moving to scatter position
                self.x += (dx / distance) * self.speed * dt
                self.y += (dy / distance) * self.speed * dt
            else:
                self.has_scattered = True
                
        # Second phase: move toward heart after scattering
        else:
            dx = heart_pos[0] - self.x
            dy = heart_pos[1] - self.y
            distance = math.sqrt(dx*dx + dy*dy)

            if distance > 0:
                # Add some random movement for organic behavior
                random_x = random.uniform(-0.2, 0.2) * self.speed * dt
                random_y = random.uniform(-0.2, 0.2) * self.speed * dt
                
                # Move toward heart with randomness
                self.x += (dx / distance) * self.speed * dt + random_x
                self.y += (dy / distance) * self.speed * dt + random_y

    def draw(self):
        """Draw virus with blue body and enhanced purple spikes"""
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        
        # Draw main blue/cyan body
        glColor3f(0.0, 0.8, 1.0)  # Bright cyan/blue
        gluSphere(gluNewQuadric(), self.radius, 10, 10)
        
        # Draw random purple spikes - 20 spikes randomly positioned
        glColor3f(0.8, 0.1, 0.9)  # Brighter purple color
        
        # Generate 20 random spike positions around the sphere
        for i in range(20):
            glPushMatrix()
            
            # Generate random position on sphere surface
            x = random.uniform(-1, 1)
            y = random.uniform(-1, 1) 
            z = random.uniform(-1, 1)
            
            # Normalize to put on sphere surface
            length = (x*x + y*y + z*z) ** 0.5
            if length > 0:
                x /= length
                y /= length
                z /= length
            
            # Position spike on sphere surface
            glTranslatef(x * self.radius * 0.8, 
                       y * self.radius * 0.8, 
                       z * self.radius * 0.8)
            
            # Random rotation for spike direction
            glRotatef(random.uniform(0, 360), x, y, z)
            
            # Draw cone spike
            gluCylinder(gluNewQuadric(), self.radius * 0.25, 0, self.radius * 0.6, 6, 1)
            glPopMatrix()
        
        glPopMatrix()

    def distance_to_heart(self):
        dx = heart_pos[0] - self.x
        dy = heart_pos[1] - self.y
        return math.sqrt(dx*dx + dy*dy)

class ImmuneCell:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.z = 25.0
        self.size = 25  # Slightly bigger than viruses (virus radius is 15, so 25 is bigger)
        self.attack_range = 20  # Reduced for actual touch collision (immune size 25 + virus radius 15)
        self.speed = 30.0
        self.target_virus = None
        self.target_boost = None  # New target for boost pickups
        self.kills = 0  # Track number of viruses killed
        self.max_kills = 3  # Maximum viruses this immune cell can kill
        self.spawn_time = time.time()  # Record when the cell is created
        self.activation_delay = 0.5  # 0.5-second delay before becoming active
        self.boosted = False  # Track if this immune cell is boosted
        self.boost_kills = 0  # Track kills made while boosted

    def update(self, dt):
        global immune_boost_time

        # Wait for the activation delay before the cell can act
        if time.time() - self.spawn_time < self.activation_delay:
            return None

        # Find nearest target (boost pickup or virus)
        if (not self.target_virus or self.target_virus not in viruses) and (not self.target_boost or self.target_boost.collected):
            self.find_nearest_target()

        # Handle boost pickup collection
        if self.target_boost and not self.target_boost.collected:
            dx = self.target_boost.x - self.x
            dy = self.target_boost.y - self.y
            distance = math.sqrt(dx*dx + dy*dy)
            
            # Check if we can collect the boost
            if distance <= 25:  # Collection range
                self.target_boost.collected = True
                self.boosted = True
                # Clear the boost target
                self.target_boost = None
                # Find a virus target now
                self.find_nearest_target()
            else:
                # Move toward boost pickup
                move_speed = self.speed
                if medicine_boost_active:
                    move_speed *= 2  # Double speed when medicine boosted
                elif immune_boost_time > 0:
                    move_speed *= 2  # Double speed when globally boosted

                # Calculate new position toward boost
                new_x = self.x + (dx / distance) * move_speed * dt
                new_y = self.y + (dy / distance) * move_speed * dt
                
                # Apply boundary and collision constraints (same as virus targeting)
                self.x, self.y = self.apply_movement_constraints(new_x, new_y, dx, dy, distance, move_speed, dt)

        # Move toward target virus
        elif self.target_virus:
            dx = self.target_virus.x - self.x
            dy = self.target_virus.y - self.y
            distance = math.sqrt(dx*dx + dy*dy)

            if distance <= self.attack_range:
                # Attack virus (remove it)
                if self.target_virus in viruses:
                    global score, corner_virus_counts
                    # Update corner count when virus is destroyed
                    corner_virus_counts[self.target_virus.corner_index] -= 1
                    viruses.remove(self.target_virus)
                    score += 10
                    self.kills += 1  # Increment kill count
                    if self.boosted:
                        self.boost_kills += 1
                    # Spawn replacement virus immediately
                    spawn_virus()
                
                # Reset target and check if immune cell should be destroyed
                self.target_virus = None
                # Check destruction condition based on boost status
                max_allowed_kills = self.max_kills + (2 if self.boosted else 0)
                if self.kills >= max_allowed_kills:
                    # Mark for removal (will be handled in update_game)
                    return "destroy"
            elif distance > 0:
                # Move toward virus
                move_speed = self.speed
                if medicine_boost_active:
                    move_speed *= 2  # Double speed when medicine boosted
                elif immune_boost_time > 0:
                    move_speed *= 2  # Double speed when globally boosted

                # Calculate new position
                new_x = self.x + (dx / distance) * move_speed * dt
                new_y = self.y + (dy / distance) * move_speed * dt
                
                # Apply movement constraints and update position
                self.x, self.y = self.apply_movement_constraints(new_x, new_y, dx, dy, distance, move_speed, dt)
        
        # Return None if immune cell continues to exist
        return None

    def apply_movement_constraints(self, new_x, new_y, dx, dy, distance, move_speed, dt):
        """Apply boundary and collision constraints to movement"""
        # Check boundary constraint - immune cell cannot go outside blue circle
        # Account for immune cell size (self.size/2 is the radius of the cube)
        immune_cell_radius = self.size / 2.0
        distance_to_heart = distance_2d(new_x, new_y, heart_pos[0], heart_pos[1])
        max_allowed_distance = placement_radius - immune_cell_radius  # Subtract cell radius to prevent any part from crossing
        
        # Check collision with heart (heart radius is 40)
        heart_radius = 40
        min_distance_from_heart = heart_radius + immune_cell_radius + 5  # 5 units buffer for collision detection
        
        # Check if new position would cause collision with heart
        if distance_to_heart < min_distance_from_heart:
            # Bounce away from heart - reverse direction and move away
            heart_dx = new_x - heart_pos[0]
            heart_dy = new_y - heart_pos[1]
            heart_distance = math.sqrt(heart_dx*heart_dx + heart_dy*heart_dy)
            
            if heart_distance > 0:
                # Normalize and push away from heart
                push_distance = min_distance_from_heart - distance_to_heart + 2  # Extra push to avoid sticking
                new_x = heart_pos[0] + (heart_dx / heart_distance) * (min_distance_from_heart + push_distance)
                new_y = heart_pos[1] + (heart_dy / heart_distance) * (min_distance_from_heart + push_distance)
                
                # Ensure the pushed position is still within blue circle bounds
                pushed_distance_to_heart = distance_2d(new_x, new_y, heart_pos[0], heart_pos[1])
                if pushed_distance_to_heart + immune_cell_radius > placement_radius:
                    # If pushing out would exceed boundary, find a tangent position
                    angle_to_heart = math.atan2(heart_dy, heart_dx)
                    # Try moving perpendicular to heart direction
                    perp_angle1 = angle_to_heart + math.pi/2
                    perp_angle2 = angle_to_heart - math.pi/2
                    
                    # Try both perpendicular directions and pick the valid one
                    safe_distance = (min_distance_from_heart + max_allowed_distance) / 2
                    new_x1 = heart_pos[0] + math.cos(perp_angle1) * safe_distance
                    new_y1 = heart_pos[1] + math.sin(perp_angle1) * safe_distance
                    new_x2 = heart_pos[0] + math.cos(perp_angle2) * safe_distance  
                    new_y2 = heart_pos[1] + math.sin(perp_angle2) * safe_distance
                    
                    # Choose the position closer to original target (either virus or boost)
                    target_x = self.target_virus.x if self.target_virus else (self.target_boost.x if self.target_boost else self.x)
                    target_y = self.target_virus.y if self.target_virus else (self.target_boost.y if self.target_boost else self.y)
                    
                    dist1 = distance_2d(new_x1, new_y1, target_x, target_y)
                    dist2 = distance_2d(new_x2, new_y2, target_x, target_y)
                    
                    if dist1 < dist2:
                        new_x, new_y = new_x1, new_y1
                    else:
                        new_x, new_y = new_x2, new_y2

        # Check blue circle boundary constraint
        elif distance_to_heart + immune_cell_radius > placement_radius:
            # Movement would cross boundary - find the maximum allowed movement
            current_distance_to_heart = distance_2d(self.x, self.y, heart_pos[0], heart_pos[1])
            
            if current_distance_to_heart + immune_cell_radius < placement_radius:
                # Calculate direction to target
                direction_x = dx / distance
                direction_y = dy / distance
                
                # Binary search for maximum allowed movement distance
                min_step = 0.0
                max_step = move_speed * dt
                
                for _ in range(10):  # 10 iterations for precision
                    test_step = (min_step + max_step) / 2
                    test_x = self.x + direction_x * test_step
                    test_y = self.y + direction_y * test_step
                    test_distance = distance_2d(test_x, test_y, heart_pos[0], heart_pos[1])
                    
                    if test_distance + immune_cell_radius <= placement_radius:
                        min_step = test_step
                    else:
                        max_step = test_step
                
                # Move with the maximum allowed step
                if min_step > 0:
                    new_x = self.x + direction_x * min_step
                    new_y = self.y + direction_y * min_step
                else:
                    # Can't move toward target, stay in current position
                    new_x = self.x
                    new_y = self.y
            else:
                # Already at boundary, don't move
                new_x = self.x
                new_y = self.y

        return new_x, new_y

    def find_nearest_target(self):
        # First priority: Look for purple boost pickups (BoostImmune) if not already boosted
        if not self.boosted and boost_immunes:
            nearest_boost = None
            min_boost_dist = float('inf')
            
            for boost in boost_immunes:
                if boost.collected:
                    continue
                    
                dx = boost.x - self.x
                dy = boost.y - self.y
                boost_distance = math.sqrt(dx*dx + dy*dy)
                
                # Purple pickups are high priority, look within reasonable range
                if boost_distance < 200:  # Look for boosts within 200 units
                    # Check if any other immune cell is closer to this boost
                    i_am_closest = True
                    for other_cell in immune_cells:
                        if other_cell is self or other_cell.boosted:  # Skip self and already boosted cells
                            continue
                            
                        other_dx = boost.x - other_cell.x
                        other_dy = boost.y - other_cell.y
                        other_boost_dist = math.sqrt(other_dx*other_dx + other_dy*other_dy)
                        
                        if other_boost_dist < boost_distance - 10:  # If another cell is closer
                            i_am_closest = False
                            break
                    
                    if i_am_closest and boost_distance < min_boost_dist:
                        min_boost_dist = boost_distance
                        nearest_boost = boost
            
            # If we found a boost pickup, target it
            if nearest_boost:
                self.target_virus = None  # Clear virus target
                self.target_boost = nearest_boost
                return
        
        # Clear boost target if we're boosted or no boosts available
        self.target_boost = None
        
        # Second priority: Look for viruses
        if not viruses:
            self.target_virus = None
            return

        nearest = None
        min_dist = float('inf')
        
        # Check all viruses and find the best target considering other immune cells
        for virus in viruses:
            dx = virus.x - self.x
            dy = virus.y - self.y
            my_dist_to_virus = math.sqrt(dx*dx + dy*dy)
            
            # Prioritize viruses that are closer to heart (more dangerous)
            virus_distance_to_heart = distance_2d(virus.x, virus.y, heart_pos[0], heart_pos[1])
            
            # Expand search range to be much more aggressive - immune cells should see viruses from far away
            if my_dist_to_virus > 300:  # Increased sight range significantly
                continue
            
            # Check if any other immune cell is closer to this virus
            i_am_closest = True
            for other_cell in immune_cells:
                if other_cell is self:  # Skip self
                    continue
                    
                other_dx = virus.x - other_cell.x
                other_dy = virus.y - other_cell.y
                other_dist_to_virus = math.sqrt(other_dx*other_dx + other_dy*other_dy)
                
                # If another cell is significantly closer, let them handle it
                if other_dist_to_virus < my_dist_to_virus - 15:  # Increased buffer for better coordination
                    i_am_closest = False
                    break
            
            # Prioritize closer viruses, but also consider threat level (distance to heart)
            priority_distance = my_dist_to_virus + (virus_distance_to_heart * 0.3)
            
            # If I'm the closest (or close enough), consider this virus
            if i_am_closest and priority_distance < min_dist:
                min_dist = priority_distance
                nearest = virus

        self.target_virus = nearest

    def find_nearest_virus(self):
        # Keep this method for backward compatibility, but redirect to new method
        self.find_nearest_target()

    def draw(self):
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)

        # Change color based on boost status
        if medicine_boost_active:
            glColor3f(0.2, 1.0, 0.2)  # Bright green when medicine boosted
        elif self.boosted:
            glColor3f(1, 1, 0)  # Yellow when individually boosted
        elif immune_boost_time > 0:
            glColor3f(1, 0.5, 0)  # Orange when globally boosted
        else:
            glColor3f(1, 1, 1)  # White normally

        glutSolidCube(self.size)
        glPopMatrix()

    
    
class Protector:
    def __init__(self):
        # Start the protector at a safe distance from the heart
        self.x = 100.0
        self.y = 100.0 
        self.z = 25.0  # Same height as immune cells
        self.protector_angle = 0
        self.fall_angle = 0  # Start at 0, animate to 90 when game over (like your code)
        self.rotate_speed = 100
        self.speed = 180.0  # Movement speed (increased for smoother movement)
        self.size = 35  # Size of protector (slightly smaller but still prominent)
        self.max_distance_from_heart = 380.0  # Stay within blue circle (placement_radius - buffer)
        self.min_distance_from_heart = 60.0   # Don't get too close to heart
        self.health = 100  # Protector health

    def update_position(self, dx, dy):
        """Update protector position with smooth boundary checking"""
        # Calculate new position
        new_x = self.x + dx
        new_y = self.y + dy
        
        # Check distance from heart
        distance_to_heart = distance_2d(new_x, new_y, heart_pos[0], heart_pos[1])
        
        # Only allow movement if it stays within bounds
        if (distance_to_heart <= self.max_distance_from_heart and 
            distance_to_heart >= self.min_distance_from_heart):
            self.x = new_x
            self.y = new_y
        else:
            # Smooth boundary handling: allow sliding along the boundary
            current_distance = distance_2d(self.x, self.y, heart_pos[0], heart_pos[1])
            
            # Calculate movement vector
            move_length = math.sqrt(dx*dx + dy*dy)
            if move_length > 0:
                # Try to find maximum allowed movement in the desired direction
                direction_x = dx / move_length
                direction_y = dy / move_length
                
                # Use binary search for smooth boundary sliding
                min_step = 0.0
                max_step = move_length
                best_step = 0.0
                
                for _ in range(8):  # 8 iterations for good precision
                    test_step = (min_step + max_step) / 2
                    test_x = self.x + direction_x * test_step
                    test_y = self.y + direction_y * test_step
                    test_distance = distance_2d(test_x, test_y, heart_pos[0], heart_pos[1])
                    
                    if (test_distance <= self.max_distance_from_heart and 
                        test_distance >= self.min_distance_from_heart):
                        best_step = test_step
                        min_step = test_step
                    else:
                        max_step = test_step
                
                # Apply the maximum valid movement
                if best_step > 0.01:  # Lower threshold for smoother movement
                    self.x += direction_x * best_step
                    self.y += direction_y * best_step

    def rotate(self, angle_delta):
        """Rotate the protector by the given angle"""
        self.protector_angle = (self.protector_angle + angle_delta) % 360

    def move_forward(self, distance):
        """Move the protector forward/backward in the direction it's facing"""
        # Account for the 180-degree rotation applied in the draw method
        # The visual model is rotated 180 degrees, so we need to adjust accordingly
        visual_angle = self.protector_angle + 180
        angle_rad = math.radians(visual_angle)
        
        # Calculate movement vector based on current facing direction
        # In OpenGL coordinate system with our rotation
        dx = distance * math.sin(angle_rad)  # X component  
        dy = distance * math.cos(angle_rad)  # Y component
        
        # Use existing boundary checking logic
        self.update_position(dx, dy)

    def move_forward_facing(self, distance):
        """Move the protector forward in the direction it's facing (like W key in your code)"""
        # Use trigonometry like in your code snippet
        dx = math.cos(math.radians(self.protector_angle)) * distance
        dy = math.sin(math.radians(self.protector_angle)) * distance
        self.update_position(dx, dy)
        
    def move_backward_facing(self, distance):
        """Move the protector backward from the direction it's facing (like S key in your code)"""
        dx = math.cos(math.radians(self.protector_angle)) * distance
        dy = math.sin(math.radians(self.protector_angle)) * distance
        self.update_position(-dx, -dy)  # Negative for backward
        
    def rotate_left(self, angle_delta):
        """Rotate the protector left (like A key in your code)"""
        self.protector_angle = (self.protector_angle + angle_delta) % 360
        
    def rotate_right(self, angle_delta):
        """Rotate the protector right (like D key in your code)"""
        self.protector_angle = (self.protector_angle - angle_delta) % 360
        
    def move_up(self, distance):
        """Move the protector up (positive Y direction)"""
        self.update_position(0, distance)
        
    def move_down(self, distance):
        """Move the protector down (negative Y direction)"""
        self.update_position(0, -distance)
        
    def move_left(self, distance):
        """Move the protector left (negative X direction)"""
        self.update_position(-distance, 0)
        
    def move_right(self, distance):
        """Move the protector right (positive X direction)"""
        self.update_position(distance, 0)

    def draw(self):
        """Draw the protector with detailed player-like appearance (based on your code structure)"""
        glPushMatrix()
        # Apply transformations like in your code
        glTranslatef(self.x, self.y, self.z)
        glRotatef(180, 0, 0, 1)  # Base rotation
        glRotatef(self.protector_angle, 0, 0, 1)  # Protector facing direction
        
        # Game over animation or health zero animation (similar to your fall_rotation)
        if game_over or self.health <= 0:
            glRotatef(self.fall_angle, 1, 0, 0)  # Fall forward like in your code

        # Scale the protector - slightly smaller but still visible (0.4 scale factor)
        scale_factor = 0.4
        
        # head
        glColor3f(0, 0, 0)
        glTranslatef(0, 0, 165 * scale_factor) 
        gluSphere(gluNewQuadric(), 15 * scale_factor, 10, 10)  
        glTranslatef(0, 0, -165 * scale_factor) 

        # green cube body
        glColor3f(0, 0.4, 0)
        glTranslatef(0, 0, 100 * scale_factor)  
        glScalef(0.5 * scale_factor, 1 * scale_factor, 2 * scale_factor)  # Scale the cube to make it a cuboid (2x width, 1x height, 1x depth)
        glutSolidCube(50) 
        glScalef(2 / scale_factor, 1 / scale_factor, 0.5 / scale_factor)
        glTranslatef(0, 0, -100 * scale_factor)
        
        glColor3f(1, 0.8, 0.6)  # Skin color 
        # right hand
        glTranslatef(0, 30 * scale_factor, 125 * scale_factor)
        glRotatef(-90, 0, 1, 0)  
        gluCylinder(gluNewQuadric(), 10 * scale_factor, 5 * scale_factor, 50 * scale_factor, 10, 10) 
        glRotatef(90, 0, 1, 0)  

        #left hand
        glTranslatef(0, -30 * scale_factor, -125 * scale_factor)
        glTranslatef(0, -30 * scale_factor, 125 * scale_factor)
        glRotatef(-90, 0, 1, 0)  
        gluCylinder(gluNewQuadric(), 10 * scale_factor, 5 * scale_factor, 50 * scale_factor, 10, 10)  
        glRotatef(90, 0, 1, 0)  
        glTranslatef(0, 30 * scale_factor, -125 * scale_factor)

        # right leg
        glColor3f(0, 0, 1)
        glTranslatef(0, 10 * scale_factor, 50 * scale_factor)
        glRotatef(180, 0, 1, 0)  
        gluCylinder(gluNewQuadric(), 10 * scale_factor, 5 * scale_factor, 50 * scale_factor, 10, 10)  
        glRotatef(-180, 0, 1, 0)  
        
        # left leg
        glTranslatef(0, -10 * scale_factor, -50 * scale_factor)
        glTranslatef(0, -10 * scale_factor, 50 * scale_factor)
        glRotatef(180, 0, 1, 0)  
        gluCylinder(gluNewQuadric(), 10 * scale_factor, 5 * scale_factor, 50 * scale_factor, 10, 10)  
        glRotatef(-180, 0, 1, 0)  
        glTranslatef(0, 10 * scale_factor, -50 * scale_factor)     

        # gray colour sword
        glColor3f(0.5, 0.5, 0.5)  
        glTranslatef(0, 0, 125 * scale_factor)  
        glRotatef(-90, 0, 1, 0)  
        glScalef(1 * scale_factor, 1 * scale_factor, 2 * scale_factor)  
        gluCylinder(gluNewQuadric(), 10, 3, 40, 10, 10)  
        glScalef(1 / scale_factor, 1 / scale_factor, 0.5 / scale_factor)  
        glRotatef(90, 0, 1, 0)  
        glTranslatef(0, 0, -125 * scale_factor)

        glPopMatrix()


# Initialize protector after class definition
protector = None  # Will be initialized in main()

# Medicine class removed - only medicine card UI remains

# Medicine system variables removed - only medicine card remains

class BoostImmune:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.z = 20.0
        self.size = 25  # Size of boost immune object
        self.radius = 20  # Collision radius
        self.collected = False
        self.pulse_time = 0  # For pulsing effect
        self.rotation_angle = 0  # For rotation animation
        
    def update(self, dt):
        """Update boost immune animation"""
        self.pulse_time += dt * 2  # Pulsing animation speed
        self.rotation_angle += dt * 90  # Rotate 90 degrees per second
    
    def draw(self):
        """Draw boost immune with pulsing purple diamond shape"""
        if self.collected:
            return
            
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        
        # Pulsing effect
        pulse = 0.9 + 0.1 * math.sin(self.pulse_time)
        size = self.size * pulse
        
        # Rotation animation
        glRotatef(self.rotation_angle, 0, 0, 1)
        
        # Purple color for boost immune
        glColor3f(0.8, 0.2, 0.9)  # Bright purple
        
        # Draw diamond/octahedron shape
        glBegin(GL_TRIANGLES)
        
        # Top pyramid (4 triangular faces)
        # Front face
        glVertex3f(0, size, 0)      # Top point
        glVertex3f(-size*0.7, 0, 0) # Left point
        glVertex3f(0, 0, size*0.7)   # Forward point
        
        # Right face  
        glVertex3f(0, size, 0)      # Top point
        glVertex3f(0, 0, size*0.7)   # Forward point
        glVertex3f(size*0.7, 0, 0)   # Right point
        
        # Back face
        glVertex3f(0, size, 0)      # Top point
        glVertex3f(size*0.7, 0, 0)   # Right point
        glVertex3f(0, 0, -size*0.7)  # Back point
        
        # Left face
        glVertex3f(0, size, 0)      # Top point
        glVertex3f(0, 0, -size*0.7)  # Back point
        glVertex3f(-size*0.7, 0, 0) # Left point
        
        # Bottom pyramid (4 triangular faces)
        # Front face
        glVertex3f(0, -size, 0)     # Bottom point
        glVertex3f(0, 0, size*0.7)   # Forward point
        glVertex3f(-size*0.7, 0, 0) # Left point
        
        # Right face
        glVertex3f(0, -size, 0)     # Bottom point
        glVertex3f(size*0.7, 0, 0)   # Right point
        glVertex3f(0, 0, size*0.7)   # Forward point
        
        # Back face
        glVertex3f(0, -size, 0)     # Bottom point
        glVertex3f(0, 0, -size*0.7)  # Back point
        glVertex3f(size*0.7, 0, 0)   # Right point
        
        # Left face
        glVertex3f(0, -size, 0)     # Bottom point
        glVertex3f(-size*0.7, 0, 0) # Left point
        glVertex3f(0, 0, -size*0.7)  # Back point
        
        glEnd()
        
        glPopMatrix()

# Boost Immune system variables
boost_immunes = []
boost_immune_spawn_times = [30.0, 60.0, 90.0]  # Spawn at 30, 60, 90 seconds
boost_immune_spawned = [False, False, False]  # Track which ones have been spawned



# Fixed virus spawn points - properly inside the grid
virus_spawn_points = [
    (-GRID_LENGTH, -GRID_LENGTH),  # Bottom-left (inside grid)
    (-GRID_LENGTH, GRID_LENGTH),   # Top-left (inside grid)
    (GRID_LENGTH, -GRID_LENGTH),   # Bottom-right (inside grid)
    (GRID_LENGTH, GRID_LENGTH),    # Top-right (inside grid)
]

def draw_grid_border():
    """Draw border around the game grid"""
    glColor3f(1.0, 1.0, 1.0)  # White border
    glLineWidth(3.0)
    
    # Draw border lines around the grid
    glBegin(GL_LINE_LOOP)
    glVertex3f(-GRID_LENGTH, -GRID_LENGTH, 2)  # Bottom-left
    glVertex3f(GRID_LENGTH, -GRID_LENGTH, 2)   # Bottom-right
    glVertex3f(GRID_LENGTH, GRID_LENGTH, 2)    # Top-right
    glVertex3f(-GRID_LENGTH, GRID_LENGTH, 2)   # Top-left
    glEnd()
    
    glLineWidth(1.0)  # Reset line width

def draw_spawn_points():
    """Mark spawn points with bigger purple cubes"""
    glColor3f(0.7, 0.2, 0.9)  # Purple markers for spawn points
    for point in virus_spawn_points:
        glPushMatrix()
        glTranslatef(point[0], point[1], 15)
        glutSolidCube(35)  # Even bigger spawn point markers
        glPopMatrix()

def spawn_virus():
    """Spawn single virus from random corner with scattering behavior"""
    global corner_virus_counts, last_virus_spawn
    
    # Only spawn if we have less than 20 viruses total
    if len(viruses) < MAX_VIRUSES:
        # Pick a completely random corner for more variety
        corner_index = random.randint(0, 3)
        spawn_point = virus_spawn_points[corner_index]
        
        # Spawn at the exact spawn point (scattering handled in Virus class)
        virus_x = spawn_point[0]
        virus_y = spawn_point[1]
        
        new_virus = Virus(virus_x, virus_y, corner_index)
        viruses.append(new_virus)
        corner_virus_counts[corner_index] += 1

# spawn_medicine function removed - only medicine card remains

def spawn_boost_immune():
    """Spawn boost immune at random position within the blue circle"""
    global boost_immunes
    
    # Generate random position within the blue circle (placement_radius)
    angle = random.uniform(0, 2 * math.pi)
    distance = random.uniform(80, placement_radius - 50)  # Stay away from heart and edge
    
    boost_x = heart_pos[0] + distance * math.cos(angle)
    boost_y = heart_pos[1] + distance * math.sin(angle)
    
    new_boost = BoostImmune(boost_x, boost_y)
    boost_immunes.append(new_boost)
    print(f"Boost Immune spawned at ({boost_x:.1f}, {boost_y:.1f})")

def activate_medicine_boost():
    """Activate medicine boost for all immune cells"""
    global medicine_boost_active, medicine_boost_end_time, medicine_card_uses_remaining, medicine_card_active
    
    if not medicine_card_active or medicine_card_uses_remaining <= 0:
        return False
    
    current_time = get_current_game_time() if start_time else 0
    
    # Activate the boost
    medicine_boost_active = True
    medicine_boost_end_time = current_time + medicine_boost_duration
    medicine_card_uses_remaining -= 1
    
    # Clear boost targets for all immune cells since they're now medicine boosted
    for immune_cell in immune_cells:
        immune_cell.target_boost = None
        # Find new virus targets since they no longer need boost pickups
        immune_cell.find_nearest_target()
    
    # Deactivate card if no uses remaining
    if medicine_card_uses_remaining <= 0:
        medicine_card_active = False
    
    print(f"Medicine boost activated! All immune cells boosted for {medicine_boost_duration} seconds!")
    print(f"Medicine uses remaining: {medicine_card_uses_remaining}")
    return True

def is_medicine_card_clicked(mouse_x, mouse_y):
    """Check if the medicine card was clicked"""
    # Card dimensions and position (same as in draw_medicine_card) - Updated for smaller card
    card_width = 140
    card_height = 50
    center_x = 500
    center_y = 750
    card_x = center_x - card_width/2
    card_y = center_y - card_height/2
    
    # Convert screen coordinates (mouse_y is from top, we need from bottom)
    screen_y = 800 - mouse_y
    
    # Check if click is within card bounds
    return (card_x <= mouse_x <= card_x + card_width and 
            card_y <= screen_y <= card_y + card_height)

def check_boost_immune_collision():
    """Check collision between immune cells and boost immune objects"""
    global boost_immunes
    
    if not boost_immunes or not immune_cells:
        return
        
    for boost in boost_immunes[:]:  # Use slice to avoid modification during iteration
        if boost.collected:
            continue
            
        for immune_cell in immune_cells:
            # Check collision using distance
            dx = immune_cell.x - boost.x
            dy = immune_cell.y - boost.y
            distance = math.sqrt(dx*dx + dy*dy)
            
            if distance < (immune_cell.size/2 + boost.radius):
                # Collision detected!
                immune_cell.boosted = True
                boost.collected = True
                boost_immunes.remove(boost)
                print(f"Immune cell boosted! Can now kill {immune_cell.max_kills + 2} viruses total.")
                break  # Only one immune cell can collect each boost

# check_medicine_collision function removed - only medicine card remains

def initialize_virus_system():
    """Initialize the game with no viruses - they will spawn one by one"""
    global corner_virus_counts
    corner_virus_counts = [0, 0, 0, 0]
    viruses.clear()
    # Start with no viruses - they will spawn gradually through the wave system


class AABB:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

def has_collided(box1, box2):
    return (box1.x < box2.x + box2.width and
            box1.x + box1.width > box2.x and
            box1.y < box2.y + box2.height and
            box1.y + box1.height > box2.y)


def screen_to_world(screen_x, screen_y):
    """Convert screen coordinates to world coordinates on the ground plane (z=0)"""
    # Use a direct mathematical approach based on our known camera setup
    # Get current camera position
    cam_x, cam_y, cam_z = camera_pos
    
    # Screen dimensions
    screen_width = 1000.0
    screen_height = 800.0
    
    # Convert screen coordinates to normalized device coordinates [-1, 1]
    # Mouse coordinates: (0,0) at top-left, (1000, 800) at bottom-right
    # NDC coordinates: (-1,-1) at bottom-left, (1,1) at top-right
    ndc_x = (screen_x / screen_width) * 2.0 - 1.0
    ndc_y = 1.0 - (screen_y / screen_height) * 2.0  # Flip Y and convert
    
    # Camera setup parameters
    fov_radians = math.radians(fovY)  # 60 degrees
    aspect_ratio = screen_width / screen_height  # 1.25
    
    # Calculate the size of the view frustum at z=1 (1 unit in front of camera)
    frustum_height = 2.0 * math.tan(fov_radians / 2.0)
    frustum_width = frustum_height * aspect_ratio
    
    # Convert NDC to view space coordinates at z=-1 (camera looks down -Z axis)
    view_x = ndc_x * (frustum_width / 2.0)
    view_y = ndc_y * (frustum_height / 2.0)
    view_z = -1.0
    
    # Create a ray from camera position through the view point
    # Ray direction in camera space
    ray_dir_x = view_x
    ray_dir_y = view_y  
    ray_dir_z = view_z
    
    # Normalize the ray direction
    ray_length = math.sqrt(ray_dir_x*ray_dir_x + ray_dir_y*ray_dir_y + ray_dir_z*ray_dir_z)
    ray_dir_x /= ray_length
    ray_dir_y /= ray_length
    ray_dir_z /= ray_length
    
    # Camera transformation: Our camera looks from (cam_x, cam_y, cam_z) towards (0, 0, 0)
    # Camera's forward vector (normalized)
    forward_x = -cam_x
    forward_y = -cam_y  
    forward_z = -cam_z
    forward_length = math.sqrt(forward_x*forward_x + forward_y*forward_y + forward_z*forward_z)
    forward_x /= forward_length
    forward_y /= forward_length
    forward_z /= forward_length
    
    # Camera's right vector (cross product of forward and world up)
    world_up_x, world_up_y, world_up_z = 0.0, 0.0, 1.0
    right_x = forward_y * world_up_z - forward_z * world_up_y
    right_y = forward_z * world_up_x - forward_x * world_up_z
    right_z = forward_x * world_up_y - forward_y * world_up_x
    right_length = math.sqrt(right_x*right_x + right_y*right_y + right_z*right_z)
    if right_length > 0:
        right_x /= right_length
        right_y /= right_length
        right_z /= right_length
    
    # Camera's up vector (cross product of right and forward)
    up_x = right_y * forward_z - right_z * forward_y
    up_y = right_z * forward_x - right_x * forward_z
    up_z = right_x * forward_y - right_y * forward_x
    
    # Transform ray direction from camera space to world space
    world_ray_x = ray_dir_x * right_x + ray_dir_y * up_x + ray_dir_z * forward_x
    world_ray_y = ray_dir_x * right_y + ray_dir_y * up_y + ray_dir_z * forward_y
    world_ray_z = ray_dir_x * right_z + ray_dir_y * up_z + ray_dir_z * forward_z
    
    # Find intersection of ray with ground plane (z = 0)
    # Ray equation: P = camera_pos + t * ray_direction
    # For ground plane: cam_z + t * world_ray_z = 0
    # Solve for t: t = -cam_z / world_ray_z
    
    if abs(world_ray_z) > 1e-10:  # Avoid division by zero
        t = -cam_z / world_ray_z
        world_x = cam_x + t * world_ray_x
        world_y = cam_y + t * world_ray_y
    else:
        # Ray is parallel to ground plane, return camera projection
        world_x = cam_x + ray_dir_x * 1000
        world_y = cam_y + ray_dir_y * 1000
    
    return float(world_x), float(world_y)

def distance_2d(x1, y1, x2, y2):
    return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)

def draw_text(x, y, text, font=None):
    if font is None:
        try:
            from OpenGL.GLUT import GLUT_BITMAP_HELVETICA_18
            font = GLUT_BITMAP_HELVETICA_18
        except ImportError:
            font = 7  # Fallback font value
    glColor3f(1, 1, 1)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def draw_heart():
    glPushMatrix()
    glTranslatef(heart_pos[0], heart_pos[1], heart_pos[2])

    # Color heart based on health
    if heart_health > 70:
        glColor3f(1, 0.3, 0.3)  # Bright red
    elif heart_health > 30:
        glColor3f(1, 0.5, 0)    # Orange
    else:
        glColor3f(0.7, 0, 0)    # Dark red

    gluSphere(gluNewQuadric(), 40, 12, 12)
    glPopMatrix()

def draw_placement_zone():
    # Draw a thicker, more visible circle showing where immune cells can be placed
    glColor3f(0.3, 0.7, 1.0)  # Brighter blue color for better visibility
    glLineWidth(8.0)  # Make line even thicker for better visibility
    glBegin(GL_LINE_LOOP)
    for i in range(64):  # More segments for smoother circle
        angle = i * 2 * math.pi / 64
        x = heart_pos[0] + placement_radius * math.cos(angle)
        y = heart_pos[1] + placement_radius * math.sin(angle)
        glVertex3f(x, y, 1)
    glEnd()
    glLineWidth(1.0)  # Reset line width

def draw_click_marker():
    """Draw a temporary marker at the click position for visual feedback."""
    global click_marker_pos, click_marker_time
    if click_marker_pos and time.time() - click_marker_time < 2.0:  # Show for 2 seconds
        glPushMatrix()
        glTranslatef(click_marker_pos[0], click_marker_pos[1], 20)
        
        # Pulsing effect
        pulse = 0.5 + 0.5 * math.sin((time.time() - click_marker_time) * 10)
        size = 10 + pulse * 5
        
        glColor3f(1, 1, 0)  # Yellow color for better visibility
        glutSolidSphere(size, 10, 10)
        glPopMatrix()
    else:
        click_marker_pos = None

def draw_left_corner_stats():
    """Draw stats in left corner without background panel"""
    # Calculate stats
    viruses_destroyed = score // 10
    
    # Draw text directly without background panel
    glColor3f(1.0, 1.0, 1.0)  # White text for visibility
    
    # Draw stats in left corner
    draw_text(15, 770, f"Score: {score}")
    draw_text(15, 750, f"Wave: {wave_number}")
    draw_text(15, 730, f"Viruses Killed: {viruses_destroyed}")
    
    # Add protector health and medicine info to left corner
    if protector:
        draw_text(15, 710, f"Protector Health: {protector.health}")
    # Medicine collection UI removed - only medicine card UI remains

def draw_medicine_card():
    """Draw medicine card at top-middle of screen (like pause card)"""
    global medicine_card_active, medicine_card_uses_remaining
    
    # Switch to 2D rendering
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    # Card dimensions and position (top-middle) - Made smaller
    card_width = 140
    card_height = 50
    center_x = 500  # Center of screen
    center_y = 750  # Top of screen
    card_x = center_x - card_width/2
    card_y = center_y - card_height/2
    border_width = 3
    
    # Draw outer border
    if medicine_card_active:
        glColor3f(0.2, 0.8, 0.2)  # Green border when available
    else:
        glColor3f(0.5, 0.5, 0.5)  # Gray border when on cooldown
    
    glBegin(GL_QUADS)
    glVertex2f(card_x - border_width, card_y - border_width)
    glVertex2f(card_x + card_width + border_width, card_y - border_width)
    glVertex2f(card_x + card_width + border_width, card_y + card_height + border_width)
    glVertex2f(card_x - border_width, card_y + card_height + border_width)
    glEnd()
    
    # Draw inner background
    if medicine_card_active:
        glColor3f(0.1, 0.3, 0.1)  # Dark green background when available
    else:
        glColor3f(0.2, 0.2, 0.2)  # Dark gray background when on cooldown
    
    glBegin(GL_QUADS)
    glVertex2f(card_x, card_y)
    glVertex2f(card_x + card_width, card_y)
    glVertex2f(card_x + card_width, card_y + card_height)
    glVertex2f(card_x, card_y + card_height)
    glEnd()
    
    # Draw medicine symbol (small green circle)
    circle_x = card_x + 25
    circle_y = card_y + card_height/2
    circle_radius = 12
    
    if medicine_card_active:
        glColor3f(0.2, 1.0, 0.2)  # Bright green circle when available
    else:
        glColor3f(0.4, 0.4, 0.4)  # Gray circle when on cooldown
    
    # Draw circle using small quads (simple circle approximation)
    glBegin(GL_QUADS)
    for i in range(16):  # 16 segments for smooth circle
        angle1 = (i * 2 * 3.14159) / 16
        angle2 = ((i + 1) * 2 * 3.14159) / 16
        
        x1 = circle_x + circle_radius * math.cos(angle1)
        y1 = circle_y + circle_radius * math.sin(angle1)
        x2 = circle_x + circle_radius * math.cos(angle2)
        y2 = circle_y + circle_radius * math.sin(angle2)
        
        # Create small quad for each segment
        glVertex2f(circle_x, circle_y)
        glVertex2f(x1, y1)
        glVertex2f(x2, y2)
        glVertex2f(circle_x, circle_y)
    glEnd()
    
    # Draw "MEDICINE" text - Made more visible with white color
    glColor3f(1.0, 1.0, 1.0)  # Always white text for better visibility
    
    text_x = card_x + 50  # Position more to the right for better visibility
    text_y = card_y + card_height/2 + 8  # Position higher for better visibility
    
    glRasterPos2f(text_x, text_y)
    medicine_text = "MEDICINE"
    # Use a reliable font that should work
    try:
        from OpenGL.GLUT import GLUT_BITMAP_HELVETICA_18
        font = GLUT_BITMAP_HELVETICA_18  # Use larger, more reliable font
    except:
        try:
            from OpenGL.GLUT import GLUT_BITMAP_HELVETICA_12
            font = GLUT_BITMAP_HELVETICA_12
        except:
            font = 7  # Fallback font value (GLUT_BITMAP_HELVETICA_18)
    for ch in medicine_text:
        glutBitmapCharacter(font, ord(ch))
    
    # Show uses remaining
    if medicine_card_active:
        uses_text = f"({medicine_card_uses_remaining}/4)"
        glRasterPos2f(text_x - 10, text_y - 15)
        for ch in uses_text:
            glutBitmapCharacter(font, ord(ch))
    else:
        # Show "USED" when no uses remaining
        glColor3f(0.8, 0.2, 0.2)  # Red text for "USED"
        used_text = "USED"
        glRasterPos2f(text_x + 5, text_y - 15)
        for ch in used_text:
            glutBitmapCharacter(font, ord(ch))
    
    # Restore matrices
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def draw_pause_screen():
    """Draw pause screen with pause symbol and text"""
    # Switch to 2D rendering
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    # Draw semi-transparent overlay
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glColor4f(0.0, 0.0, 0.0, 0.5)  # Semi-transparent black
    glBegin(GL_QUADS)
    glVertex2f(0, 0)
    glVertex2f(1000, 0)
    glVertex2f(1000, 800)
    glVertex2f(0, 800)
    glEnd()
    glDisable(GL_BLEND)
    
    # Draw pause symbol (two vertical bars)
    glColor3f(1.0, 1.0, 1.0)  # White color
    bar_width = 20
    bar_height = 80
    center_x = 500
    center_y = 450
    spacing = 15
    
    # Left bar
    glBegin(GL_QUADS)
    glVertex2f(center_x - spacing - bar_width, center_y - bar_height/2)
    glVertex2f(center_x - spacing, center_y - bar_height/2)
    glVertex2f(center_x - spacing, center_y + bar_height/2)
    glVertex2f(center_x - spacing - bar_width, center_y + bar_height/2)
    glEnd()
    
    # Right bar
    glBegin(GL_QUADS)
    glVertex2f(center_x + spacing, center_y - bar_height/2)
    glVertex2f(center_x + spacing + bar_width, center_y - bar_height/2)
    glVertex2f(center_x + spacing + bar_width, center_y + bar_height/2)
    glVertex2f(center_x + spacing, center_y + bar_height/2)
    glEnd()
    
    # Draw rectangular box for text (game-style design) - smaller size
    box_width = 240  # Reduced from 300
    box_height = 70   # Reduced from 120
    box_x = center_x - box_width/2
    box_y = center_y - 200
    border_width = 6  # Slightly thinner border
    
    # Draw outer border (dark gray)
    glColor3f(0.2, 0.2, 0.2)
    glBegin(GL_QUADS)
    glVertex2f(box_x - border_width, box_y - border_width)
    glVertex2f(box_x + box_width + border_width, box_y - border_width)
    glVertex2f(box_x + box_width + border_width, box_y + box_height + border_width)
    glVertex2f(box_x - border_width, box_y + box_height + border_width)
    glEnd()
    
    # Draw inner border (light gray)
    glColor3f(0.7, 0.7, 0.7)
    glBegin(GL_QUADS)
    glVertex2f(box_x - border_width/2, box_y - border_width/2)
    glVertex2f(box_x + box_width + border_width/2, box_y - border_width/2)
    glVertex2f(box_x + box_width + border_width/2, box_y + box_height + border_width/2)
    glVertex2f(box_x - border_width/2, box_y + box_height + border_width/2)
    glEnd()
    
    # Draw main background (dark blue-gray)
    glColor3f(0.1, 0.1, 0.2)
    glBegin(GL_QUADS)
    glVertex2f(box_x, box_y)
    glVertex2f(box_x + box_width, box_y)
    glVertex2f(box_x + box_width, box_y + box_height)
    glVertex2f(box_x, box_y + box_height)
    glEnd()
    
    # Draw "PAUSED" text in the box
    glColor3f(1.0, 1.0, 0.0)  # Yellow text for emphasis
    try:
        from OpenGL.GLUT import GLUT_BITMAP_HELVETICA_18
        font = GLUT_BITMAP_HELVETICA_18
    except:
        font = None
    
    if font:
        # Main "PAUSED" text (centered in smaller box)
        glRasterPos2f(box_x + 85, box_y + box_height - 28)
        paused_text = "PAUSED"
        for ch in paused_text:
            glutBitmapCharacter(font, ord(ch))
        
        # Instructions (centered in smaller box)
        glColor3f(0.9, 0.9, 0.9)  # Light gray for instructions
        glRasterPos2f(box_x + 45, box_y + box_height - 55)
        instruction_text = "Press P to Resume"
        for ch in instruction_text:
            glutBitmapCharacter(font, ord(ch))
    
    # Restore matrices
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def draw_ui():
    # Draw left corner stats (no background panel)
    draw_left_corner_stats()
    
    # Game info (remaining UI elements in right corner)
    if game_over and not game_won:
        # Show 0.0 time when game is lost
        draw_text(750, 770, f"Time Left: 0.0s")
    else:
        current_game_time = get_current_game_time() if start_time else 0
        time_left = max(0, game_time - current_game_time)
        draw_text(750, 770, f"Time Left: {time_left:.1f}s")
    
    draw_text(750, 740, f"Heart Health: {heart_health}")
    draw_text(750, 710, f"Energy: {player_energy}")

    # View mode indicator
    if view_mode_enabled:
        draw_text(750, 680, "VIEW MODE: ON")
    else:
        draw_text(750, 680, "VIEW MODE: OFF")

    # Boost indicators (only show when game is active)
    if not game_over:
        if medicine_boost_active:
            remaining_time = medicine_boost_end_time - get_current_game_time()
            draw_text(10, 520, f"MEDICINE BOOST: {remaining_time:.1f}s")
        elif immune_boost_time > 0:
            draw_text(10, 500, f"IMMUNE BOOST: {immune_boost_time:.1f}s")

    # Wave flash notification (as per requirements)
    if wave_flash_time > 0:
        current_time = get_current_game_time() if start_time else 0
        if current_time - wave_flash_time < wave_flash_duration:
            # Flash "Wave X!" message
            draw_text(450, 600, f"Wave {wave_number}!")

    # Instructions removed to clean up the screen

    # Game over messages
    if game_over:
        if game_won:
            draw_text(400, 400, "YOU WON! Press R to restart")
        else:
            draw_text(400, 400, "YOU LOSE! Press R to restart")

    # Pause overlay is now handled in showScreen() for proper rendering order

def get_current_game_time():
    """Get current game time accounting for pause time"""
    if not start_time:
        return 0.0
    
    current_pause_time = 0.0
    if paused and pause_start_time:
        current_pause_time = time.time() - pause_start_time
    
    return time.time() - start_time - total_pause_time - current_pause_time

def update_game(dt):
    global heart_health, player_energy, wave_number, game_over, game_won
    global last_virus_spawn, last_energy_regen, immune_boost_time
    global wave_start_time, wave_flash_time, corner_virus_counts
    global medicine_boost_active, medicine_boost_end_time

    if game_over or paused or not start_time:
        return

    current_time = get_current_game_time()

    # Check win condition - survive all 4 waves (100 seconds)
    if current_time >= game_time or wave_number > max_waves:
        game_over = True
        game_won = True
        return

    # Wave system: every 25 seconds for 4 waves total
    if wave_start_time is None:
        wave_start_time = current_time
    
    new_wave = min(int(current_time // wave_interval) + 1, max_waves)  # New wave every 25 seconds, max 4 waves
    if new_wave > wave_number and wave_number < max_waves:
        wave_number = new_wave
        wave_flash_time = current_time  # Start flash notification
        
        # Update existing viruses' speed for the new wave
        for virus in viruses:
            virus.speed = virus.base_speed + (wave_number * 8)

    # Spawn viruses one by one with timing intervals
    # Spawn rate increases with wave number (more frequent spawning in later waves)
    current_spawn_interval = max(0.8, virus_spawn_interval - (wave_number * 0.3))  # Faster spawning each wave
    target_viruses = min(MAX_VIRUSES, 3 + (wave_number * 4))  # More viruses per wave (3, 7, 11, 15)
    
    if current_time - last_virus_spawn > current_spawn_interval and len(viruses) < target_viruses:
        spawn_virus()
        last_virus_spawn = current_time

    # Spawn boost immune objects at specific times
    for i, spawn_time in enumerate(boost_immune_spawn_times):
        if current_time >= spawn_time and not boost_immune_spawned[i]:
            spawn_boost_immune()
            boost_immune_spawned[i] = True

    # Regenerate energy
    if current_time - last_energy_regen > 10.0:  # Every 10 seconds
        player_energy = min(100, player_energy + 5)
        last_energy_regen = current_time

    # Update immune boost timer
    if immune_boost_time > 0:
        immune_boost_time -= dt
    
    # Update medicine boost timer (only when game is active)
    if not game_over and medicine_boost_active and current_time >= medicine_boost_end_time:
        medicine_boost_active = False
        print("Medicine boost ended!")

    # Update all game objects
    for virus in viruses[:]:
        virus.update(dt)

        # Check collision between virus and protector
        if protector and protector.health > 0:
            virus_box = AABB(virus.x - virus.radius, virus.y - virus.radius, virus.radius * 2, virus.radius * 2)
            protector_box = AABB(protector.x - protector.size/2, protector.y - protector.size/2, protector.size, protector.size)
            
            if has_collided(virus_box, protector_box):
                protector.health -= 10
                # Remove virus after collision
                corner_virus_counts[virus.corner_index] -= 1
                viruses.remove(virus)
                # Spawn replacement virus
                spawn_virus()
                continue  # Skip heart collision check for this virus

        # Check if virus reached heart
        if virus.distance_to_heart() < 50:
            heart_health -= 10
            # Update corner count when virus reaches heart
            corner_virus_counts[virus.corner_index] -= 1
            viruses.remove(virus)
            # Spawn replacement virus
            spawn_virus()
            if heart_health <= 0:
                game_over = True
                game_won = False

    # Update immune cells and handle destruction
    for cell in immune_cells[:]:  # Use slice to avoid modification during iteration
        result = cell.update(dt)
        if result == "destroy":
            immune_cells.remove(cell)
    
    # Medicine update removed - only medicine card remains
    
    # Update boost immune objects
    for boost in boost_immunes:
        boost.update(dt)
    
    # Medicine collision removed - only medicine card remains
    
    # Check boost immune collision with immune cells
    check_boost_immune_collision()

def keyboardListener(key, x, y):
    global paused, game_over, heart_health, player_energy, score, wave_number
    global viruses, immune_cells, start_time, immune_boost_time
    global wave_start_time, wave_flash_time, last_virus_spawn, last_energy_regen
    global corner_virus_counts, game_won, view_mode_enabled
    global pause_start_time, total_pause_time, protector

    # Protector movement controls (WASD) - only when game is active, not paused, and protector is alive
    if not game_over and not paused and protector and protector.health > 0:
        # Use consistent movement distance for better responsiveness and smoother feel
        move_distance = 12.0  # Movement per key press
        rotation_angle = 6.0  # Rotation per key press
        
        # Hybrid control system - both direct movement and facing-based movement
        if key == b'w' or key == b'W':
            # Move forward in the direction protector is facing (like your code)
            protector.move_forward_facing(move_distance)
        elif key == b's' or key == b'S':
            # Move backward from the direction protector is facing (like your code)
            protector.move_backward_facing(move_distance)
        elif key == b'a' or key == b'A':
            # Rotate protector left (like your code)
            protector.rotate_left(rotation_angle)
        elif key == b'd' or key == b'D':
            # Rotate protector right (like your code)
            protector.rotate_right(rotation_angle)
        


    # Pause game - only works during active gameplay, not when game is over
    if key == b'p' or key == b'P':
        if not game_over:  # Only allow pause when game is active
            if not paused:
                # Starting pause
                paused = True
                pause_start_time = time.time()
            else:
                # Resuming from pause
                paused = False
                if pause_start_time is not None:
                    total_pause_time += time.time() - pause_start_time
                    pause_start_time = None

    # Toggle view mode
    if key == b'v' or key == b'V':
        view_mode_enabled = not view_mode_enabled
        print(f"View mode {'enabled' if view_mode_enabled else 'disabled'}")

    # Reset game
    if key == b'r' or key == b'R':
        heart_health = 100
        player_energy = 100
        score = 0
        wave_number = 1
        game_over = False
        game_won = False
        paused = False
        immune_boost_time = 0
        wave_start_time = None
        wave_flash_time = 0
        view_mode_enabled = False  # Reset view mode on restart
        
        # Reset timing variables
        last_virus_spawn = 0
        last_energy_regen = 0
        pause_start_time = None
        total_pause_time = 0.0
        
        # Clear all game objects
        immune_cells.clear()
        initialize_virus_system()  # This will clear viruses and reset corner counts
        # medicines.clear() removed - only medicine card remains
        boost_immunes.clear()  # Clear boost immune objects
        
        # Medicine system reset removed - only medicine card reset remains
        
        # Reset medicine card system
        global medicine_card_active, medicine_card_uses_remaining, medicine_boost_active, medicine_boost_end_time
        medicine_card_active = True
        medicine_card_uses_remaining = medicine_card_max_uses
        medicine_boost_active = False
        medicine_boost_end_time = 0.0
        
        # Reset boost immune system
        global boost_immune_spawned
        boost_immune_spawned = [False, False, False]
        
        # Reset protector position
        if protector:
            protector.x = 100.0
            protector.y = 100.0
            protector.protector_angle = 0
            protector.health = 100  # Reset protector health
        
        # Reset start time
        start_time = time.time()

def specialKeyListener(key, x, y):
    global camera_pos, view_mode_enabled, camera_angle
    
    # Only allow camera movement when view mode is enabled
    if not view_mode_enabled:
        return
    
    x, y, z = camera_pos

    if key == GLUT_KEY_LEFT:
        x -= 10
    if key == GLUT_KEY_RIGHT:
        x += 10
    if key == GLUT_KEY_UP:
        y -= 10
    if key == GLUT_KEY_DOWN:
        y += 10

    camera_pos = (x, y, z)

def mouseListener(button, state, x, y):
    global player_energy, immune_boost_time, click_marker_pos, click_marker_time
    # Medicine variables removed - only medicine card remains

    # Check medicine card click first (higher priority)
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN and not game_over and not paused:
        if is_medicine_card_clicked(x, y):
            if activate_medicine_boost():
                return  # Medicine card was clicked and activated, don't process other clicks

    # Right mouse button functionality removed - only medicine card remains

    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN and not game_over and not paused:
        # Validate screen coordinates are within viewport bounds
        if x < 0 or x > 1000 or y < 0 or y > 800:
            print(f"Click outside screen bounds: ({x}, {y})")
            return
        
        # Screen-space validation: Check if click is roughly within the game area
        # The game view is centered, so clicks should be in the middle area of the screen
        screen_center_x = 500  # Center of 1000px screen
        screen_center_y = 400  # Center of 800px screen
        max_screen_radius = 280  # Even stricter screen radius for placement zone
        
        # Also ensure click is not too close to edges where the view might be distorted
        min_x, max_x = 200, 800  # Horizontal bounds
        min_y, max_y = 120, 680  # Vertical bounds (avoid top UI area and bottom edge)
        
        screen_distance = math.sqrt((x - screen_center_x)**2 + (y - screen_center_y)**2)
        if screen_distance > max_screen_radius or x < min_x or x > max_x or y < min_y or y > max_y:
            print(f"Click REJECTED: Outside safe game area! Screen pos: ({x}, {y}), distance: {screen_distance:.1f}")
            return
            
        # Convert screen coordinates to world coordinates
        world_x, world_y = screen_to_world(x, y)
        
        # Early validation - check if coordinates were successfully converted
        if world_x is None or world_y is None:
            print("Failed to convert screen coordinates to world coordinates!")
            return
        
        # Set click marker for visual feedback
        click_marker_pos = (world_x, world_y)
        click_marker_time = time.time()
        
        # Debug prints
        print(f"Left click detected at screen: ({x}, {y})")
        print(f"Converted to world coordinates: ({world_x:.1f}, {world_y:.1f})")
        print(f"Current player energy: {player_energy}")

        # Check if within placement radius and have energy
        distance_to_heart = distance_2d(world_x, world_y, heart_pos[0], heart_pos[1])

        # Account for immune cell size - ensure no part of the cell crosses boundary
        immune_cell_size = 25  # Size of immune cell cube
        immune_cell_radius = immune_cell_size / 2.0
        visual_zone_radius = placement_radius - immune_cell_radius  # Subtract cell radius
        heart_radius = 40
        min_distance_from_heart = heart_radius + immune_cell_radius + 5  # Buffer for heart collision

        print(f"Click world coords: ({world_x:.1f}, {world_y:.1f})")
        print(f"Heart position: ({heart_pos[0]}, {heart_pos[1]})")
        print(f"Click distance: {distance_to_heart:.1f}, Effective zone radius: {visual_zone_radius:.1f}")
        
        # Strict zone validation - must be within placement zone
        if distance_to_heart > visual_zone_radius:
            print(f"Click REJECTED: Outside placement zone! Distance {distance_to_heart:.1f} > Zone radius {visual_zone_radius:.1f}")
            return

        # First check if we've reached the immune cell limit
        if len(immune_cells) >= 20:
            print("Maximum immune cells (20) already placed!")
        # Check if we have enough energy (reduced to 5)
        elif player_energy < 5:
            print("Not enough energy to place immune cell!")
        # Check if too close to heart (would cause collision)
        elif distance_to_heart < min_distance_from_heart:
            print("Too close to heart! Place immune cell further away.")
        else:
            # All conditions met - place the immune cell at clicked location
            new_immune_cell = ImmuneCell(world_x, world_y)
            immune_cells.append(new_immune_cell)
            player_energy -= 5  # Reduced energy cost
            print(f"Immune cell successfully placed at ({world_x:.1f}, {world_y:.1f})!")
            print(f"Remaining energy: {player_energy}")
            print(f"Immune cells: {len(immune_cells)}/20")

def setupCamera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fovY, 1.25, 0.1, 2000)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    x, y, z = camera_pos
    gluLookAt(x, y, z, 0, 0, 0, 0, 0, 1)



def idle():
    global protector
    
    # Handle fall animation when game is over or protector health is zero (like in your code)
    if protector and (game_over or protector.health <= 0):
        if protector.fall_angle < 90:
            protector.fall_angle += 2  # Same increment as your code
    
    update_game(1/60.0)  # 60 FPS
    glutPostRedisplay()

def showScreen():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glViewport(0, 0, 1000, 800)
    setupCamera()

    # Draw lighter uniform grid squares
    square_size = 40  # Small squares
    num_squares = int(GRID_LENGTH * 2 / square_size)
    
    for i in range(num_squares):
        for j in range(num_squares):
            x = -GRID_LENGTH + i * square_size
            y = -GRID_LENGTH + j * square_size
            
            # Uniform lighter color for all grid squares
            glColor3f(0.4, 0.5, 0.7)  # Lighter blue-gray for all squares
            
            glBegin(GL_QUADS)
            glVertex3f(x, y, 0)
            glVertex3f(x + square_size, y, 0)
            glVertex3f(x + square_size, y + square_size, 0)
            glVertex3f(x, y + square_size, 0)
            glEnd()

    # Draw grid border to show game area boundaries
    draw_grid_border()

    # Draw placement zone
    draw_placement_zone()

    # Draw spawn points (as per requirements)
    draw_spawn_points()

    # Draw heart
    draw_heart()

    # Draw all game objects
    for virus in viruses:
        virus.draw()

    for cell in immune_cells:
        cell.draw()

    # Medicine drawing removed - only medicine card remains

    # Draw boost immune objects
    for boost in boost_immunes:
        boost.draw()

    # Draw protector
    if protector:
        protector.draw()

    # Draw click marker for debugging
    draw_click_marker()

    # Draw UI
    draw_ui()
    
    # Draw medicine card (only during active gameplay)
    if not game_over and not paused:
        draw_medicine_card()
    
    # Draw pause screen last to ensure it appears on top
    if paused:
        glDisable(GL_DEPTH_TEST)  # Disable depth test for overlay
        draw_pause_screen()
        glEnable(GL_DEPTH_TEST)   # Re-enable depth test

    glutSwapBuffers()

def main():
    global start_time, protector
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1000, 800)
    glutInitWindowPosition(0, 0)
    wind = glutCreateWindow(b"Virus vs. Immunity - 3D Tower Defense")

    glEnable(GL_DEPTH_TEST)
    glClearColor(0.1, 0.1, 0.2, 1.0)

    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)

    # Initialize game objects
    protector = Protector()  # Initialize protector
    initialize_virus_system()
    start_time = time.time()

    print("Game Controls:")
    print("- Left Click: Place immune cell (5 energy, max 20)")
    # Right click medicine functionality removed
    print("- WASD Keys: Forward/backward movement + rotation (like your code)")
    print("- IJKL Keys: Direct up/left/down/right movement")
    print("- P: Pause/Unpause")
    print("- R: Restart game")
    print("- V: Toggle View Mode")
    print("- Arrow Keys: Move camera (View Mode)")
    print("\nObjective: Protect the heart for 100 seconds!")
    print(f"Features: Protector defense unit + 20 viruses on screen + Medicine system")

    glutMainLoop()

if __name__ == "__main__":
    main()
