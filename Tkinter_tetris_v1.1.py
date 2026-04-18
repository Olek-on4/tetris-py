from __future__ import annotations

import tkinter
from tkinter_extension import Message
from typing import Callable
from random import randrange
from time import sleep

Rect = tuple[int, int]
PieceInfo = list[int | list[int] | Rect]
PieceData = tuple[list[int], Rect]
PieceCatalog = tuple[int | PieceData, ...]
ControlScheme = tuple[str, str, str, str, str, str, str]

def new_color() -> str:
    '''Generate a new color'''
    col = ""
    for _ in range(2):
        col = col + "{:02}".format((randrange(2)) * "f")

    r = randrange(3)
    col = col[:r * 2] + "f0" + col[r * 2:]
    print(col)
    col = "#" + col
    return col

# def get_color(map: tuple[int], canvas: tkinter.Canvas):
#     for id in map:
#         if id != 0:
#             return canvas.itemcget(id, "fill")

class Controller():
    '''Responsible for controlling pieces and squares on the map'''
    __slots__ = ("game", "res", "side", "map", "active", "on_hold", "next", "mid")
    def __init__(self, res: Rect, block: int, game):
        self.game = game
        self.res = res
        self.side = block
        self.map = [0 for _ in range(res[0] * res[1])]
        self.active = [0, 0, 0, (0, 0)]
        self.on_hold = None #(piece, res)
        self.next = None #(piece, res)
        self.mid = res[0]//2

    @staticmethod
    def to_ind(coords: tuple[int, int, int]) -> int:
        '''Calculate map index from coordinates'''
        return coords[1] * coords[2] + coords[0]

    def for_each_block(self, info: PieceInfo, func: Callable[..., bool | None], *args):
        '''Apply a function to every square of the piece and return the result if any'''
        x = info[0]
        y = info[1]

        piece = info[2]
        
        sY = info[3][1]
        sX = info[3][0]
        row = self.res[0]

        for i in range(sY):
            for j in range(sX):

                if piece[i * sX + j] != 0:
                    res = func((x + j, y + i, row), i * sX + j, *args)
                    if res is not None:
                        return res
        return True

    def is_empty(self, coords: tuple[int, int, int], _, dx: int, dy: int) -> bool | None:
        '''Check if the area does not contain any squares'''
        if self.map[(coords[1] + dy) * coords[2] + coords[0] + dx] != 0:
            return False

    def make_square(self, coords: tuple[int, int, int], loc: int, localMap: list[int] | None, col: str):
        '''Create visual representation of active piece'''
        canv = self.game.canvas
        a = self.side

        Id = canv.create_rectangle(coords[0] * a, coords[1] * a, coords[0] * a + a, coords[1] * a + a, fill=col)
        if localMap is not None:
            localMap[loc] = Id
        else:
            self.map[self.to_ind(coords)] = Id

    def move_square(self, coords: tuple[int, int, int], loc: int, localMap: list[int] | None, dx: int, dy: int):
        '''Move a square on the map or in the active piece by a designated offset'''
        canv = self.game.canvas
        Id = 0

        if localMap is None: #Check if global
            ind = self.to_ind(coords)
            Id = self.map[ind]
            self.map[ind] = 0
            self.map[ind + dy * coords[2] + dx] = Id

        else:
            Id = localMap[loc]
        canv.move(Id, self.side * dx, self.side * dy)

    def del_square(self, coords: tuple[int, int, int], loc: int, localMap: list[int] | None):
        '''Delete the visual representation and id of a square on the map or in the active piece'''
        canv = self.game.canvas

        if localMap is None: #Check if global
            ind = self.to_ind(coords)
            canv.delete(self.map[ind])
            self.map[ind] = 0

        else:
            canv.delete(localMap[loc])
            localMap[loc] = 1

    def replace_id(self, coords: tuple[int, int, int], loc: int, localMap: list[int]):
        '''Copy the active piece's ids to the map'''
        self.map[self.to_ind(coords)] = localMap[loc]

    def move(self, dx: int, dy: int, auto_spawn: bool=True):
        '''Move the active piece by <dx> on the x axis and by <dy> on the y axis'''
        x = self.active[0]
        y = self.active[1]

        if dx != 0:
            newX = x + dx
            # Check if in bounds
            if newX + self.active[3][0] > self.res[0] or newX < 0:
                return False
            
            if not self.for_each_block(self.active, self.is_empty, dx, 0):
                return False
            self.active[0] = newX

        if dy > 0:
            newY = y + dy

            # Check if in bounds
            if newY + self.active[3][1] > self.res[1] or not self.for_each_block(self.active, self.is_empty, 0, dy):
                self.for_each_block(self.active, self.replace_id, self.active[2])
                lines = 0

                for i in range(y, y + self.active[3][1], 1):
                    clear = True
                    for j in range(self.res[0]):
                        if self.map[i*self.res[0] + j] == 0:
                            clear = False

                    if clear:
                        info = [0, i, self.map[i * self.res[0]: (i+1) * self.res[0]], (self.res[0], 1)]
                        self.for_each_block(info, self.del_square, None)
                        lines = lines + 1

                        for j in range(i-1, -1, -1):
                            info[1] = j
                            info[2] = self.map[j * self.res[0]: (j+1) * self.res[0]]
                            self.for_each_block(info, self.move_square, None, 0, 1)

                if lines > 0:
                    self.game.player.update_score(lines * 10 * self.res[0] * self.game.diff)
                    if self.game.player.score >= self.game.player.spd * 1200 // self.game.diff:
                        self.game.player.spd *= 1.5
                
                if auto_spawn:
                    suc = self.spawn()
                    return suc
                return False
            
            else:
                self.active[1] = newY

        self.for_each_block(self.active, self.move_square, self.active[2], dx, dy)
        #print("Moved by: ", dx, dy)
        return True
    
    def set_next(self, piece: PieceData):
        coords = self.game.hold_in
        x = coords[0] / self.side - piece[1][0] / 2
        y = (coords[1] / self.side + 7) - piece[1][1] / 2
        info = [x, y, piece[0], piece[1]]

        self.for_each_block(info, self.make_square, piece[0], new_color())
        self.next = piece

    def spawn(self, piece: PieceData | None = None):
        '''Spawn a new active piece with structure described by <piece>'''
        custom = piece is not None
        if custom:
            suc = True
            while suc:
                sleep(0.05)
                suc = self.move(0, 1, False)
        else:
            piece = self.next
            if piece is None:
                return False

        info = [self.mid, 0, piece[0], piece[1]]
        if self.for_each_block(info, self.is_empty, 0, 0):
            self.active = info

            if custom:
                self.for_each_block(info, self.make_square, piece[0], new_color())
            else:
                self.for_each_block(info, self.move_square, info[2], -(self.res[0] + 3 - self.mid - self.active[3][0] / 2), -12 + self.active[3][1] / 2)
                self.set_next(self.game.choose_piece())
            #print("Spawned new piece")
            return True
        return False

    def rotate(self, dr: int):
        '''Rotate the active piece |<dr>| times, positive value rotating to the left'''
        neg = int(dr < 0)
        dr = (neg * -2 + 1) * dr
        dr = dr % 4

        if dr != 0:
            piece = self.active[2]
            res = self.active[3]

            for _ in range(dr):
                res = (res[1], res[0])
                newMap = [[] for _ in range(res[1])]
                
                for k in range(res[0]):
                    for j in range(res[1]):
                        block = 0
                        if neg:
                            block = ((res[0] - 1) - k) * res[1] + j
                        else:
                            block = k * res[1] + (res[1] - 1 - j)
                        newMap[j].append(piece[block])
                
                piece = []
                for lst in newMap:
                    piece = piece + lst
            
            if dr % 2 == 1 and (self.active[0] + res[0] > self.res[0]
                                or not self.for_each_block([self.active[0], self.active[1], piece, res],
                                    self.is_empty, 0, 0)):
                return False

            x = self.active[0]
            y = self.active[1]
            for i in range(res[1]):
                for j in range(res[0]):
                    
                    block = piece[i * res[0] + j]
                    if block != 0:
                        self.game.canvas.moveto(block, (x + j) * self.side - 1, (y + i) * self.side - 1)

            self.active[2] = piece
            self.active[3] = res
            #print("Rotated active piece by: ", (neg * -2 + 1) * dr)
        return True

    def to_hold(self, info: PieceInfo):
        '''Calculate the vector from the current piece's coordinates to the help piece coordinates'''
        return (self.game.hold_in[0] - round((self.active[0] + info[3][0] / 2) * self.side),  self.game.hold_in[1] - round((self.active[1] + info[3][1] / 2) * self.side))

    def hold(self):
        '''Puts the active piece on hold to be used when putting another piece on hold next time'''
        if self.on_hold != None:
            res_hold = self.on_hold[1]
            if res_hold[0] + self.active[0] > self.res[0] or res_hold[1] + self.active[1] > self.res[1]:
                return False

            info = [self.active[0], self.active[1], self.on_hold[0], res_hold]
            if not self.for_each_block(info, self.is_empty, 0, 0): #Check if piece can be replaced
                return False

            trans = self.to_hold(self.active)
            for id in self.active[2]:
                if id != 0:
                    self.game.canvas.move(id, trans[0], trans[1])

            trans = self.to_hold(info)
            for id in info[2]:
                if id != 0:
                    self.game.canvas.move(id, -trans[0], -trans[1])

            self.on_hold = (self.active[2], self.active[3])
            self.active = info
            #print("Swapped pieces. Translated by:", trans[0], trans[1])
        else:

            info = self.active
            trans = self.to_hold(info)
            for id in info[2]:
                if id != 0:
                    self.game.canvas.move(id, trans[0], trans[1])
            self.on_hold = (self.active[2].copy(), self.active[3])
            #print("Put a piece on hold. Translated by:", trans[0], trans[1])
            suc = self.spawn()
            if not suc:
                self.game.stop("Invalid spawn")
                return False

        self.game.next_in = self.game.next_in + 0.100
        return True


class Tetris():
    '''Main game class. Responsible for controlling the <Controller> and giving the player access to controls'''
    __slots__ = ("pieces", "hold_in", "player", "canvas", "control", "next_in", "halt", "queue", "diff", "FPS", "mes_board")
    def __init__(self, res: Rect, lst: PieceCatalog, side: int, can: tkinter.Canvas, hold: Rect, diff: int, fps: int):
        self.pieces = lst
        self.hold_in = hold
        self.player = None
        self.canvas = can
        self.control = Controller(res, side, self)
        self.next_in = 0
        self.halt = False
        self.queue = []
        self.diff = diff
        self.FPS = round(1/fps, 6)
        self.mes_board = Message(can, res[0] * side//2, res[1] * side//2, fps) # Invisible canvas object displaying messages with color animations
        self.mes_board.set_keyframes(500, "#0f0f0f")

    def add_player(self, plr):
        '''Assigns a player <plr> to self and self to a player's game attribute'''
        self.player = plr
        plr.game = self
    
    def process_in(self, event: tkinter.Event):
        '''Accepts canvas bound input and according to given controls queues up active piece control actions'''
        assert self.player is not None
        key = event.keysym
        if len(key) > 1:
            key = "<" + key + ">"

        ind = self.player.ctrls.index(key)
        if ind < 3:
            self.queue.append((self.control.move, ind - 1, ind % 2))
        elif ind < 5:
            self.queue.append((self.control.rotate, 1 - 2 * (ind - 3)))
        elif ind == 5:
            self.queue.append(self.control.hold)
        else:
            self.queue.append(self.pause)
        #print("Pressed key:", key)

    def bind_ctrl(self, pause=False):
        '''Binds player's controls to canvas to be processed as input'''
        bind = self.canvas.bind_all
        ctrls = self.player.ctrls
        for i in range(6+int(pause)):
            bind(ctrls[i], self.process_in)

    def unbind_ctrl(self):
        '''Unbinds player's controls from being processed'''
        unbind = self.canvas.unbind_all
        ctrls = self.player.ctrls
        for i in range(6):
            unbind(ctrls[i])
    
    def give_time(self):
        '''Calculates and saves time for the next lowering of the active piece'''
        self.next_in = round(2 / self.player.spd, 6)
    
    def choose_piece(self):
        '''Chooses a random piece from given pieces at start'''
        piece = self.pieces[randrange(1, self.pieces[0]+1)]
        return (piece[1].copy(), (piece[0], len(piece[1])//piece[0]))

    def resume(self):
        '''Lowers the active piece in intervals and executes queued up control actions'''
        while not self.halt:
            sleep(self.FPS)
            self.next_in = self.next_in - self.FPS

            for item in self.queue:
                if type(item) == tuple:
                    fun = item[0]
                    fun(*item[1:])
                else:
                    item()
            self.queue = []

            if self.next_in < self.FPS:
                suc = self.control.move(0, 1)
                if not suc:
                    self.stop("You lost")
                    return
                #print("Lowered piece automatically")
                self.give_time()
            self.canvas.update()

    def pause(self, _ = None):
        '''Stops the game, displays the pause message, binds and unbinds controls accordingly'''
        if self.halt:
            self.give_time()
            self.mes_board.erase()
            self.canvas.unbind_all(self.player.ctrls[6])
            self.bind_ctrl(True)
            self.halt = False
            self.resume()
        else:
            self.unbind_ctrl()
            self.halt = True
            self.canvas.bind_all(self.player.ctrls[6], self.pause)
            self.mes_board.display_message("Paused", ("OCR A Extended", 40), "#c0c0c0", True)
    
    def start(self, plr=None):
        '''Initiates the game and spawns the first active piece'''
        if plr is not None:
            self.add_player(plr)
        self.give_time()

        self.control.set_next(self.choose_piece())
        suc = self.control.spawn()
        if not suc:
            self.stop("Invalid start")
        else:
            self.bind_ctrl(True)
            self.resume()
    
    def stop(self, mes: str):
        '''Stops game cycle like <pause> and displays the reason of game's end <mes>'''
        self.unbind_ctrl()
        self.halt = True
        self.canvas.unbind_all(self.player.ctrls[6])
        self.mes_board.set_keyframes(1500, "#f00000")
        self.mes_board.display_message(mes, ("OCR A Extended", 40), "#f0f0f0", True)


#IdNum = 0
class Player():
    '''Player class housing player-specific attributes'''
    __slots__ = ("score", "score_id", "game", "spd", "ctrls")
    def __init__(self, ctrls: ControlScheme, score_id: int):
        self.score = 0
        self.score_id = score_id
        #self.Id = IdNum
        #IdNum = IdNum + 1
        self.game = None
        self.spd = 1
        self.ctrls = ctrls

    def update_score(self, val: int):
        '''Updates game's score by <val>'''
        self.score = self.score + val
        assert self.game is not None
        self.game.canvas.itemconfigure(self.score_id, text="Score:\n{}".format(self.score))
        #print("Changed score by:", val)


def New_game(ctrl: ControlScheme | None = None, pieces: PieceCatalog | None = None, res: Rect = (10, 20), diff: int = 1, FPS: int = 60):
    '''Sets up a game object with given parameters or with default values'''
    ctrl = ctrl or ("a", "s", "d", "q", "e", "f", "<Escape>")
    pieces = pieces or (8, (2, [1, 0,
                                1, 0,
                                1, 1]),

                            (2, [1, 1,
                                 1, 1]),

                            (2, [1, 1,
                                 1, 0,
                                 1, 0]),

                            (1, [1, 1, 1, 1]),

                            (3, [1, 1, 1,
                                 0, 1, 0]),

                            (3, [0, 1, 1,
                                1, 1, 0]),

                            (3, [1, 1, 0,
                                 0, 1, 1]),

                            (5, [1, 0, 1, 1, 1,
                                  1, 0, 1, 0, 0,
                                  1, 1, 1, 1, 1,
                                  0, 0, 1, 0, 1,
                                  1, 1, 1, 0, 1]))

    side = 30
    pX = res[0] * side
    pY = res[1] * side
    root = tkinter.Tk()
    root.geometry("{}x{}+{}+{}".format(pX + 6 * side, pY, 
                                       round(root.winfo_screenwidth() / 2 - pX / 2 - 3 * side), round(root.winfo_screenheight() / 2 - pY / 2)))
    root.title("Tkinter Tetris")
    root.iconbitmap("t_icon.ico")
    canvas = tkinter.Canvas(width=pX + 6 * side, height=pY, bg="#ffffff")
    canvas.pack(anchor="center", expand=True)

    seg = 3 * side // 2
    canvas.create_line(pX + 2, 0, pX + 2, pY, width=3)
    # Hold text and bounding box
    score_id = canvas.create_text(pX + 2 * seg, seg, text="Score: 0", font=("OCR A Extended", 22), anchor="center")
    canvas.create_rectangle(pX + side, 2 * seg, pX + 5 * side, 2 * seg + 4 * side, width=3, dash=(20, 20))
    hold_coords = (pX + 2 * seg, 2 * seg + 2 * side)
    # Next text and bounding box
    canvas.create_text(pX + 2 * seg, 5 * seg + side, text="Next:", font=("OCR A Extended", 22), anchor="center")
    canvas.create_rectangle(pX + side, 6 * seg + side, pX + 5 * side, 6 * seg + 5 * side, width=3, dash=(20, 20))
    canvas.update()

    plr1 = Player(ctrl, score_id)
    game = Tetris(res, pieces, side, canvas, hold_coords, diff, FPS)
    game.add_player(plr1)
    return game

if __name__ == "__main__":
    game1 = New_game(None, None, (20,10), 5, 80)
    game1.start()

# >>> Made by Olek <3
