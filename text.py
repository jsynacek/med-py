def s_bol(txt, pos):
    if pos <= 0:
        return 0
    i = txt.rfind('\n', 0, pos)
    return i+1

def s_eol(txt, pos):
    i = txt.find('\n', pos)
    if i < 0:
        return len(txt)
    return i

def s_visual_len(line, tab_width=8):
    l = 0
    i = 0
    for i in range(0, len(line)):
        if line[i] == '\t':
            l += tab_width - l % tab_width
        else:
            l += 1
    return l

class RenderIter:
    def __init__(self, txt, width, point=0, start=0, tab_width=8):
        self.txt = txt
        self.width = width
        self.point = point
        self.pos = start
        self.tab_width = tab_width
        self._lines = 0
        self._cont = False
        self._first = True
        # Results.
        self.point_x = -1
        self.point_y = -1
        self.render_len = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.pos >= len(self.txt):
            raise StopIteration
        cont = self._cont
        p = self.pos
        # Visual width of the displayed text.
        width = self.width
        # Look behind to see if we start on the continuation line.
        if self._first and p >= width and self.txt[p-width : p].count('\n') == 0:
            self._cont = True
        self._first = False
        s = self.txt[p : p+width]

        i = s.find('\n')
        if i >= 0:
            self._cont = False
            self.pos += i + 1
        else:
            self._cont = True
            self.pos = min(len(self.txt), self.pos + width)
        # Take tabulators into account.
        # The problem here is that s_visual_len is O(n) and the loop is called for every line
        # on the display, effectively making this O(m * n^2), which is really slow.
        while s_visual_len(self.txt[p : self.pos]) > width:
            self.pos -= 1

        if p <= self.point <= self.pos:
            self.point_x = s_visual_len(self.txt[p : self.point])
            self.point_y = self._lines
        # Last line ending with a newline char is a special case
        # from the point rendering point of view.
        if self.point == len(self.txt) and self.txt[-1] == '\n':
            self.point_x = 0
            self.point_y += 1
        self._lines += 1
        self.render_len += self.pos - p
        # Return line lenghts in characters including the newline, if any.
        return (self.pos - p, cont, self.txt[p:self.pos].rstrip('\n').expandtabs(self.tab_width))


class TextIter:
    # FIXME: Continuation lines will not work correctly with tabs. See test3.c.
    """ Go to virtual line end or beginning. """
    def __init__(self, txt, width, pos):
        self.txt = txt
        self.width = width
        self.pos = pos

    def next(self):
        bol = s_bol(self.txt, self.pos)
        eol = s_eol(self.txt, self.pos)
        step = self.width - (self.pos - bol) % self.width
        return min(eol, self.pos + step - 1)

    def prev(self):
        bol = s_bol(self.txt, self.pos)
        return self.pos - (self.pos - bol) % self.width
