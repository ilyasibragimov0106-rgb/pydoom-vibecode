"""Billboard sprite base class plus pickups and decorative torches."""
from settings import (PLAYER_MAX_HEALTH, MAX_BULLETS, MAX_SHELLS,
                      MEDKIT_HEALTH, BULLETS_PICKUP, SHELLS_PICKUP)
from textures import SPRITES


class SpriteObject:
    """Anything drawn as a billboard: scale is a fraction of wall height,
    z is the height of the sprite bottom above the floor (world units)."""

    def __init__(self, game, x, y, scale=1.0, z=0.0, emissive=False):
        self.game = game
        self.x = x
        self.y = y
        self.scale = scale
        self.z = z
        self.emissive = emissive
        self.dead = False

    def current_frame(self):
        raise NotImplementedError


_PICKUP_MESSAGES = {
    'medkit': "PICKED UP A MEDIKIT",
    'bullets': "PICKED UP A BOX OF BULLETS",
    'shells': "PICKED UP A BOX OF SHOTGUN SHELLS",
}


class Pickup(SpriteObject):
    def __init__(self, game, kind, x, y):
        super().__init__(game, x, y, scale=0.36, z=0.02)
        self.kind = kind
        self.message = _PICKUP_MESSAGES[kind]

    def current_frame(self):
        return SPRITES[self.kind][0]

    def try_pickup(self, player):
        if self.kind == 'medkit':
            if player.health >= PLAYER_MAX_HEALTH:
                return False
            player.add_health(MEDKIT_HEALTH)
            return True
        if self.kind == 'bullets':
            if player.bullets >= MAX_BULLETS:
                return False
            player.add_bullets(BULLETS_PICKUP)
            return True
        if player.shells >= MAX_SHELLS:
            return False
        player.add_shells(SHELLS_PICKUP)
        return True


class Torch(SpriteObject):
    def __init__(self, game, x, y):
        super().__init__(game, x, y, scale=1.0, z=0.0, emissive=True)
        self.anim_t = 0.0

    def current_frame(self):
        return SPRITES['torch'][int(self.anim_t * 9) % 2]

    def update(self, dt):
        self.anim_t += dt
