#!/usr/bin/env python3
"""
Speed Mentorship Event Display — scaled for 800x480 display
"""

import pygame
import math
import time
import sys
import json
import os
from datetime import datetime
from enum import Enum

SCREEN_W, SCREEN_H = 800, 480
FPS = 60
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mentorship_config.json")
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))

C = {
    "bg":        ( 10,  12,  20),
    "panel":     ( 18,  22,  38),
    "panel2":    ( 25,  30,  52),
    "accent":    ( 80, 160, 255),
    "accent2":   ( 60, 220, 170),
    "accent3":   (255, 160,  60),
    "danger":    (240,  70,  70),
    "success":   ( 60, 220, 120),
    "text":      (235, 238, 248),
    "text2":     (160, 170, 200),
    "text3":     (100, 110, 145),
    "border":    ( 40,  50,  80),
    "border2":   ( 60,  75, 115),
    "white":     (255, 255, 255),
    "timer_bg":  ( 14,  20,  40),
}

DEFAULT_CONFIG = {
    "session_minutes": 4,
    "session_seconds": 0,
    "end_time": "",
    "event_name": "Speed Mentorship",
    "venue_name": "Main Hall",
    "move_direction": "right",
    "rotation_label": "Move one seat to the RIGHT ->",
    "faq": [
        {"q": "What do I do when the bell rings?",
         "a": "Move ONE SEAT to the right. Person on the far right wraps to the far left."},
        {"q": "Where do I sit when I arrive?",
         "a": "Find any open seat. Mentors sit on the INSIDE row, mentees on the OUTSIDE row."},
        {"q": "What if someone leaves early?",
         "a": "A volunteer will fill the empty seat. Keep your conversation going until the bell."},
        {"q": "What if I arrive late?",
         "a": "Wait near the entrance. A volunteer will seat you at the next bell rotation."},
        {"q": "How long is each session?",
         "a": "Each session is 4 minutes. A short beep = 1 min left. Long beep = rotate now."},
        {"q": "What questions should I ask?",
         "a": "Questions are on the projector screen. Feel free to use them or ask your own!"},
        {"q": "Where are the restrooms?",
         "a": "Exit through the double doors and turn left. Restrooms are the second door on the right."},
        {"q": "Is food available?",
         "a": "Yes! Refreshments are at the back of the room. Enjoy them during the networking break."},
    ]
}

class Mode(Enum):
    HOME     = "home"
    FAQ      = "faq"
    MAP      = "map"
    TIMER    = "timer"
    SETTINGS = "settings"


# ─── Audio ────────────────────────────────────────────────────────────────────

class AudioEngine:
    SOUND_FILES = {
        "beep_start":  "beep_start.wav",
        "beep_warn":   "beep_warn.wav",
        "beep_rotate": "beep_rotate.wav",
        "beep_end":    "beep_end.wav",
    }

    def __init__(self):
        try:
            pygame.mixer.pre_init(44100, -16, 1, 512)
            pygame.mixer.init()
            pygame.mixer.set_num_channels(8)
            self._sounds = {}
            missing = []
            for key, filename in self.SOUND_FILES.items():
                path = os.path.join(SCRIPT_DIR, filename)
                if os.path.exists(path):
                    self._sounds[key] = pygame.mixer.Sound(path)
                else:
                    missing.append(filename)
            if missing:
                print(f"Audio: missing WAV files: {missing}")
                print("Run generate_beeps.py once to create them.")
            self._ok = True
        except Exception as e:
            print(f"Audio init failed: {e}")
            self._ok = False

    def play(self, sound_name):
        if not self._ok:
            return
        s = self._sounds.get(sound_name)
        if s:
            try:
                s.play()
            except Exception as e:
                print(f"Audio play error: {e}")


# ─── Config ───────────────────────────────────────────────────────────────────

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                cfg = json.load(f)
            merged = dict(DEFAULT_CONFIG)
            merged.update(cfg)
            return merged
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


# ─── Drawing helpers ──────────────────────────────────────────────────────────

def draw_rounded_rect(surf, color, rect, radius=8, border=0, border_color=None):
    pygame.draw.rect(surf, color, rect, border_radius=radius)
    if border and border_color:
        pygame.draw.rect(surf, border_color, rect, border, border_radius=radius)

def draw_text(surf, text, font, color, x, y, align="left", max_width=None):
    if max_width:
        words = text.split()
        lines, current = [], ""
        for word in words:
            test = (current + " " + word).strip()
            if font.size(test)[0] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        for i, line in enumerate(lines):
            _render_line(surf, line, font, color, x, y + i * (font.get_height() + 3), align)
        return len(lines) * (font.get_height() + 3)
    else:
        _render_line(surf, text, font, color, x, y, align)
        return font.get_height()

def _render_line(surf, text, font, color, x, y, align="left"):
    img = font.render(text, True, color)
    w = img.get_width()
    if align == "center": x -= w // 2
    elif align == "right": x -= w
    surf.blit(img, (x, y))

def lerp_color(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# ─── Main App ─────────────────────────────────────────────────────────────────

class SpeedMentorshipApp:
    def __init__(self):
        pygame.init()
        try:
            self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.FULLSCREEN)
        except Exception:
            self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Speed Mentorship Event Display")
        pygame.mouse.set_visible(True)

        self.clock = pygame.time.Clock()
        self.audio = AudioEngine()
        self.cfg   = load_config()

        self._init_fonts()
        self._init_state()

    def _init_fonts(self):
        def tf(names, size, bold=False):
            for name in names:
                try:
                    f = pygame.font.SysFont(name, size, bold=bold)
                    if f: return f
                except Exception:
                    pass
            return pygame.font.Font(None, size)
        # Scaled down fonts for 800x480
        self.f_huge   = tf(["dejavusans","ubuntu","freesans"], 58, bold=True)
        self.f_xlarge = tf(["dejavusans","ubuntu","freesans"], 40, bold=True)
        self.f_large  = tf(["dejavusans","ubuntu","freesans"], 26, bold=True)
        self.f_medium = tf(["dejavusans","ubuntu","freesans"], 20)
        self.f_bold   = tf(["dejavusans","ubuntu","freesans"], 18, bold=True)
        self.f_small  = tf(["dejavusans","ubuntu","freesans"], 15)
        self.f_xsmall = tf(["dejavusans","ubuntu","freesans"], 13)

    def _init_state(self):
        self.mode            = Mode.HOME
        self.faq_index       = 0
        self.home_card_rects = []
        self.faq_rects       = []
        self.timer_btns      = []
        self.set_rects       = {}
        self.kbd_rects       = []
        self._back_rect      = pygame.Rect(0,0,0,0)
        self._exit_rect      = pygame.Rect(0,0,0,0)

        self.timer_running   = False
        self.session_dur     = self._cfg_duration()
        self.timer_remaining = self.session_dur
        self.timer_start_wall= None
        self.session_count   = 0
        self.event_started   = False
        self.event_ended     = False
        self.warn_played     = False
        self.rotate_played   = False

        self.t            = 0.0
        self.flash_t      = 0.0
        self.flash_active = False
        self.flash_color  = C["accent"]

        self.settings_min   = str(self.cfg["session_minutes"])
        self.settings_sec   = str(self.cfg["session_seconds"]).zfill(2)
        self.settings_end   = self.cfg["end_time"]
        self.settings_dir   = self.cfg["move_direction"]
        self.settings_focus = None
        self.last_end_check = 0

    def _cfg_duration(self):
        return self.cfg["session_minutes"] * 60 + self.cfg["session_seconds"]

    # ── Main loop ──────────────────────────────────────────────────────────────

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.t += dt
            if self.flash_active:
                self.flash_t += dt
                if self.flash_t > 0.6:
                    self.flash_active = False
            self._handle_timer()
            self._handle_events()
            self._draw()
            pygame.display.flip()

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.mode != Mode.HOME: self.mode = Mode.HOME
                    else: self._quit()
                elif event.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
                elif self.mode == Mode.SETTINGS:
                    self._settings_keydown(event)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_click(event.pos)

    def _handle_timer(self):
        if not self.timer_running or self.event_ended:
            return
        elapsed = time.time() - self.timer_start_wall
        self.timer_remaining = max(0, self.session_dur - elapsed)
        if self.timer_remaining <= 60 and not self.warn_played:
            self.audio.play("beep_warn")
            self.warn_played = True
        if self.timer_remaining <= 0 and not self.rotate_played:
            self.rotate_played = True
            self._do_rotate()
        now = time.time()
        if now - self.last_end_check > 5:
            self.last_end_check = now
            self._check_end_time()

    def _do_rotate(self):
        self.session_count   += 1
        self.audio.play("beep_rotate")
        self._flash(C["accent2"])
        self.session_dur      = self._cfg_duration()
        self.timer_remaining  = self.session_dur
        self.timer_start_wall = time.time()
        self.warn_played      = False
        self.rotate_played    = False

    def _flash(self, color):
        self.flash_active = True
        self.flash_t      = 0.0
        self.flash_color  = color

    def _check_end_time(self):
        et = self.cfg.get("end_time","").strip()
        if not et or self.event_ended: return
        try:
            h, m = map(int, et.split(":"))
            now = datetime.now()
            end_dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if now >= end_dt:
                self._end_event()
        except Exception:
            pass

    def _end_event(self):
        self.event_ended   = True
        self.timer_running = False
        self.audio.play("beep_end")
        self._flash(C["accent3"])

    def _start_event(self):
        self.event_started    = True
        self.event_ended      = False
        self.timer_running    = True
        self.session_count    = 0
        self.session_dur      = self._cfg_duration()
        self.timer_remaining  = self.session_dur
        self.timer_start_wall = time.time()
        self.warn_played      = False
        self.rotate_played    = False
        self.audio.play("beep_start")
        self._flash(C["success"])

    def _pause_timer(self):
        if self.timer_running:
            self.timer_running = False
        else:
            self.timer_start_wall = time.time() - (self.session_dur - self.timer_remaining)
            self.timer_running    = True

    def _skip_session(self):
        self._do_rotate()

    def _quit(self):
        pygame.quit()
        sys.exit()

    # ── Click routing ──────────────────────────────────────────────────────────

    def _handle_click(self, pos):
        x, y = pos
        if self._exit_rect.collidepoint(pos):
            self._quit()
        # Corner nav buttons (bottom bar)
        if 0 <= x <= 80 and SCREEN_H-35 <= y <= SCREEN_H:
            self.mode = Mode.MAP; return
        if SCREEN_W//2-40 <= x <= SCREEN_W//2+40 and SCREEN_H-35 <= y <= SCREEN_H:
            self.mode = Mode.HOME; return
        if SCREEN_W-80 <= x <= SCREEN_W and SCREEN_H-35 <= y <= SCREEN_H:
            self.mode = Mode.TIMER; return
        # SETUP button top-right (left of X)
        if SCREEN_W-115 <= x <= SCREEN_W-65 and 5 <= y <= 35:
            self.mode = Mode.SETTINGS; return

        if   self.mode == Mode.HOME:     self._click_home(pos)
        elif self.mode == Mode.FAQ:      self._click_faq(pos)
        elif self.mode == Mode.MAP:      self._click_map(pos)
        elif self.mode == Mode.TIMER:    self._click_timer(pos)
        elif self.mode == Mode.SETTINGS: self._click_settings(pos)

    # ── Draw dispatcher ────────────────────────────────────────────────────────

    def _draw(self):
        self.screen.fill(C["bg"])

        if   self.mode == Mode.HOME:     self._draw_home()
        elif self.mode == Mode.FAQ:      self._draw_faq()
        elif self.mode == Mode.MAP:      self._draw_map()
        elif self.mode == Mode.TIMER:    self._draw_timer()
        elif self.mode == Mode.SETTINGS: self._draw_settings()

        if self.flash_active:
            alpha = int(180 * max(0, 1 - self.flash_t / 0.6))
            ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            ov.fill((*self.flash_color, alpha))
            self.screen.blit(ov, (0, 0))

        self._draw_chrome()

    def _draw_chrome(self):
        # Bottom nav bar
        bar = pygame.Rect(0, SCREEN_H-32, SCREEN_W, 32)
        draw_rounded_rect(self.screen, C["panel2"], bar, 0, 1, C["border"])
        self._nav_btn(0,           SCREEN_H-32, 80,  "MAP",   self.mode==Mode.MAP)
        self._nav_btn(SCREEN_W//2-40, SCREEN_H-32, 80, "HOME", self.mode==Mode.HOME)
        self._nav_btn(SCREEN_W-80, SCREEN_H-32, 80,  "TIMER", self.mode==Mode.TIMER)

        # Top-right: SETUP + X
        self._nav_btn(SCREEN_W-115, 5, 48, "SETUP", self.mode==Mode.SETTINGS)
        self._exit_rect = pygame.Rect(SCREEN_W-62, 5, 55, 26)
        draw_rounded_rect(self.screen, C["panel2"], self._exit_rect, 6, 1, C["danger"])
        img = self.f_xsmall.render("X EXIT", True, C["danger"])
        self.screen.blit(img, (SCREEN_W-62+(55-img.get_width())//2, 5+(26-img.get_height())//2))

    def _nav_btn(self, x, y, w, label, active):
        color  = C["accent"] if active else C["panel2"]
        border = C["accent"] if active else C["border"]
        r = pygame.Rect(x, y, w, 32)
        draw_rounded_rect(self.screen, color, r, 5, 1, border)
        img = self.f_xsmall.render(label, True, C["text"] if active else C["text2"])
        self.screen.blit(img, (x+(w-img.get_width())//2, y+(32-img.get_height())//2))

    # ══════════════════════════════════════════════════════════════════════════
    # HOME
    # ══════════════════════════════════════════════════════════════════════════

    def _draw_home(self):
        pulse  = 0.5 + 0.5 * math.sin(self.t * 1.5)
        accent = lerp_color(C["accent"], C["accent2"], pulse)
        draw_text(self.screen, self.cfg["event_name"], self.f_xlarge, accent, SCREEN_W//2, 8, "center")
        draw_text(self.screen, self.cfg["venue_name"], self.f_xsmall, C["text2"], SCREEN_W//2, 52, "center")

        # Timer status strip
        self._draw_timer_strip(68)

        # Three nav cards
        cards = [
            ("FAQ", "FAQs",       "Common questions", Mode.FAQ,   C["accent"]),
            ("MAP", "Room Map",   "Layout & rotation", Mode.MAP,  C["accent2"]),
            ("TMR", "Timer",      "Session control",  Mode.TIMER, C["accent3"]),
        ]
        cw, ch, gap = 228, 110, 8
        total = len(cards)*cw + (len(cards)-1)*gap
        x0 = (SCREEN_W - total)//2
        y0 = 100
        self.home_card_rects = []
        for i,(icon,title,sub,target,color) in enumerate(cards):
            cx = x0 + i*(cw+gap)
            r = pygame.Rect(cx, y0, cw, ch)
            self.home_card_rects.append((r, target))
            hover = r.collidepoint(pygame.mouse.get_pos())
            bg = lerp_color(C["panel2"], C["panel"], 0.5) if hover else C["panel2"]
            draw_rounded_rect(self.screen, bg, r, 10, 2, color)
            draw_text(self.screen, icon,  self.f_large, color,     cx+10, y0+10)
            draw_text(self.screen, title, self.f_bold,  C["text"], cx+10, y0+46)
            draw_text(self.screen, sub,   self.f_xsmall,C["text2"],cx+10, y0+70, max_width=cw-16)

        # Rotation reminder
        self._draw_rotation_banner(220)

        # Quick FAQ
        self._draw_quick_faq(268)

    def _draw_timer_strip(self, y):
        if not self.event_started:
            status, color = "Event not started — tap TIMER to begin", C["text3"]
        elif self.event_ended:
            status, color = "Event complete — thank you!", C["success"]
        elif self.timer_running:
            mins = int(self.timer_remaining)//60
            secs = int(self.timer_remaining)%60
            status = f"Session {self.session_count+1}  |  {mins}:{secs:02d} remaining"
            color  = C["accent2"] if self.timer_remaining > 60 else C["danger"]
        else:
            mins = int(self.timer_remaining)//60
            secs = int(self.timer_remaining)%60
            status = f"PAUSED  |  {mins}:{secs:02d} remaining  |  Session {self.session_count+1}"
            color  = C["accent3"]
        r = pygame.Rect(8, y, SCREEN_W-16, 28)
        draw_rounded_rect(self.screen, C["panel"], r, 6, 1, C["border"])
        draw_text(self.screen, status, self.f_xsmall, color, SCREEN_W//2, y+6, "center")

    def _draw_rotation_banner(self, y):
        direction = self.cfg.get("rotation_label","Move one seat to the RIGHT ->")
        r = pygame.Rect(8, y, SCREEN_W-16, 36)
        pulse = 0.5 + 0.5 * math.sin(self.t * 2.0)
        bc = lerp_color(C["accent2"], C["accent"], pulse)
        draw_rounded_rect(self.screen, C["panel2"], r, 8, 2, bc)
        arrow = "->" if self.cfg.get("move_direction") == "right" else "<-"
        draw_text(self.screen, f"BELL: {direction}  {arrow}",
                  self.f_bold, C["accent2"], SCREEN_W//2, y+9, "center")

    def _draw_quick_faq(self, y):
        faq = self.cfg["faq"]
        if not faq: return
        item = faq[self.faq_index % len(faq)]
        r = pygame.Rect(8, y, SCREEN_W-16, 140)
        draw_rounded_rect(self.screen, C["panel"], r, 8, 1, C["border"])
        draw_text(self.screen, "Q: "+item["q"], self.f_small, C["accent"],  16, y+8,  max_width=SCREEN_W-32)
        draw_text(self.screen, "A: "+item["a"], self.f_xsmall,C["text2"],  16, y+36, max_width=SCREEN_W-32)
        draw_text(self.screen, "tap for next >", self.f_xsmall, C["text3"], SCREEN_W-16, y+118, "right")

    def _click_home(self, pos):
        for r, target in self.home_card_rects:
            if r.collidepoint(pos):
                self.mode = target; return
        if 8 <= pos[0] <= SCREEN_W-8 and 268 <= pos[1] <= 408:
            self.faq_index = (self.faq_index+1) % len(self.cfg["faq"])

    # ══════════════════════════════════════════════════════════════════════════
    # FAQ
    # ══════════════════════════════════════════════════════════════════════════

    def _draw_faq(self):
        draw_text(self.screen, "Frequently Asked Questions", self.f_large, C["accent"], SCREEN_W//2, 8, "center")
        draw_text(self.screen, "Tap a question to expand it", self.f_xsmall, C["text3"], SCREEN_W//2, 36, "center")
        faq = self.cfg["faq"]
        self.faq_rects = []
        y = 55
        for i, item in enumerate(faq):
            expanded = (i == self.faq_index)
            height   = 90 if expanded else 36
            r = pygame.Rect(8, y, SCREEN_W-16, height)
            self.faq_rects.append((r, i))
            bg     = C["panel2"] if expanded else C["panel"]
            border = C["accent"] if expanded else C["border"]
            draw_rounded_rect(self.screen, bg, r, 6, 2 if expanded else 1, border)
            draw_text(self.screen, "Q: "+item["q"], self.f_small,
                      C["accent"] if expanded else C["text"], 16, y+8, max_width=SCREEN_W-40)
            if expanded:
                draw_text(self.screen, "A: "+item["a"], self.f_xsmall, C["accent2"],
                          16, y+34, max_width=SCREEN_W-40)
            y += height + 5
            if y > SCREEN_H-40: break
        self._draw_back_btn()

    def _click_faq(self, pos):
        if self._check_back(pos): return
        for r, i in self.faq_rects:
            if r.collidepoint(pos):
                self.faq_index = i if self.faq_index != i else -1
                return

    # ══════════════════════════════════════════════════════════════════════════
    # MAP
    # ══════════════════════════════════════════════════════════════════════════

    def _draw_map(self):
        draw_text(self.screen, "Room Layout & Rotation", self.f_large, C["accent2"], SCREEN_W//2, 8, "center")
        draw_text(self.screen, "Mentors (inside) stay seated. Mentees (outside) rotate.",
                  self.f_xsmall, C["text2"], SCREEN_W//2, 36, "center")
        direction = self.cfg.get("move_direction","right")
        self._draw_table_map(direction)
        self._draw_map_legend()
        self._draw_back_btn()

    def _draw_table_map(self, direction):
        cx      = SCREEN_W // 2
        tw      = 740
        tx      = cx - tw//2
        ns      = 10          # number of seats per row
        sw, sh  = 52, 24
        gap     = (tw - ns*sw)//(ns-1)

        row_in  = 100
        row_out = 180
        trow_y  = 130

        draw_rounded_rect(self.screen, C["panel2"], pygame.Rect(tx, trow_y, tw, 30), 6, 1, C["border2"])
        draw_text(self.screen, "<-- TABLE SNAKE LAYOUT -->", self.f_xsmall, C["text3"], cx, trow_y+8, "center")

        seats_in, seats_out = [], []
        for i in range(ns):
            sx = tx + i*(sw+gap)
            ri = pygame.Rect(sx, row_in,  sw, sh)
            ro = pygame.Rect(sx, row_out, sw, sh)
            seats_in.append(ri)
            seats_out.append(ro)
            draw_rounded_rect(self.screen, C["accent"], ri, 4)
            draw_text(self.screen, f"M{i+1}", self.f_xsmall, C["white"], sx+sw//2, row_in+5, "center")
            draw_rounded_rect(self.screen, C["panel"], ro, 4, 1, C["accent2"])
            draw_text(self.screen, f"A{i+1}", self.f_xsmall, C["accent2"], sx+sw//2, row_out+5, "center")

        anim = 0.5 + 0.5 * math.sin(self.t*2.5)
        acol = lerp_color(C["accent2"], C["white"], anim*0.4)

        for i in range(ns-1):
            if direction == "right":
                ax, bx = seats_out[i].right+1, seats_out[i+1].left-1
            else:
                ax, bx = seats_out[i+1].right+1, seats_out[i].left-1
            ay = row_out + sh//2
            self._draw_arrow(ax, ay, bx, ay, acol)

        # Wrap arrow below
        fy = row_out + sh + 4
        if direction == "right":
            fx, tx2 = seats_out[-1].centerx, seats_out[0].centerx
        else:
            fx, tx2 = seats_out[0].centerx, seats_out[-1].centerx
        bot = fy + 18
        pts = []
        for i in range(20):
            t2 = i/19
            px = (1-t2)**3*fx + 3*(1-t2)**2*t2*fx + 3*(1-t2)*t2**2*tx2 + t2**3*tx2
            py = (1-t2)**3*fy + 3*(1-t2)**2*t2*bot + 3*(1-t2)*t2**2*bot + t2**3*fy
            pts.append((int(px),int(py)))
        if len(pts) >= 2:
            pygame.draw.lines(self.screen, acol, False, pts, 2)

        draw_text(self.screen, "START->", self.f_xsmall, C["success"], tx-4, row_out+5, "right")
        draw_text(self.screen, "<-END",   self.f_xsmall, C["danger"],  tx+tw+4, row_out+5)

        arr_str = "-> Mentees move RIGHT each round" if direction=="right" else "<- Mentees move LEFT each round"
        draw_text(self.screen, arr_str, self.f_bold, C["accent2"], cx, 245, "center")

        steps = [
            ("1", "Mentors stay seated the whole event."),
            ("2", "Mentees move one seat in the arrow direction when the bell rings."),
            ("3", "Person at the end wraps to the opposite end of the row."),
        ]
        y = 270
        for num, txt in steps:
            r = pygame.Rect(cx-370, y, 740, 28)
            draw_rounded_rect(self.screen, C["panel"], r, 5, 1, C["border"])
            draw_text(self.screen, num, self.f_bold,  C["accent"], cx-358, y+5)
            draw_text(self.screen, txt, self.f_xsmall,C["text"],   cx-340, y+6)
            y += 34

    def _draw_arrow(self, x1, y1, x2, y2, color, head=7):
        pygame.draw.line(self.screen, color, (x1,y1), (x2,y2), 2)
        angle = math.atan2(y2-y1, x2-x1)
        for da in (0.5, -0.5):
            ex = x2 - head*math.cos(angle-da)
            ey = y2 - head*math.sin(angle-da)
            pygame.draw.line(self.screen, color, (x2,y2), (int(ex),int(ey)), 2)

    def _draw_map_legend(self):
        items = [(C["accent"],"Mentor (fixed)"),(C["accent2"],"Mentee (rotates)"),
                 (C["success"],"Start"),(C["danger"],"End")]
        x = 8
        y = SCREEN_H - 58
        for col, label in items:
            pygame.draw.rect(self.screen, col, (x, y, 12, 12), border_radius=2)
            draw_text(self.screen, label, self.f_xsmall, C["text2"], x+16, y)
            x += 145

    def _click_map(self, pos):
        self._check_back(pos)

    # ══════════════════════════════════════════════════════════════════════════
    # TIMER
    # ══════════════════════════════════════════════════════════════════════════

    def _draw_timer(self):
        cx, cy = SCREEN_W//2, 195
        radius = 130

        max_t = self.session_dur if self.session_dur > 0 else 1
        frac  = self.timer_remaining / max_t

        pygame.draw.circle(self.screen, C["timer_bg"], (cx,cy), radius)
        pygame.draw.circle(self.screen, C["border"],   (cx,cy), radius, 2)

        if frac > 0:
            arc_color = C["success"] if frac > 0.33 else (C["accent3"] if frac > 0.15 else C["danger"])
            start_a = -math.pi/2
            end_a   = start_a + 2*math.pi*frac
            pts = []
            for i in range(201):
                a = start_a + (end_a-start_a)*i/200
                pts.append((cx+int((radius-5)*math.cos(a)), cy+int((radius-5)*math.sin(a))))
            if len(pts) >= 2:
                pygame.draw.lines(self.screen, arc_color, False, pts, 8)

        if self.event_ended:
            draw_text(self.screen, "EVENT COMPLETE", self.f_large,  C["accent3"], cx, cy-18, "center")
            draw_text(self.screen, "Thank you!",     self.f_medium, C["text2"],   cx, cy+18, "center")
        else:
            mins = int(self.timer_remaining)//60
            secs = int(self.timer_remaining)%60
            pulse = 0.85 + 0.15*math.sin(self.t*3)
            tcol  = C["text"] if self.timer_remaining > 30 else lerp_color(C["text"], C["danger"], pulse)
            draw_text(self.screen, f"{mins}:{secs:02d}", self.f_huge,   tcol,      cx, cy-34, "center")
            lbl = "remaining" if self.timer_running else "paused"
            draw_text(self.screen, lbl,                  self.f_xsmall, C["text2"], cx, cy+34, "center")
            draw_text(self.screen, f"Session {self.session_count+1}", self.f_xsmall, C["text3"], cx, cy+52, "center")

        self.timer_btns = []
        btn_y = 345
        if not self.event_started or self.event_ended:
            btns = [("START EVENT", self._start_event, C["success"])]
        elif self.timer_running:
            btns = [("PAUSE", self._pause_timer, C["accent3"]), ("NEXT SESSION", self._skip_session, C["accent"])]
        else:
            btns = [("RESUME", self._pause_timer, C["success"]), ("NEXT SESSION", self._skip_session, C["accent"])]

        bw    = 160
        total = len(btns)*bw + (len(btns)-1)*12
        bx    = (SCREEN_W-total)//2
        for label, action, col in btns:
            r = pygame.Rect(bx, btn_y, bw, 38)
            self.timer_btns.append((r, action))
            hover = r.collidepoint(pygame.mouse.get_pos())
            bg = lerp_color(col, C["bg"], 0.2 if hover else 0.4)
            draw_rounded_rect(self.screen, bg, r, 8, 2, col)
            draw_text(self.screen, label, self.f_bold, C["white"], r.centerx, btn_y+10, "center")
            bx += bw+12

        et = self.cfg.get("end_time","").strip()
        if et:
            draw_text(self.screen, f"Event ends: {et}", self.f_xsmall, C["text3"], cx, 396, "center")
        if self.event_started and not self.event_ended:
            draw_text(self.screen, f"Completed: {self.session_count} sessions", self.f_xsmall, C["text2"], cx, 416, "center")

        arrow = "-> RIGHT" if self.cfg.get("move_direction")=="right" else "<- LEFT"
        draw_text(self.screen, f"Bell = Move {arrow}", self.f_bold, C["accent2"], cx, 436, "center")

        self._draw_back_btn()

    def _click_timer(self, pos):
        if self._check_back(pos): return
        for r, action in self.timer_btns:
            if r.collidepoint(pos):
                action(); return

    # ══════════════════════════════════════════════════════════════════════════
    # SETTINGS
    # ══════════════════════════════════════════════════════════════════════════

    def _draw_settings(self):
        draw_text(self.screen, "Settings", self.f_large, C["accent"], SCREEN_W//2, 8, "center")

        col1, col2 = 10, 260
        y = 42
        self.set_rects = {"presets":[], "dir":[]}

        # Duration
        draw_text(self.screen, "Session duration", self.f_bold, C["text"], col1, y)
        draw_text(self.screen, "min", self.f_xsmall, C["text2"], col2+52, y+4)
        draw_text(self.screen, "sec", self.f_xsmall, C["text2"], col2+152, y+4)

        mr = pygame.Rect(col2,     y, 46, 30)
        sr = pygame.Rect(col2+100, y, 46, 30)
        self.set_rects["min"] = mr
        self.set_rects["sec"] = sr
        for field, r, val in [("min",mr,self.settings_min),("sec",sr,self.settings_sec)]:
            focused = self.settings_focus == field
            draw_rounded_rect(self.screen, C["panel2"], r, 6, 2, C["accent"] if focused else C["border"])
            draw_text(self.screen, val, self.f_bold, C["text"], r.centerx, r.y+6, "center")

        # Presets
        y2 = y+38
        draw_text(self.screen, "Presets:", self.f_xsmall, C["text2"], col1, y2+4)
        for pm, ps, lbl in [(3,0,"3:00"),(3,30,"3:30"),(4,0,"4:00"),(4,30,"4:30"),(5,0,"5:00")]:
            pr = pygame.Rect(col2 + len(self.set_rects["presets"])*56, y2, 50, 26)
            active = self.settings_min==str(pm) and self.settings_sec==str(ps).zfill(2)
            draw_rounded_rect(self.screen, C["accent"] if active else C["panel2"], pr, 5, 1,
                              C["accent"] if active else C["border"])
            draw_text(self.screen, lbl, self.f_xsmall, C["white"] if active else C["text2"],
                      pr.centerx, pr.y+5, "center")
            self.set_rects["presets"].append((pr, pm, ps))

        # End time
        y += 82
        draw_text(self.screen, "Event end time (HH:MM)", self.f_bold, C["text"], col1, y)
        draw_text(self.screen, "Leave blank = no auto-end", self.f_xsmall, C["text3"], col1, y+20)
        er = pygame.Rect(col2, y, 100, 30)
        self.set_rects["end"] = er
        focused = self.settings_focus == "end"
        draw_rounded_rect(self.screen, C["panel2"], er, 6, 2, C["accent"] if focused else C["border"])
        edisp = self.settings_end if self.settings_end else "e.g. 18:30"
        tcol  = C["text"] if self.settings_end else C["text3"]
        draw_text(self.screen, edisp, self.f_xsmall if not self.settings_end else self.f_bold,
                  tcol, er.centerx, er.y+7, "center")

        # Direction
        y += 60
        draw_text(self.screen, "Rotation direction", self.f_bold, C["text"], col1, y)
        dx = col2
        for val, label in [("right","-> RIGHT"),("left","<- LEFT")]:
            active = self.settings_dir == val
            dr = pygame.Rect(dx, y-4, 120, 30)
            draw_rounded_rect(self.screen, C["accent"] if active else C["panel2"], dr, 6, 1,
                              C["accent"] if active else C["border"])
            draw_text(self.screen, label, self.f_bold if active else self.f_xsmall,
                      C["white"] if active else C["text2"], dr.centerx, dr.y+7, "center")
            self.set_rects["dir"].append((dr, val))
            dx += 128

        # Soft keyboard
        y += 44
        if self.settings_focus:
            self._draw_soft_keyboard(y)

        # Save / Cancel
        btn_y = SCREEN_H - 68
        save_r   = pygame.Rect(SCREEN_W//2-160, btn_y, 140, 34)
        cancel_r = pygame.Rect(SCREEN_W//2+20,  btn_y, 140, 34)
        self.set_rects["save"]   = save_r
        self.set_rects["cancel"] = cancel_r
        draw_rounded_rect(self.screen, C["success"], save_r,   8, 1, C["success"])
        draw_text(self.screen, "Save & Apply", self.f_bold, C["white"], save_r.centerx, btn_y+8, "center")
        draw_rounded_rect(self.screen, C["panel2"], cancel_r,  8, 1, C["border"])
        draw_text(self.screen, "Cancel", self.f_bold, C["text2"], cancel_r.centerx, btn_y+8, "center")

    def _draw_soft_keyboard(self, y):
        rows = [["7","8","9"],["4","5","6"],["1","2","3"],[":","0","<-"]]
        self.kbd_rects = []
        kw, kh, gap = 48, 36, 6
        kx0 = 260
        ky  = y
        for row in rows:
            kx = kx0
            for key in row:
                kr = pygame.Rect(kx, ky, kw, kh)
                self.kbd_rects.append((kr, key))
                hover = kr.collidepoint(pygame.mouse.get_pos())
                draw_rounded_rect(self.screen, C["border"] if hover else C["panel2"], kr, 5, 1, C["border2"])
                draw_text(self.screen, key, self.f_bold, C["text"], kx+kw//2, ky+9, "center")
                kx += kw+gap
            ky += kh+gap

    def _click_settings(self, pos):
        if self._check_back(pos): return
        rects = self.set_rects
        if rects.get("save") and rects["save"].collidepoint(pos):
            self._save_settings(); return
        if rects.get("cancel") and rects["cancel"].collidepoint(pos):
            self.mode = Mode.HOME; return
        for pr, pm, ps in rects.get("presets",[]):
            if pr.collidepoint(pos):
                self.settings_min = str(pm)
                self.settings_sec = str(ps).zfill(2)
                self.settings_focus = None; return
        for dr, val in rects.get("dir",[]):
            if dr.collidepoint(pos):
                self.settings_dir = val; return
        for field in ["min","sec","end"]:
            r = rects.get(field)
            if r and r.collidepoint(pos):
                self.settings_focus = field; return
        for kr, key in self.kbd_rects:
            if kr.collidepoint(pos):
                self._kbd_input(key); return

    def _kbd_input(self, key):
        f = self.settings_focus
        if not f: return
        if key == "<-":
            if f == "min": self.settings_min = self.settings_min[:-1] or "0"
            elif f == "sec": self.settings_sec = self.settings_sec[:-1] or "00"
            elif f == "end": self.settings_end = self.settings_end[:-1]
        elif key == ":":
            if f == "end": self.settings_end += ":"
        elif key.isdigit():
            if f == "min":
                v = (self.settings_min+key).lstrip("0") or "0"
                if int(v) <= 99: self.settings_min = v
            elif f == "sec":
                v = (self.settings_sec+key).lstrip("0") or "0"
                if int(v) <= 59: self.settings_sec = str(int(v)).zfill(2)
            elif f == "end":
                if len(self.settings_end) < 5: self.settings_end += key

    def _settings_keydown(self, event):
        if event.key == pygame.K_TAB:
            fields = ["min","sec","end"]
            idx = fields.index(self.settings_focus) if self.settings_focus in fields else -1
            self.settings_focus = fields[(idx+1)%len(fields)]; return
        if event.key == pygame.K_RETURN:
            self._save_settings(); return
        if event.key == pygame.K_BACKSPACE:
            self._kbd_input("<-"); return
        char = event.unicode
        if char.isdigit(): self._kbd_input(char)
        elif char == ":": self._kbd_input(":")

    def _save_settings(self):
        try:
            m = max(0, min(99, int(self.settings_min) if self.settings_min else 0))
            s = max(0, min(59, int(self.settings_sec) if self.settings_sec else 0))
            if m == 0 and s == 0: m, s = 4, 0
        except ValueError:
            m, s = 4, 0
        direction = self.settings_dir
        rlabel = "Move one seat to the RIGHT ->" if direction=="right" else "<- Move one seat to the LEFT"
        self.cfg["session_minutes"] = m
        self.cfg["session_seconds"] = s
        self.cfg["end_time"]        = self.settings_end.strip()
        self.cfg["move_direction"]  = direction
        self.cfg["rotation_label"]  = rlabel
        save_config(self.cfg)
        self.session_dur = self._cfg_duration()
        if not self.timer_running:
            self.timer_remaining = self.session_dur
        self.settings_min   = str(m)
        self.settings_sec   = str(s).zfill(2)
        self.settings_focus = None
        self.mode = Mode.HOME
        self._flash(C["success"])

    # ── Shared helpers ─────────────────────────────────────────────────────────

    def _draw_back_btn(self):
        r = pygame.Rect(8, 8, 80, 26)
        self._back_rect = r
        draw_rounded_rect(self.screen, C["panel2"], r, 6, 1, C["border"])
        draw_text(self.screen, "<- Back", self.f_xsmall, C["text2"], r.centerx, r.y+6, "center")

    def _check_back(self, pos):
        if self._back_rect.collidepoint(pos):
            self.mode = Mode.HOME
            return True
        return False


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        import pygame
    except ImportError:
        print("pygame not found. Run: sudo apt install python3-pygame")
        sys.exit(1)
    app = SpeedMentorshipApp()
    app.run()
