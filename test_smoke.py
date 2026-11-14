"""Headless smoke test: boots the whole game with dummy SDL drivers, fires
weapons, exercises movement/collision, states and the AI, and prints timing.

Run:  python test_smoke.py
"""
import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import math
import time

import pygame

from npc import Rocket
from settings import MOUSE_SENS

import levelgen
import main as game_mod


def place_in_front(g, npc, dist):
    """Teleport npc into the player's view at `dist` tiles with clear LOS."""
    p = g.player
    for ang in (0.0, math.pi / 2, math.pi, -math.pi / 2):
        tx = p.x + math.cos(ang) * dist
        ty = p.y + math.sin(ang) * dist
        if not g.map.is_wall(tx, ty) and g.map.line_of_sight(p.x, p.y, tx, ty):
            npc.x, npc.y = tx, ty
            p.angle = ang
            return True
    return False


def main():
    g = game_mod.Game()
    g.new_game()
    assert g.state == "play"
    p = g.player

    # --- mouse look (MOUSEMOTION events must rotate the camera) -------------
    a0 = p.angle
    g.handle_event(pygame.event.Event(pygame.MOUSEMOTION, rel=(120, 0)))
    g.handle_event(pygame.event.Event(pygame.MOUSEMOTION, rel=(-40, 0)))
    assert abs((p.angle - a0) - 80 * MOUSE_SENS) < 1e-9, "mouse look is dead"
    g.paused = True
    g.handle_event(pygame.event.Event(pygame.MOUSEMOTION, rel=(500, 0)))
    assert abs(p.angle - a0 - 80 * MOUSE_SENS) < 1e-9, "camera turned while paused"
    g.paused = False
    print("mouse look ok")
    assert not g.map.is_wall(p.x, p.y), "player spawned inside a wall"

    # --- weapon kills an npc placed right in front of the player -----------
    for n in g.npcs:
        n.health = 9999
        n.x, n.y = 30.0, 30.0            # park everyone out of the way
    npc = g.npcs[0]
    npc.health = 60
    npc.x, npc.y = p.x + 2.5, p.y
    npc.state = 'idle'
    p.angle = 0.0                      # square up to the target
    shots = 0
    while npc.alive and shots < 40:
        g.weapons.cooldown = 0.0
        g.weapons.fire()
        shots += 1
    assert not npc.alive, f"npc still alive after {shots} shots"
    assert g.kills >= 1
    print(f"pistol killed test npc in {shots} shots")

    # --- movement & wall collision ------------------------------------------
    g.new_game()
    p = g.player
    x0 = p.x
    p.move(2.0, 0.0)
    assert p.x <= x0 + 2.0 + 1e-6
    for _ in range(20):
        p.move(0.5, 0.0)
    assert p.x < 7.0 - 0.28 + 1e-6, "player clipped through the east wall"
    assert not g.map.is_wall(p.x, p.y)
    print(f"movement ok, stopped at x={p.x:.2f} (wall at 7.0)")

    # --- render pipeline timing ----------------------------------------------
    frames = 150
    t0 = time.perf_counter()
    for _ in range(frames):
        p.health = 100                   # stay alive
        g.update(1 / 60)
        g.render()
    ms = (time.perf_counter() - t0) / frames * 1000
    print(f"avg frame: {ms:.2f} ms (~{1000 / ms:.0f} fps headless)")
    assert any(n.state != 'idle' for n in g.npcs), "no npc woke up near the player"

    # --- imp throws a fireball -------------------------------------------------
    p.x, p.y, p.angle = 2.5, 2.5, 0.0   # back to the open start room
    imp = g.npcs[0]
    imp.health = 60
    imp.state = 'chase'
    imp.attack_cd = 0.0
    imp.x, imp.y = p.x + 4.0, p.y
    g.projectiles.clear()
    threw = False
    for _ in range(120):
        imp.x, imp.y = p.x + 4.0, p.y    # keep it in sight range
        g.update(1 / 60)
        if g.projectiles:
            threw = True
            break
    assert threw, "imp never threw a fireball"
    print("imp fireball ok")

    # --- shotgun kill ------------------------------------------------------------
    g.new_game()
    p = g.player
    for n in g.npcs:
        n.health = 9999
        n.x, n.y = 30.0, 30.0
    npc = g.npcs[1]
    npc.health = 60
    npc.x, npc.y = p.x + 2.0, p.y
    p.shells = 20
    g.weapons.select(1)
    g.weapons.anim_t = 99.0
    shots = 0
    while npc.alive and shots < 20:
        g.weapons.cooldown = 0.0
        g.weapons.fire()
        shots += 1
    assert not npc.alive, "shotgun failed to kill npc"
    print(f"shotgun killed test npc in {shots} shots")

    # --- damage -> game over -> restart ---------------------------------------
    p.damage(500)
    assert g.state == "gameover"
    g.render()
    g.new_game()
    assert g.state == "play"

    # --- exit switch -> win ----------------------------------------------------
    ex = g.map.exit_cells[0]
    g.player.x, g.player.y = ex[0] - 1.0, ex[1]
    g.update(1 / 60)
    assert g.state == "win"
    g.render()

    # --- endless generation: next level is procedural --------------------------
    g.new_game(next_level=True)
    assert g.level == 2 and g.state == "play"
    assert g.map.exit_cells, "generated level has no exit switch"
    for n in g.npcs:
        n.health = 9999
        n.x, n.y = 40.0, 40.0
    npc = g.npcs[0]
    npc.health = 60
    assert place_in_front(g, npc, 2.5), "no open line of sight near the spawn"
    shots = 0
    while npc.alive and shots < 40:
        g.weapons.cooldown = 0.0
        g.weapons.fire()
        shots += 1
    assert not npc.alive, "pistol failed on a generated level"
    print(f"generated level 2 playable, npc killed in {shots} shots")

    # win it and descend to level 3
    ex = g.map.exit_cells[0]
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        fx, fy = ex[0] + dx, ex[1] + dy
        if not g.map.is_wall(fx, fy):
            break
    g.player.x, g.player.y = fx, fy
    g.update(1 / 60)
    assert g.state == "win"
    g.new_game(next_level=True)
    assert g.level == 3
    print("level chaining ok (2 -> 3)")

    # generation stress: 10 more levels must parse and validate
    for lvl in range(4, 14):
        rows = levelgen.generate_level(lvl, seed=1000 + lvl)
        m = game_mod.GameMap(rows)
        assert m.exit_cells and m.player_start
    print("generation stress ok (levels 4..13)")

    # --- menu -------------------------------------------------------------------
    g.state = "menu"
    g.render()

    # --- chainsaw kills up close -------------------------------------------------
    g.new_game()
    for n in g.npcs:
        n.health = 9999
        n.x, n.y = 40.0, 40.0
    npc = g.npcs[0]
    npc.health = 30
    assert place_in_front(g, npc, 1.0)
    g.weapons.select(2)
    ticks = 0
    while npc.alive and ticks < 200:
        g.weapons.cooldown = 0.0
        g.weapons.update(1 / 60, True)
        ticks += 1
    assert not npc.alive, "chainsaw failed to kill npc"
    print(f"chainsaw killed npc in {ticks} ticks")

    # --- plasma bolt flies and kills ---------------------------------------------
    npc = g.npcs[1]
    npc.health = 12                 # one plasma bolt (15 dmg) is enough
    assert place_in_front(g, npc, 4.0)
    g.weapons.select(3)
    p.cells = 50
    g.weapons.cooldown = 0.0
    g.weapons.fire()
    assert g.projectiles, "plasma did not spawn a bolt"
    died = False
    for _ in range(120):
        g.update(1 / 60)
        if not npc.alive:
            died = True
            break
    assert died, "plasma bolt never killed the npc"
    print("plasma bolt ok")

    # --- boss level 5: exit sealed until the cyberdemon dies ----------------------
    g.new_game(fresh=True)
    while g.level < 5:
        g.new_game(next_level=True)
    assert g.level == 5 and g.boss is not None, "no cyberdemon on level 5"
    assert g.map.exit_locked
    ex = g.map.exit_cells[0]
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        fx, fy = ex[0] + dx, ex[1] + dy
        if not g.map.is_wall(fx, fy):
            break
    g.player.x, g.player.y = fx, fy
    g.update(1 / 60)
    assert g.state == "play", "exit opened while the boss is alive"
    assert "SEALED" in g.message
    # the boss wakes up and attacks
    attacked = False
    for _ in range(240):
        g.player.health = 100
        g.update(1 / 60)
        if g.boss.attack_done or any(isinstance(pr, Rocket) for pr in g.projectiles):
            attacked = True
            break
    assert attacked, "cyberdemon never attacked"
    # kill the boss -> exit unlocks -> win
    assert place_in_front(g, g.boss, 2.5)
    g.boss.health = 5
    g.weapons.select(0)
    g.weapons.cooldown = 0.0
    g.weapons.fire()
    assert not g.boss.alive, "boss survived the shot"
    assert not g.map.exit_locked, "exit did not unlock after boss death"
    g.player.x, g.player.y = fx, fy
    g.update(1 / 60)
    assert g.state == "win"
    g.new_game(next_level=True)
    assert g.level == 6 and g.boss is None and not g.map.exit_locked
    print("boss gate ok (level 5 sealed -> kill -> win -> level 6)")

    # --- cheat codes -------------------------------------------------------------
    g.new_game()
    p = g.player
    p.bullets = 0
    p.shells = 0
    for k in "sadsadwwsad":
        g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=getattr(pygame, f"K_{k}")))
    assert g.cheat_ammo, "ammo cheat did not activate"
    g.weapons.select(0)
    g.weapons.anim_t = 99.0
    g.weapons.cooldown = 0.0
    g.weapons.fire()                # pistol with 0 bullets must still fire
    assert p.bullets == 0, "ammo was consumed despite the cheat"
    for k in "wswswsadadad":
        g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=getattr(pygame, f"K_{k}")))
    assert g.cheat_health, "health cheat did not activate"
    p.damage(50)
    assert p.health == 100, "god mode did not block damage"
    for k in "sadsadwwsad":         # toggles back off
        g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=getattr(pygame, f"K_{k}")))
    assert not g.cheat_ammo
    print("cheat codes ok")

    # --- AI soak: everyone fights for 10 simulated seconds ----------------------
    g.new_game()
    for _ in range(600):
        g.player.health = 100
        g.update(1 / 60)
        if g.state != "play":
            g.new_game()
    print(f"AI soak done, kills={g.kills}")
    print("SMOKE TEST OK")


if __name__ == "__main__":
    main()
