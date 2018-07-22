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

def c_main(stdscr):
    #logger = Logger('log.txt')
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    term_h, term_w = stdscr.getmaxyx()
    view_w = term_w - 1
    view_h = term_h - 2
    view = View(view_w, view_h)
    point = Point()
    last_search = None
    # Options.
    tab_w = 8
    show_gutter = True
    gutter_w = 3

    if len(sys.argv) <= 1:
       return
    path = sys.argv[1]
    txt = open(path).read()

    scroller = Scroller(txt, view, point)
    f = '{:>' + str(gutter_w-1) + '}'
    mc = f.format('➥') + ' '
    mn = f.format(' ') + ' '
    while True:
        ### Display.
        stdscr.clear()
        gw = gutter_w if show_gutter else 0
        it = text.RenderIter(txt, view.w-gw, point.pos, view.pos, tab_width=tab_w)
        for i, (_, m, ln) in enumerate(itertools.islice(it, view.h)):
            if show_gutter:
                if m:
                    stdscr.addstr(i, 0, mc + ln)
                else:
                    stdscr.addstr(i, 0, mn + ln)
            else:
                stdscr.addstr(i, 0, ln)
        px, py = it.point_x+gw, it.point_y
        view_end = view.pos + it.render_len
        status = 'point.pos:{}, {}, {} ; view: {}-{}'.format(point.pos, px, py, view.pos, view_end)
        stdscr.addstr(view.h + 1, 0, status[:view.w])
        stdscr.move(py, px)
        stdscr.refresh()

        ### Process input.
        k = stdscr.getch()
        if k == curses.KEY_ENTER or k == ord('\n') or k == ord('q'):
            break
        elif k == curses.KEY_DOWN:  scroller.scroll_down(1)
        elif k == curses.KEY_UP:    scroller.scroll_up(1, view_end)
        elif k == curses.KEY_NPAGE: scroller.scroll_down(3)
        elif k == curses.KEY_PPAGE: scroller.scroll_up(3, view_end)
        elif k == ord('l'): point.right(txt)
        elif k == ord('j'): point.left(txt)
        elif k == ord('k'): point.down(txt, view.w-gw)
        elif k == ord('i'): point.up(txt, view.w-gw)
        elif k == ord('L'): point.eol(txt)
        elif k == ord('J'): point.bol(txt)
        elif k == ord('>'): point.goto(txt, len(txt))
        elif k == ord('<'):
            point.goto(txt, 0)
            view.pos = 0
        elif k == ord('0'): show_gutter = not show_gutter
        elif k == ord('g'):
            point.goto(txt, 0)
        # Dead simple search. For now...
        elif k == ord('/'):
            stdscr.move(view.h + 1, 0)
            stdscr.clrtoeol()
            stdscr.addstr('search: ')
            curses.echo()
            s = stdscr.getstr().decode()
            curses.noecho()
            i = txt.find(s, point.pos)
            if i > 0:
                point.pos = i
                last_search = (i, s)
        elif k == ord('n'):
            if last_search:
                p, s = last_search
                p = p+1 if point.pos == p else point.pos
                i = txt.find(s, p)
                if i > 0:
                    point.pos = i
                    last_search = (i, s)

        ### Adjust view for the next render.
        if point.pos >= view_end:
            # This will be slow with huge number of lines...
            it = text.RenderIter(txt, view.w-gw, start=view_end)
            off = view_end
            while off <= point.pos:
                try:
                    # When point jumps to the end of file, this is a special case.
                    l, _, _ = next(it)
                except StopIteration:
                    break
                d, _, _ = next(text.RenderIter(txt, view.w-gw, start=view.pos))
                view.pos += d
                off += l
        elif point.pos < view.pos:
            off = text.s_bol(txt, point.pos)
            it = text.RenderIter(txt, view.w-gw, start=off)
            # This unwieldy algorithm is a result of using a forward scanning iterator
            # to scan backwards. Well, it works.
            while True:
                l, _, _ = next(it)
                if off <= point.pos:
                    view.pos = off
                    off += l
                else:
                    break

if __name__ == '__main__':
    curses.wrapper(c_main)
