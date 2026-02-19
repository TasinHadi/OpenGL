from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

import time
import random

width = 800
height = 600
diamond_size = 15
catcher_h = 90
catcher_w = 15

# Midpoint Line Drawing & Eight-Way Symmetry 
def draw_points(x, y):
    glPointSize(2)
    glBegin(GL_POINTS)
    glVertex2f(x, y)
    glEnd()

def find_zone(x0, y0, x1, y1):
    dx = x1 - x0
    dy = y1 - y0
    if abs(dx) >= abs(dy):
        if dx >= 0 and dy >= 0:
            zone= 0
        elif dx < 0 and dy >= 0:
            zone= 3
        elif dx < 0 and dy < 0:
            zone= 4
        else:
            zone= 7
    else:
        if dx >= 0 and dy >= 0:
            zone= 1
        elif dx < 0 and dy >= 0:
            zone= 2
        elif dx < 0 and dy < 0:
            zone= 5
        else:
            zone= 6
    return zone

def convert_to_zone0(x, y, zone):
    if zone == 0:
        return x, y
    elif zone == 1:
        return y, x
    elif zone == 2:
        return y, -x
    elif zone == 3:
        return -x, y
    elif zone == 4:
        return -x, -y
    elif zone == 5:
        return -y, -x
    elif zone == 6:
        return -y, x
    elif zone == 7:
        return x, -y

def convert_from_zone0(x, y, zone):
    if zone == 0:
        return x, y
    elif zone == 1:
        return y, x
    elif zone == 2:
        return -y, x
    elif zone == 3:
        return -x, y
    elif zone == 4:
        return -x, -y
    elif zone == 5:
        return -y, -x
    elif zone == 6:
        return y, -x
    elif zone == 7:
        return x, -y

def midpoint(zone, x0, y0, x1, y1):
    dx = x1 - x0
    dy = y1 - y0
    d = (2 * dy) - dx
    E = 2 * dy
    NE = 2 * (dy - dx)
    x, y = x0, y0
    while x <= x1:
        x_og, y_og = convert_from_zone0(x, y, zone)
        draw_points(x_og, y_og)
        if d <= 0:
            x += 1
            d += E
        else:
            x += 1
            y += 1
            d += NE

def draw_line(x0, y0, x1, y1):
    zone = find_zone(x0, y0, x1, y1)
    x0_convert, y0_convert = convert_to_zone0(x0, y0, zone)
    x1_convert, y1_convert = convert_to_zone0(x1, y1, zone)
    midpoint(zone, x0_convert, y0_convert, x1_convert, y1_convert)


# AABB Collision
class AABB:
    def __init__(self, x, y, width, height):
        self.x, self.y, self.width, self.height = x, y, width, height

def has_collided(box1, box2):
    return (box1.x < box2.x + box2.width and
            box1.x + box1.width > box2.x and
            box1.y < box2.y + box2.height and
            box1.y + box1.height > box2.y)


# Drawing Functions 
def draw_diamond(x, y, size):
    glColor3f(*game.diamond_color)
    draw_line(x, y + size, x + size, y)
    draw_line(x + size, y, x, y - size)
    draw_line(x, y - size, x - size, y)
    draw_line(x - size, y, x, y + size)

def draw_catcher(x, y, width, height):
    glColor3f(1, 0, 0) if game.game_over else glColor3f(1, 1, 1)
    half = width // 2
    draw_line(x - half + 15, y, x - half, y + height)
    draw_line(x - half, y + height, x + half, y + height)
    draw_line(x + half, y + height, x + half - 15, y)
    draw_line(x - half + 15, y, x + half - 15, y)

def restart(x, y, size):
    glColor3f(0, 0.8, 0.8)
    half = size // 2
    draw_line(x - half, y, x, y + half)
    draw_line(x - half, y, x, y - half)
    draw_line(x - half, y, x + half, y)

def play_pause(x, y, size):
    glColor3f(1, 0.6, 0)
    half = size // 2
    if game.paused:
        draw_line(x - half, y - half, x - half, y + half)
        draw_line(x - half, y + half, x + half, y)
        draw_line(x + half, y, x - half, y - half)
    else:
        draw_line(x - 8, y - half, x - 8, y + half)
        draw_line(x + 8, y - half, x + 8, y + half)

def cross(x, y, size):
    glColor3f(1, 0, 0)
    half = size // 2
    draw_line(x - half, y - half, x + half, y + half)
    draw_line(x - half, y + half, x + half, y - half)


# Game logic
class Game:
    def __init__(self):
        self.score = 0
        self.game_over = False
        self.paused = False
        self.catcher_x = width // 2
        self.diamond_x = random.randint(50, width - 50)
        self.diamond_y = height - 100
        self.diamond_speed = 100
        self.diamond_color = self.random_color()
        
    def random_color(self):
        colors = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0), (1, 0, 1), (0, 1, 1)]
        return random.choice(colors)
    
    def restart_game(self):
        self.score = 0
        self.game_over = False
        self.paused = False
        self.catcher_x = width // 2
        self.diamond_x = random.randint(50, width - 50)
        self.diamond_y = height - 100
        self.diamond_speed = 100
        self.diamond_color = self.random_color()
        print("Starting Over")
    
    def spawn_new_diamond(self):
        self.diamond_x = random.randint(50, width - 50)
        self.diamond_y = height - 100
        self.diamond_speed += 20
        self.diamond_color = self.random_color()

game = Game()
last_time = time.time()


# Collision Check 
def check_collision():
    diamond_box = AABB(game.diamond_x - diamond_size, game.diamond_y - diamond_size, diamond_size * 2, diamond_size * 2)
    catcher_box = AABB(game.catcher_x - catcher_h//2, 40, catcher_h, catcher_w)
    return has_collided(diamond_box, catcher_box)


# Button Click 
def click_button(mouse_x, mouse_y, button_x, button_y, size):
    half = size // 2
    return (button_x - half <= mouse_x <= button_x + half and
            button_y - half <= mouse_y <= button_y + half)


# Display 
def display():
    glClear(GL_COLOR_BUFFER_BIT)
    restart(80, height - 60, 40)
    play_pause(width // 2, height - 60, 40)
    cross(width - 80, height - 60, 40)
    if not game.game_over:
        draw_diamond(game.diamond_x, game.diamond_y, diamond_size)
    draw_catcher(game.catcher_x, 40, catcher_h, catcher_w)
    glutSwapBuffers()


# Update 
def update():
    global last_time
    if not game.paused and not game.game_over:
        current_time = time.time()
        dt = current_time - last_time
        last_time = current_time
        game.diamond_y -= game.diamond_speed * dt
        if check_collision():
            game.score += 1
            print(f"Score: {game.score}")
            game.spawn_new_diamond()
        elif game.diamond_y < 20:
            game.game_over = True
            print(f"Game Over! Final Score: {game.score}")
    glutPostRedisplay()


# keyboard & mouse Controls 
def keyboard_special(key, x, y):
    if not game.game_over and not game.paused:  # catcher won't move if paused
        if key == GLUT_KEY_LEFT:
            game.catcher_x = max(catcher_h//2, game.catcher_x - 30)
        elif key == GLUT_KEY_RIGHT:
            game.catcher_x = min(width - catcher_h//2, game.catcher_x + 30)


def mouse_click(button, state, x, y):
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        mouse_x = x
        mouse_y = height - y
        if click_button(mouse_x, mouse_y, 80, height - 60, 40):
            game.restart_game()
        elif click_button(mouse_x, mouse_y, width // 2, height - 60, 40):
            game.paused = not game.paused
        elif click_button(mouse_x, mouse_y, width - 80, height - 60, 40):
            print(f"Goodbye! Final Score: {game.score}")
            glutLeaveMainLoop()


def animate():
    update()

def init():
    glClearColor(0, 0, 0, 1)
    glPointSize(2)
    gluOrtho2D(0, width, 0, height)

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB)
    glutInitWindowSize(width, height)
    glutInitWindowPosition(100, 100)
    glutCreateWindow(b"Catch the Diamonds!")
    init()
    glutDisplayFunc(display)
    glutSpecialFunc(keyboard_special)
    glutMouseFunc(mouse_click)
    glutIdleFunc(animate)  
    glutMainLoop()

main() 