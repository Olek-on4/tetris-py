import tkinter

# Message communication
class Message():
    '''Message class for on customizable on-screen notifications.'''
    __slots__ = ("canvas", "coords", "displaying", "queue", "keyframes", "length", "fps", "id")

    def __init__(self, canvas: tkinter.Canvas, x: int, y: int, FPS: int):
        self.canvas = canvas
        self.coords = (x, y)

        self.displaying = False
        self.queue = None

        self.fps = 1000//FPS
        self.keyframes = None

        self.length = 0
        self.id = None

    def set_keyframes(self, *args: int|str):
        '''Set color keyframes for message transitions.'''
        l = len(args)
        
        if l % 2 != 0:
            raise ValueError("Invalid number of arguments for keyframes")
        for i in range(0, l, 2):
            if type(args[i]) != int:
                raise TypeError("Argument {} of keyframe is not an integer".format(i))
            
            if type(args[i+1]) != str or args[i+1][0] != "#" or len(args[i+1]) != 7:
                raise ValueError("Argument {} of keyframe is not a valid color string".format(i+1))
        self.keyframes = args
        self.length = l

    def trans(self, objId: int, col: str, n: int) -> bool:
        '''Transform mmessage color from last state to the next keyframe.'''
        last = self.canvas.itemcget(objId, "fill")
        last = (int(last[1:3], 16), int(last[3:5], 16), int(last[5:7], 16))
        col = (int(col[1:3], 16), int(col[3:5], 16), int(col[5:7], 16))
        inc = ((col[0] - last[0])/n, (col[1] - last[1])/n, (col[2] - last[2])/n)

        i = 0
        while i < n:
            if self.queue == None and self.id != None:
                last = (last[0] + inc[0],
                        last[1] + inc[1],
                        last[2] + inc[2])
                self.canvas.itemconfigure(objId, fill="#{:02x}{:02x}{:02x}".format(round(last[0]), round(last[1]), round(last[2])))
                self.canvas.update()
                self.canvas.after(self.fps)
            else:
                return False
            i = i + 1
        return True

    def display_message(self, mes: str, font: str|tuple[str|int], col: str = None, perm: bool = False):
        '''Display new message with starting font and color.'''
        if type(mes) != str or len(mes) < 1:
            raise ValueError("Parameter 0 of display_message is too short or not a string")

        if type(font) not in (str, tuple):
            raise TypeError("Parameter 1 of display_message is not a string or a tuple")

        if col:
            if (type(col) != str or col[0] != "#" or len(col) != 7):
                raise ValueError("Parameter 2 of display_message is not a valid color string")
        else:
            col = "#000000"
        
        if self.displaying:
            self.queue = (mes, font, col, perm)
        else:
            ind = self.canvas.create_text(self.coords[0], self.coords[1], text=mes, font=font, fill=col, anchor="center")
            self.id = ind
            self.displaying = True
            for i in range(0, self.length, 2):
                done = self.trans(ind, self.keyframes[i+1], self.keyframes[i]//self.fps)
                if not done:
                    break
            
            if perm:
                self.canvas.itemconfigure(ind, fill=self.keyframes[-1])
                self.displaying = False
                return ind
            self.canvas.delete(ind)
            self.canvas.update()

            if self.queue:
                temp = self.queue
                self.queue = None
                self.display_message(*temp)
            else:
                self.displaying = False
    
    def erase(self):
        self.canvas.delete(self.id)
        self.id = None
        self.queue = None