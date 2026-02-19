from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from math import *
import random

camera_angle = 0  # Horizontal rotation (degrees)
camera_height = 500  # Vertical position (z)
camera_distance = 500  # Distance from center
camera_pos = (0, camera_height, camera_distance)

fovY = 120  # Field of view
GRID_LENGTH = 600  # Length of grid lines
rand_var = 423

# Player
player_pos = (0, 0, 0)  
player_angle = 0  
fall_angle = 90  
rotate_speed = 20 
player_speed = 30  
gun_length = 70  

# game
game_over = False  
life = 5
score = 0
bullet_missed = 0

# bullets
bullets = []  
bullet_speed = 0.5  
bullet_height = 100  
bullet_pos = player_pos  
bullet_angle = player_angle  

#mode
cheat= False
first_person = False  
gun_follow_camera = False

# enemy
enemy_pos = []
enemy_speed = 0.08
enemy_area = 100
time_pass = 0


def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glColor3f(1,1,1)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    
    # Set up an orthographic projection that matches window coordinates
    gluOrtho2D(0, 1000, 0, 800)  # left, right, bottom, top

    
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    # Draw text at (x, y) in screen coordinates
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    
    # Restore original projection and modelview matrices
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


def drawPlayer():
    global player_pos, fall_angle, game_over, player_angle, first_person

    glPushMatrix()  # Save the current matrix state
    x, y, z = player_pos  # Unpack player position
    glTranslatef(x, y, z)  # Move to the position of the player
    glRotatef(180, 0, 0, 1)  # Rotate to align with the player's direction
    glRotatef(player_angle, 0, 0, 1)  # Rotate to align with the player's direction
    if game_over:
        glRotatef(fall_angle, 0, 1, 0)

    if first_person:
        pass
    else:
        # head
        glColor3f(0, 0, 0)
        glTranslatef(0, 0, 165) 
        gluSphere(gluNewQuadric(), 15, 10, 10)  
        glTranslatef(0, 0, -165) 

        # green cube body
        glColor3f(0, 0.4, 0)
        glTranslatef(0, 0, 100)  
        glScalef(0.5, 1, 2)  # Scale the cube to make it a cuboid (2x width, 1x height, 1x depth)
        glutSolidCube(50) 
        glScalef(2, 1, 0.5)
        glTranslatef(0, 0, -100)
        
        glColor3f(1, 0.8, 0.6)  # Skin color 
        # right hand
        glTranslatef(0, 30, 125)
        glRotatef(-90, 0, 1, 0)  
        gluCylinder(gluNewQuadric(), 10, 5, 50, 10, 10) 
        glRotatef(90, 0, 1, 0)  

        #left hand
        glTranslatef(0, -30, -125)
        glTranslatef(0, -30, 125)
        glRotatef(-90, 0, 1, 0)  
        gluCylinder(gluNewQuadric(), 10, 5, 50, 10, 10)  
        glRotatef(90, 0, 1, 0)  
        glTranslatef(0, 30, -125)

        # right leg
        glColor3f(0, 0, 1)
        glTranslatef(0, 10, 50)
        glRotatef(180, 0, 1, 0)  
        gluCylinder(gluNewQuadric(), 10, 5, 50, 10, 10)  
        glRotatef(-180, 0, 1, 0)  
        
        # left leg
        glTranslatef(0, -10, -50)
        glTranslatef(0, -10, 50)
        glRotatef(180, 0, 1, 0)  
        gluCylinder(gluNewQuadric(), 10, 5, 50, 10, 10)  
        glRotatef(-180, 0, 1, 0)  
        glTranslatef(0, 10, -50)     

        # gray colour gun
        glColor3f(0.5, 0.5, 0.5)  
        glTranslatef(0, 0, 125)  
        glRotatef(-90, 0, 1, 0)  
        glScalef(1, 1, 2)  
        gluCylinder(gluNewQuadric(), 10, 3, 40, 10, 10)  
        glScalef(1, 1, 0.5)  
        glRotatef(90, 0, 1, 0)  
        glTranslatef(0, 0, -125)
    glPopMatrix()  


def drawEnemies():
    global enemy_pos, enemy_speed, time_pass
    
    scale = 1 + 0.07 * sin(time_pass) # Oscillates between 0.93 and 1.07 (less pronounced)

    for enemy in enemy_pos:
        glPushMatrix() 
        x, y, z = enemy['position']  
        glTranslatef(x, y, z)  
        glScalef(scale, scale, scale)  
        glColor3f(1, 0, 0)  
        glutSolidSphere(enemy_area, 10, 10)  
        glColor3f(0, 0, 0)  
        glTranslatef(0, 0, 75) 
        glutSolidSphere(enemy_area//2 , 10, 10)  
        glTranslatef(0, 0, -75)  # 
        glPopMatrix()  


def drawBullets():
    global bullets
    # Draw each bullet
    for i in bullets:
        glPushMatrix()
        glTranslatef(i[0], i[1], i[2])
        glRotatef(i[3], 0, 0, 1)  
        glColor3f(0, 0, 0)  
        glutSolidCube(10)  
        glPopMatrix()


def spawn_enemy():
    x = random.randint(-GRID_LENGTH + 50, GRID_LENGTH - 50)
    y = random.randint(-GRID_LENGTH + 50, GRID_LENGTH - 50)
    z = 50  # Fixed height for enemies
    enemy_pos.append((x, y, z))


def initialize_enemies():

    global enemy_pos
    enemy_pos.clear()
    for _ in range(5):
        x = random.randint(-GRID_LENGTH + 50, GRID_LENGTH - 50)
        y = random.randint(-GRID_LENGTH + 50, GRID_LENGTH - 50)
        z = 50
        enemy_pos.append({'position': [x, y, z]})


def draw_shapes():
    if game_over:
        drawPlayer()
    else:
        drawPlayer()
        drawBullets()
        drawEnemies()


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


def fire_bullet():
    global bullets, player_pos, player_angle
    x, y, z = player_pos
    bx = x + 60 * sin(radians(player_angle))
    by = y + 60 * cos(radians(player_angle))
    bz = z + 50
    bullets.append([bx, by, bz, player_angle])


def update_bullets_and_enemies():
    global bullets, enemy_pos, score, bullet_missed, life, game_over, player_pos, player_angle, cheat, time_pass
    if game_over:
        return
    # Move bullets
    new_bullets = []
    for b in bullets:
        bx, by, bz, bangle = b
        # Move bullet forward
        bx += bullet_speed * sin(radians(bangle))
        by += bullet_speed * cos(radians(bangle))
        # Remove if out of bounds
        if abs(bx) > GRID_LENGTH or abs(by) > GRID_LENGTH:
            bullet_missed += 1
            continue
        # Check collision with enemies
        hit = False
        for idx, enemy in enumerate(enemy_pos):
            ex, ey, ez = enemy['position']
            bullet_box = AABB(bx, by, 10, 10)
            enemy_box = AABB(ex, ey, enemy_area, enemy_area)
            if has_collided(bullet_box, enemy_box):
                score += 1
                # Respawn enemy
                enemy_pos[idx]['position'] = [random.randint(-GRID_LENGTH+50, GRID_LENGTH-50), random.randint(-GRID_LENGTH+50, GRID_LENGTH-50), 50]
                hit = True
                break
        if not hit:
            new_bullets.append([bx, by, bz, bangle])
    bullets = new_bullets

    # Move enemies toward player
    px, py, pz = player_pos
    for enemy in enemy_pos:
        ex, ey, ez = enemy['position']
        dx = px - ex
        dy = py - ey
        dist = sqrt(dx*dx + dy*dy)
        # Only move if not too close to player (reduce shaking)
        if dist > 30:
            ex += enemy_speed * dx / dist
            ey += enemy_speed * dy / dist
        enemy['position'] = [ex, ey, ez]
        # Shrink/expand effect
        time_pass += 0.05

        # Check collision with player
        player_box = AABB(px, py, 50, 50)
        enemy_box = AABB(ex, ey, enemy_area, enemy_area)
        if has_collided(player_box, enemy_box):
            life -= 1
            # Respawn enemy
            enemy['position'] = [random.randint(-GRID_LENGTH+50, GRID_LENGTH-50), random.randint(-GRID_LENGTH+50, GRID_LENGTH-50), 50]
            if life <= 0:
                game_over = True

    # Always keep 5 enemies
    while len(enemy_pos) < 5:
        enemy_pos.append({'position':[random.randint(-GRID_LENGTH+50, GRID_LENGTH-50), random.randint(-GRID_LENGTH+50, GRID_LENGTH-50), 50]})

    # Game over if too many missed
    if bullet_missed >= 10:
        game_over = True

    # Cheat mode: auto rotate and fire
    if cheat and not game_over:
        cheat_function()

 
def specialKeyListener(key, x, y):

    global camera_angle, camera_height, camera_distance, first_person
    if not first_person:
        
        if key == GLUT_KEY_UP:
            camera_height += 20
        
        if key == GLUT_KEY_DOWN:
            camera_height = max(100, camera_height - 20)
        
        if key == GLUT_KEY_LEFT:
            camera_angle = (camera_angle - 5) % 360
        
        if key == GLUT_KEY_RIGHT:
            camera_angle = (camera_angle + 5) % 360


def keyboardListener(key, x, y):
    global player_pos, player_angle, cheat, gun_follow_camera, game_over, life, score, bullet_missed, first_person
    if game_over:
        if key == b'r':
            # Reset game
            player_pos = (0, 0, 0)
            player_angle = 0
            life = 5
            score = 0
            bullet_missed = 0
            enemy_pos.clear()
            bullets.clear()
            initialize_enemies()
            game_over = False
        return
    # Move forward (W key)
    if key == b's':
        x, y, z = player_pos
        x += player_speed * sin(radians(player_angle))
        y += player_speed * cos(radians(player_angle))
        # Enforce grid boundaries - keep player well inside the grid
        x = max(-GRID_LENGTH+75, min(GRID_LENGTH-75, x))
        y = max(-GRID_LENGTH+75, min(GRID_LENGTH-75, y))
        player_pos = (x, y, z)
    
    if key == b'w':
        x, y, z = player_pos
        x -= player_speed * sin(radians(player_angle))
        y -= player_speed * cos(radians(player_angle))
        
        x = max(-GRID_LENGTH+75, min(GRID_LENGTH-75, x))
        y = max(-GRID_LENGTH+75, min(GRID_LENGTH-75, y))
        player_pos = (x, y, z)
    
    if key == b'a':
        player_angle = (player_angle + rotate_speed) % 360
    
    if key == b'd':
        player_angle = (player_angle - rotate_speed) % 360
    
    if key == b'c':  
        cheat = not cheat
       
    if key == b'v' and cheat:
        first_person = not first_person
    
    if key == b'v' and not cheat:
        gun_follow_camera = not gun_follow_camera
   
    if key == b'r':
        restart()


def restart():
    global player_pos, player_angle, life, score, bullet_missed, enemy_pos, bullets, game_over, cheat
    cheat = False
    player_pos = (0, 0, 0)
    player_angle = 0
    life = 5
    score = 0
    bullet_missed = 0
    enemy_pos.clear()
    bullets.clear()
    initialize_enemies()
    game_over = False


def mouseListener(button, state, x, y):
    global first_person, gun_follow_camera
    # Left mouse button fires a bullet
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        fire_bullet()
    # Right mouse button toggles camera tracking mode
    if button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
        first_person = not first_person


def setupCamera():
    glMatrixMode(GL_PROJECTION)  
    glLoadIdentity()  
    gluPerspective(fovY, 1.25, 0.1, 1500)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    global camera_angle, camera_height, camera_distance, player_pos, player_angle, first_person
    if first_person:
        # First-person mode: camera at player position, looking forward 
        px, py, pz = player_pos
        cam_offset = 170  
        cam_x = px + cam_offset * sin(radians(player_angle))
        cam_y = py + cam_offset * cos(radians(player_angle))
        cam_z = pz + 80  # Height offset for eye level
        look_x = px + 100 * sin(radians(player_angle))
        look_y = py + 100 * cos(radians(player_angle))
        look_z = cam_z
        gluLookAt(cam_x, cam_y, cam_z, look_x, look_y, look_z, 0, 0, 1)
    else:
        # Third-person mode: camera rotates around the center
        cam_x = camera_distance * sin(radians(camera_angle))
        cam_y = camera_distance * cos(radians(camera_angle))
        cam_z = camera_height
        gluLookAt(cam_x, cam_y, cam_z, 0, 0, 0, 0, 0, 1)


def idle():
    """
    Idle function that runs continuously:
    - Triggers screen redraw for real-time updates.
    """
    update_bullets_and_enemies()
    glutPostRedisplay()

def cheat_function():
    global player_angle, enemy_pos, player_pos
    player_angle = (player_angle + 5) % 360
    px, py, _ = player_pos
    for enemy in enemy_pos:
        ex, ey, ez = enemy['position']
        angle_to_enemy = degrees(atan2(ex-px, ey-py)) % 360
        if abs((player_angle - angle_to_enemy + 180) % 360 - 180) < 10:
            fire_bullet()
            break

        

def showScreen():
    """
    Display function to render the game scene:
    - Clears the screen and sets up the camera.
    - Draws everything of the screen
    """
    # Clear color and depth buffers
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()  # Reset modelview matrix
    glViewport(0, 0, 1000, 800)  # Set viewport size

    setupCamera()  # Configure camera perspective

    glBegin(GL_QUADS)
    for x in range(-GRID_LENGTH, GRID_LENGTH, 100):
        for y in range(-GRID_LENGTH, GRID_LENGTH, 100):
            tile_x = (x // 100)
            tile_y = (y // 100)
            if (tile_x + tile_y) % 2 == 0:
                glColor3f(1, 1, 1)      # white
            else:
                glColor3f(0.7, 0.5, 0.95)  # pink color

            glVertex3f(x, y, 0)
            glVertex3f(x + 100, y, 0)
            glVertex3f(x + 100, y + 100, 0)
            glVertex3f(x, y + 100, 0)
    glEnd()

    # Drawing the walls of the game
    wall_height = 100
    glBegin(GL_QUADS)
    
    # Cyan color / top Wall
    glColor3f(0, 1, 1)  
    glVertex3f(-GRID_LENGTH, -GRID_LENGTH, 0)
    glVertex3f(GRID_LENGTH, -GRID_LENGTH, 0)
    glVertex3f(GRID_LENGTH, -GRID_LENGTH, wall_height)
    glVertex3f(-GRID_LENGTH, -GRID_LENGTH, wall_height)
    
    # red color / bottom Wall
    glColor3f(1, 0, 0)  
    glVertex3f(-GRID_LENGTH, GRID_LENGTH, 0)
    glVertex3f(GRID_LENGTH, GRID_LENGTH, 0)
    glVertex3f(GRID_LENGTH, GRID_LENGTH, wall_height)
    glVertex3f(-GRID_LENGTH, GRID_LENGTH, wall_height)
    
    # Blue color / left Wall
    glColor3f(0, 0, 1)  
    glVertex3f(-GRID_LENGTH, GRID_LENGTH, 0)
    glVertex3f(-GRID_LENGTH, -GRID_LENGTH, 0)
    glVertex3f(-GRID_LENGTH, -GRID_LENGTH, wall_height)
    glVertex3f(-GRID_LENGTH, GRID_LENGTH, wall_height)
    
    # green color / right Wall
    glColor3f(0, 1, 0)  
    glVertex3f(GRID_LENGTH, GRID_LENGTH, 0)
    glVertex3f(GRID_LENGTH, -GRID_LENGTH, 0)
    glVertex3f(GRID_LENGTH, -GRID_LENGTH, wall_height)
    glVertex3f(GRID_LENGTH, GRID_LENGTH, wall_height)

    glEnd()
    
    # Display game info text at a fixed screen position
    draw_text(10, 770, f"Player Life Remaining: {life}")
    draw_text(10, 740, f"Game Score: {score}")
    draw_text(10, 710, f"Player Bullet Missed: {bullet_missed}")

    # Check if the game is over
    if game_over:
        draw_text(400, 750, "GAME OVER", font=GLUT_BITMAP_HELVETICA_18)
        draw_text(400, 710, "Press R to Restart", font=GLUT_BITMAP_HELVETICA_18)
        drawPlayer()
    else:
        draw_shapes()

    # Swap buffers for smooth rendering (double buffering)
    glutSwapBuffers()


# Main function to set up OpenGL window and loop
def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)  # Double buffering, RGB color, depth test
    glutInitWindowSize(1000, 800)  # Window size
    glutInitWindowPosition(0, 0)  # Window position
    wind = glutCreateWindow(b"3D OpenGL Intro")  # Create the window

    glutDisplayFunc(showScreen)  # Register display function
    glutKeyboardFunc(keyboardListener)  # Register keyboard listener
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)  # Register the idle function to move the bullet automatically

    glutMainLoop()  # Enter the GLUT main loop

if __name__ == "__main__":
    main()
