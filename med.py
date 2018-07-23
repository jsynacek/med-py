#!/usr/bin/python3

import curses
import itertools
import sys

import text

class Logger():
    def __init__(self, path):
        self.file = open(path, 'w+')

    def log(self, txt):
        self.file.write(txt + '\n')
        self.file.flush()

# DEBUG
logger = Logger('log.txt')

class Point:
    def __init__(self, pos=0):
        self.pos = pos

    def right(self, txt):
        if len(txt) <= 0 or self.pos >= len(txt):
            return
        self.pos += 1

    def left(self, txt):
        self.pos = max(0, self.pos - 1)

    def eol(self, txt):
        self.pos = text.s_eol(txt, self.pos)

    def bol(self, txt):
        self.pos = text.s_bol(txt, self.pos)

    def down(self, txt, view_w):
        it = text.TextIter(txt, view_w, self.pos)
        p  = it.next() + 1
        # Do not work on the last line.
        if p < len(txt):
            self.pos = p

    def up(self, txt, view_w):
        it = text.TextIter(txt, view_w, self.pos)
        p = it.prev()
        # Do not work on the first line.
        if p <= 0:
            return
        it = text.TextIter(txt, view_w, p - 1)
        self.pos = it.prev()

    def goto(self, txt, pos):
        if pos < 0: pos = 0
        if pos > len(txt): pos = len(txt)
        self.pos = pos

class View:
    def __init__(self, w=80, h=25, pos=0):
        self.pos = pos
        self.w = w
        self.h = h

class Scroller:
    def __init__(self, txt, view, point):
        self.txt = txt
        self.view = view
        self.point = point

    def scroll_down(self, n):
        for _ in range(n):
            p = text.TextIter(self.txt, self.view.w, self.view.pos).next() + 1
            if p < len(self.txt):
                self.view.pos = p
                if self.view.pos > self.point.pos:
                    self.point.pos = self.view.pos

    def scroll_up(self, n, view_end):
        end = view_end
        for _ in range(n):
            if self.view.pos < 0:
                break
            pn = Point(self.view.pos)
            pn.up(self.txt, self.view.w)
            self.view.pos = pn.pos
            pn = Point(end)
            pn.up(self.txt, self.view.w)
            end = pn.pos
        # Probably rescan from view.pos and recalculate the point position...
        # OR! After scanning, I know how many lines are there in the view. Don't recalculate the position if lines < n.
        # TODO: FIXME: Fix this when at the end of file!
        if self.point.pos >= end:
            pn = Point(end)
            pn.up(self.txt, self.view.w)
            self.point.pos = pn.pos

class Interaction():
    def __init__(self, prompt, update=None, finish=None):
        self.prompt = prompt
        self.txt = ''
        self.on_update = update
        self.on_finish = finish

    def update(self, editor):
        self.on_update(editor, self)

    def finish(self, editor, cancel=False):
        self.on_finish(editor, self, cancel)
        editor.interactive = False

class SearchContext:
    def __init__(self):
        # The point and view state needed to restore the user's view
        # if the search fails: (point position, view position).
        self.mark = None
        # The last successful search: (point position, string found).
        self.last = None

def search_update(editor, what, forward=True):
    p, _ = editor.search_context.mark
    if forward:
        i = editor.txt.find(what, p)
    else:
        i = editor.txt.rfind(what, 0, p+len(what))
    if i > 0:
        editor.point.goto(editor.txt, i)
    else:
        editor.point.pos, editor.view.pos = editor.search_context.mark

def search_update_forw(editor, interaction):
    search_update(editor, interaction.txt)

def search_update_back(editor, interaction):
    search_update(editor, interaction.txt, False)

def search_finish(editor, interaction, cancel=False):
    if cancel:
        editor.point.pos, editor.view.pos = editor.search_context.mark
    elif len(interaction.txt) > 0:
        editor.search_context.last = (editor.point.pos, interaction.txt)
    editor.interactive = False

def search_next(editor, forward=True):
    if editor.search_context.last:
        p, s = editor.search_context.last
        if forward:
            p = p+1 if editor.point.pos == p else editor.point.pos
            i = editor.txt.find(s, p)
        else:
            p = p-1 if editor.point.pos == p else editor.point.pos
            i = editor.txt.rfind(s, 0, p+len(s))
        if i > 0:
            editor.point.pos = i
            editor.search_context.last = (i, s)

class Editor():
    def __init__(self, term_w, term_h):
        self.txt = ''
        self.point = Point()
        self.view = View(term_w - 1, term_h - 2)
        self.interactive = False
        self.search_context = SearchContext()

def c_main(stdscr):
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    term_h, term_w = stdscr.getmaxyx()

    editor = Editor(term_w, term_h)
    action = None

    # Options.
    tab_w = 8
    show_gutter = True
    gutter_w = 3

    if len(sys.argv) <= 1:
       return
    path = sys.argv[1]
    editor.txt = open(path).read()

    scroller = Scroller(editor.txt, editor.view, editor.point)
    f = '{:>' + str(gutter_w-1) + '}'
    mc = f.format('➥') + ' '
    mn = f.format(' ') + ' '
    while True:
        ### Display.
        stdscr.clear()
        gw = gutter_w if show_gutter else 0
        it = text.RenderIter(editor.txt, editor.view.w-gw, editor.point.pos, editor.view.pos, tab_width=tab_w)
        for i, (_, m, ln) in enumerate(itertools.islice(it, editor.view.h)):
            if show_gutter:
                if m:
                    stdscr.addstr(i, 0, mc + ln)
                else:
                    stdscr.addstr(i, 0, mn + ln)
            else:
                stdscr.addstr(i, 0, ln)
        px, py = it.point_x+gw, it.point_y
        view_end = editor.view.pos + it.render_len
        y = editor.view.h + 1
        if not editor.interactive:
            status = 'point.pos:{}, {}, {} ; view: {}-{}'.format(editor.point.pos, px, py, editor.view.pos, view_end)
            stdscr.addstr(y, 0, status[:editor.view.w])
        else:
            stdscr.addstr(y, 0, action.prompt)
            x = len(action.prompt)
            stdscr.addstr(y, x, action.txt)
        stdscr.move(py, px)
        stdscr.refresh()

        ### Process input.
        k = stdscr.get_wch()

        if editor.interactive:
            if k == curses.KEY_BACKSPACE:
                action.txt = action.txt[:-1]
                action.update(editor)
            elif k == '\n': # Enter.
                action.finish(editor, cancel=False)
            elif k == '\x1b': # Esc.
                action.finish(editor, cancel=True)
            else:
                action.txt += k
                action.update(editor)

        else:
            if k == 'q':
                break
            elif k == curses.KEY_DOWN:  scroller.scroll_down(1)
            elif k == curses.KEY_UP:    scroller.scroll_up(1, view_end)
            elif k == curses.KEY_NPAGE: scroller.scroll_down(editor.view.h // 2)
            elif k == curses.KEY_PPAGE: scroller.scroll_up(editor.view.h // 2, view_end)
            elif k == 'l': editor.point.right(editor.txt)
            elif k == 'j': editor.point.left(editor.txt)
            elif k == 'k': editor.point.down(editor.txt, editor.view.w-gw)
            elif k == 'i': editor.point.up(editor.txt, editor.view.w-gw)
            elif k == 'L': editor.point.eol(editor.txt)
            elif k == 'J': editor.point.bol(editor.txt)
            elif k == '>': editor.point.goto(editor.txt, len(editor.txt))
            elif k == '<':
                editor.point.goto(editor.txt, 0)
                editor.view.pos = 0
            elif k == '0': show_gutter = not show_gutter
            # Search.
            elif k == ';':
                action = Interaction('search → ', search_update_forw, search_finish)
                editor.search_context.mark = (editor.point.pos, editor.view.pos)
                editor.interactive = True
            elif k == ':':
                action = Interaction('search ← ', search_update_back, search_finish)
                editor.search_context.mark = (editor.point.pos, editor.view.pos)
                editor.interactive = True
            elif k == 'n':
                search_next(editor)
            elif k == 'N':
                search_next(editor, False)

        ### Adjust view for the next render.
        # For the following algorithm to work, view_end must be up to date. Since commands based on the user's
        # input could have changed the view position, view_end has to be recalculated. That really sucks,
        # because the scanning algorigthm has to actually be run twice, which makes it *really* slow.
        # I should either make the scan very quick (which is hard because of the line wrap and tabulators),
        # or redesign this algorithm somehow.
        it = text.RenderIter(editor.txt, editor.view.w-gw, editor.point.pos, editor.view.pos, tab_width=tab_w)
        for _ in itertools.islice(it, editor.view.h): pass
        view_end = editor.view.pos + it.render_len
        if editor.point.pos >= view_end:
            # This will be slow with huge number of lines...
            it = text.RenderIter(editor.txt, editor.view.w-gw, start=view_end)
            off = view_end
            while off <= editor.point.pos:
                try:
                    # When point jumps to the end of file, this is a special case.
                    l, _, _ = next(it)
                except StopIteration:
                    break
                d, _, _ = next(text.RenderIter(editor.txt, editor.view.w-gw, start=editor.view.pos))
                editor.view.pos += d
                off += l
        elif editor.point.pos < editor.view.pos:
            off = text.s_bol(editor.txt, editor.point.pos)
            it = text.RenderIter(editor.txt, editor.view.w-gw, start=off)
            # This unwieldy algorithm is a result of using a forward scanning iterator
            # to scan backwards. Well, it works.
            while True:
                l, _, _ = next(it)
                if off <= editor.point.pos:
                    editor.view.pos = off
                    off += l
                else:
                    break

if __name__ == '__main__':
    curses.wrapper(c_main)
