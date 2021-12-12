import pyautogui
import cv2
import time
import subprocess

from PIL import ImageGrab, Image
import numpy as np

import win32api
from winguiauto import findTopWindow
import win32gui
import win32con
import os

import datetime

G_HWND = None
G_RECT = None


def _t(tag='info', now=None):
    now = now if now else datetime.datetime.now()
    tmp = now.strftime('%Y-%m-%d %H:%M:%S.%f')
    arr = tmp.split('.', 2)
    if len(arr) == 2:
        ms = int(arr[1] + '0' * (6 - len(arr[1])))
        ret = arr[0] + '.' + '{:0>3d}'.format(int(ms / 1000))
    else:
        ret = arr[0] + '.000'

    return ret + ' [' + tag.upper() + ']'


def find_lushi_window():
    global G_HWND, G_RECT

    hwnd = G_HWND if G_HWND else findTopWindow("炉石传说")
    G_HWND = hwnd

    t_rect = G_RECT if G_RECT else win32gui.GetWindowPlacement(hwnd)[-1]
    G_RECT = t_rect

    image = ImageGrab.grab(t_rect)
    image = cv2.cvtColor(np.array(image), cv2.COLOR_BGR2GRAY)
    return t_rect, image


        
def set_top_window(title='炉石传说'):
    top_windows = []
    
    def windowEnumerationHandler(hwnd, top_windows):
        top_windows.append((hwnd, win32gui.GetWindowText(hwnd)))
    
    win32gui.EnumWindows(windowEnumerationHandler, top_windows)
    for i in top_windows:
        if title in i[1].lower():
            win32gui.ShowWindow(i[0],5)
            win32gui.SetForegroundWindow(i[0])
            return True
    else:
        return False
            

G_ICON_RANGE_CACHE = {}

G_ICON_RANGE_STATIC = {
    'not_ready_dots': [(650, 530), (1020, 600)],
    'final_reward2': [(490, 210), (1200, 770)],
}
for t in ['b-fh', 'b-zs', 'b-fs', 'b-ck', 'b-try']:
    G_ICON_RANGE_STATIC[t] = [(300, 370), (1010, 650)]

def d_range(icon, pos, mw=20, mh=10):
    w = icon.shape[1] // 2
    h = icon.shape[0] // 2
    ww = w if w < mw else mw
    hh = h if w < mh else mh
    return [(pos[0] - w - ww, pos[1] - h - hh), (pos[0] + w + ww, pos[1] + h + hh)]

G_CACHE_MAP = {
    'member_ready': d_range,
    'battle_ready': d_range,
    'treasure_list': d_range,
    'treasure_replace': d_range,
    'skill_select': d_range,
    'visitor_list': d_range,
    '1-1': d_range,
    '2-5': d_range,
    '2-6': d_range,
    'f-fh': d_range,
    'f-buf': d_range,
    'stranger': d_range,
    'blue_portal': d_range,
    'destroy': d_range,
    'boom': d_range,
    'cfm_done': d_range,
    'cfm_reward': d_range,
    'start_game': d_range,
    'map_not_ready': d_range,
    'start_point': d_range,
    'team_lock': d_range,
    'team_list': d_range,
    'final_reward': d_range,
}

def find_icon_location(k, lushi, icon, kk=0.8699):
    global G_ICON_RANGE_CACHE

    if k in G_ICON_RANGE_CACHE:
        p1, p2 = (G_CACHE_MAP[k])(icon, G_ICON_RANGE_CACHE[k])
        lushi = lushi[p1[1]:p2[1], p1[0]:p2[0]]
    elif k in G_ICON_RANGE_STATIC:
        p1, p2 = G_ICON_RANGE_STATIC[k]
        lushi = lushi[p1[1]:p2[1], p1[0]:p2[0]]
        
    result = cv2.matchTemplate(lushi, icon, cv2.TM_CCOEFF_NORMED)
    (minVal, maxVal, minLoc, maxLoc) = cv2.minMaxLoc(result)
    if k == 'b-try' or k == 'not_ready_dots' or k == 'skill_select':
        kk = 0.68
        
    if k.startswith('final_reward'):
        kk = 0.55
        
    if maxVal > kk:
        maxVal = round(maxVal, 3)
        tmp = (0, 0)
        if k in G_ICON_RANGE_CACHE:
            tmp = (G_CACHE_MAP[k])(icon, G_ICON_RANGE_CACHE[k])[0]
        elif k in G_ICON_RANGE_STATIC:
            tmp = G_ICON_RANGE_STATIC[k][0]
        
        startX, startY = tmp[0] + maxLoc[0], tmp[1] + maxLoc[1]
        px = startX + icon.shape[1] // 2
        py = startY + icon.shape[0] // 2
        ret = (True, px, py, -maxVal if k in G_ICON_RANGE_CACHE or k in G_ICON_RANGE_STATIC else maxVal)

        if k in G_CACHE_MAP:
            G_ICON_RANGE_CACHE[k] = (px, py)

        # print(_t(), 'CACHE:', G_ICON_RANGE_CACHE)
        return ret
    else:
        return False, None, None, maxVal


rect = [0, 0]
_tp = lambda pos=None, y=None: pos if isinstance(pos, (tuple, list)) else (pos, y)

r_moveTo = lambda *args, **kwgs: pyautogui.moveTo(*args, **kwgs)
r_click = lambda *args, **kwgs: pyautogui.click(*args, **kwgs)
x_moveTo = lambda pos=None, y=None, **kwgs: pyautogui.moveTo(rect[0] + _tp(pos, y)[0],
                                                             rect[1] + _tp(pos, y)[1], **kwgs)
x_click = lambda pos=None, y=None, **kwgs: pyautogui.click(rect[0] + _tp(pos, y)[0],
                                                           rect[1] + _tp(pos, y)[1], **kwgs)


class Agent:

    def __init__(self, team_id, heros_id, skills_id, targets_id, hero_cnt, while_delay):
        self.icons = {}
        imgs = [img for img in os.listdir('imgs') if img.endswith('.png')]
        for img in imgs:
            k = img.split('.')[0]
            v = cv2.cvtColor(cv2.imread(os.path.join('imgs', img)), cv2.COLOR_BGR2GRAY)
            self.icons[k] = v

        self.team_id = team_id
        self.heros_id = heros_id
        self.skills_id = skills_id
        self.targets_id = targets_id
        self.hero_cnt = hero_cnt
        self.while_delay = while_delay

        self.hero_relative_locs = [
            (692, 632),
            (807, 641),
            (943, 641)
        ]

        self.enemy_mid_location = (850, 285)

        self.skill_relative_locs = [
            (653, 447),
            (801, 453),
            (963, 459),
        ]

        self.treasure_locs = [
            (707, 376), (959, 376), (1204, 376)
        ]
        self.treasure_collect_loc = (968, 765)

        self.visitor_locs = [
            (544, 426), (790, 420), (1042, 416)
        ]
        self.visitor_choose_loc = (791, 688)

        self.members_loc = (622, 1000, 900)

        self.drag2loc = (1213, 564)

        self.locs = {
            'left': [(452, 464), (558, 461), (473, 465)],
            'right': [(777, 478), (800, 459), (903, 469)]
        }

        self.finial_reward_locs = [
            (660, 314), (554, 687), (1010, 794), (1117, 405), (806, 525)
        ]

        self.select_travel_relative_loc = (1090, 674)

        self.team_locations = [(374, 324), (604, 330), (837, 324)]
        self.team_loc = self.team_locations[team_id]
        self.start_team_loc = (1190, 797)
        self.start_game_relative_loc = (1240, 742)
        # self.start_point_relative_loc = (646, 712)

        self.options_loc = (1579, 920)
        self.surrender_loc = (815, 363)

        self.start_battle_loc = (1327, 454)
        self.check_team_loc = (674, 885 - 5)
        self.give_up_loc = (929, 706 - 5)
        self.give_up_cfm_loc = (712, 560 - 5)

        self.rewards_locs = {
            5: [(608, 706), (1034, 720), (1117, 371), (846, 311), (541, 430)],
            4: [(660, 314), (554, 687), (1010, 794), (1117, 405)],
            3: [(608, 706), (1034, 720), (846, 311)],
        }
        self.rewards_cfm_loc = (806, 525)
        self.cfm_done_loc = (790, 766)

        self.acc, self.state, self.no, self.reward_count = 0, '', '', 5
        self.empty_acc, self.member_ready_acc, self.buf_ready_acc = 0, 0, 0

    def give_up(self):
        time.sleep(0.6)
        x_click(self.check_team_loc)
        time.sleep(0.2)
        x_click(self.give_up_loc)
        time.sleep(0.2)
        x_click(self.give_up_cfm_loc)

    def esc_give_up(self):
        x_click(self.options_loc)
        time.sleep(0.1)
        x_click(self.surrender_loc)

    def mutil_click_start(self):
        x_click(self.start_game_relative_loc)
        time.sleep(0.5)
        x_click(self.start_game_relative_loc)
        time.sleep(0.5)
        x_click(self.start_game_relative_loc)
        time.sleep(0.5)
        x_click(self.start_game_relative_loc)
        time.sleep(0.5)
        x_click(self.start_game_relative_loc)

    def do_use_hero(self):
        if self.hero_cnt > 3:
            first_x, last_x, y = self.members_loc
            for i, idx in enumerate(self.heros_id):
                assert (self.hero_cnt - i - 1 > 0)
                dis = (last_x - first_x) // (self.hero_cnt - i - 1)
                loc = (first_x + dis * (idx - i), y)
                x_click(loc)
                x_moveTo(self.drag2loc)
                r_click()

    def do_treasure_list(self):
        treasure_loc_id = np.random.randint(0, 3)
        treasure_loc = self.treasure_locs[treasure_loc_id]
        x_click(treasure_loc)
        x_click(self.treasure_collect_loc)

    def do_skill_select(self):
        time.sleep(0.2)
        if self.hero_cnt == 1:
            mid_hero_loc = self.hero_relative_locs[1]
            x_click(mid_hero_loc)
            for idx, skill_id, target_id in zip([0, 1, 2], self.skills_id, self.targets_id):
                if idx != 1:
                    continue
                time.sleep(0.2)
                x_click(self.skill_relative_locs[skill_id])

                if target_id != -1:
                    x_click(self.enemy_mid_location)
            return 

        first_hero_loc = self.hero_relative_locs[0]
        x_click(first_hero_loc)
        for idx, skill_id, target_id in zip([0, 1, 2], self.skills_id, self.targets_id):
            time.sleep(0.2)
            x_click(self.skill_relative_locs[skill_id])

            if target_id != -1:
                x_click(self.enemy_mid_location)

            if self.hero_cnt == 2 and idx == 1:
                break

    def do_select_stranger(self):
        visitor_id = np.random.randint(0, 3)
        visitor_loc = self.visitor_locs[visitor_id]
        x_click(visitor_loc)
        x_click(self.visitor_choose_loc)

    def do_shutdown(self):
        autoshutdown = os.path.join(os.getcwd(), 'autoshutdown.bat')
        p = os.system("cmd.exe /c " + autoshutdown)
        
                    
    def run(self):
        # self.run_pve_break(no='2-6', for_jy=False)
        self.run_pve_full(no='1-1', reward_count=3, max_member_ready=99, max_buf_ready=99, ext_reward=True)

    def run_test(self):
        global rect

        delay = 2.5
        while True:
            time.sleep((np.random.rand() + delay) if delay > 0 else 0.3)

            states, rect = self.check_state()
            print(_t(), self.state + ':', states, self.empty_acc, self.member_ready_acc, self.buf_ready_acc, delay)

    def run_pve_full(self, no='2-6', reward_count=3, max_member_ready=2, max_buf_ready=3, ext_reward=False):
        global rect

        self.while_delay = self.while_delay / 3.0
        
        self.acc, self.state, self.no, self.reward_count = 0, '', no, reward_count
        delay, self.empty_acc, self.member_ready_acc, self.buf_ready_acc, is_first = 0.5, 0, 0, 0, True
        self.shutdown_acc = 0
        while True:
            time.sleep((np.random.rand() + delay) if delay > 0 else 0.3)
            states, rect = self.check_state(ext_buf = self.state != 'battle', ext_reward = ext_reward)

            delay = (delay + 0.1) if not states else delay
            self.empty_acc = (self.empty_acc + 1) if not states or 'cfm_done' in states else 0                
            delay = delay if delay < 3 else 3
            print(_t(), self.state + ':', states, self.empty_acc, self.member_ready_acc, self.buf_ready_acc, round(delay, 2))

            if self.empty_acc >= 10:
                self.empty_acc = 0
                self.give_up()
                set_top_window()
                self.shutdown_acc += 1
                if self.shutdown_acc >= 5:
                    self.do_shutdown()
                    break
                    
                continue
                    
            if 'boom' in states or 'blue_portal' in states or 'destroy' in states:
                self.give_up()
                continue
                
            map_not_ready = False
            is_empty = 'map_not_ready' in states or 'f-buf' in states or 'f-fh' in states  or 'stranger' in states
            if is_empty and 'start_point' not in states:
                self.state = 'map'
                map_not_ready = True
                for b_icon in ['b-fs', 'b-sp', 'b-zs', 'b-ck', 'b-fh', 'b-try']:
                    if b_icon in states:
                        if b_icon == 'b-try':
                            if self.member_ready_acc >= max_member_ready:
                                break
                            
                            r_moveTo(states[b_icon][0][0] + 15, states[b_icon][0][1])
                            r_click(states[b_icon][0][0] + 15, states[b_icon][0][1])
                        else:
                            self.buf_ready_acc += 1
                            r_moveTo(states[b_icon][0])
                            r_click(states[b_icon][0])
                        time.sleep(0.9)
                        x_moveTo(self.start_game_relative_loc)
                        r_click()
                        time.sleep(0.2)
                        r_click()
                        
                        if self.buf_ready_acc >= max_buf_ready:
                            time.sleep(0.9)
                            self.give_up()
                            
                        map_not_ready = False
                        break

            if map_not_ready:
                has_break = True

                time.sleep(1.6)
                new_states, rect = self.check_state(ext_buf=True, ext_reward=ext_reward)
                print(_t(), self.state + '_:', new_states, self.empty_acc, self.member_ready_acc, self.buf_ready_acc, round(delay, 2))

                if 'start_game' in new_states and 'map_not_ready' not in new_states and self.member_ready_acc < max_member_ready:
                    x_moveTo(self.start_game_relative_loc)
                    r_click()
                    time.sleep(10) if 'start_game' in new_states else time.sleep(1.0)
                    continue

                if 'boom' in new_states or 'blue_portal' in new_states or 'destroy' in new_states:
                    self.give_up()
                    continue

                if 'stranger' in new_states:
                    x_click(self.start_game_relative_loc)
                    time.sleep(0.3)
                    self.do_select_stranger()
                    time.sleep(0.9)
                    self.give_up()
                    continue
                    
                for b_icon in ['b-sp', 'b-fs', 'b-zs', 'b-ck', 'b-fh', 'b-try']:
                    if b_icon in new_states:
                        if b_icon == 'b-try':
                            if self.member_ready_acc >= max_member_ready:
                                break
                            
                            r_moveTo(new_states[b_icon][0][0] + 15, new_states[b_icon][0][1])
                            r_click(new_states[b_icon][0][0] + 15, new_states[b_icon][0][1])
                        else:
                            self.buf_ready_acc += 1
                            r_moveTo(new_states[b_icon][0])
                            r_click(new_states[b_icon][0])
                        time.sleep(0.5)
                        x_moveTo(self.start_game_relative_loc)
                        r_click()
                        time.sleep(0.2)
                        r_click()
                        
                        if self.buf_ready_acc >= max_buf_ready:
                            time.sleep(0.9)
                            self.give_up()

                        has_break = False
                        break


                if self.member_ready_acc >= max_member_ready or self.buf_ready_acc >= max_buf_ready:
                    time.sleep(0.9)
                    self.give_up()
                    continue

                    
                if has_break:
                    x_moveTo(self.start_game_relative_loc)
                    r_click()
                    if not ext_reward:
                        time.sleep(0.9)
                        self.give_up()
                    continue

            if self.no in states:
                self.state = 'map'
                self.member_ready_acc = 0
                self.buf_ready_acc = 0
                r_click(states[self.no][0])
                x_click(self.start_game_relative_loc)
                if not is_first:
                    self.mutil_click_start()
                is_first = False
                self.shutdown_acc = 0
                continue

            if 'visitor_list' in states:
                self.state = 'map'
                self.do_select_stranger()
                time.sleep(0.9)
                self.give_up()
                continue

            if 'start_point' in states:
                self.state = 'map'
                    
            if 'team_list' in states:
                self.state = 'map'
                self.member_ready_acc = 0
                self.buf_ready_acc = 0
                
                x_click(self.team_loc)
                if 'team_lock' in states:
                    r_click(states['team_lock'][0])
                x_click(self.start_team_loc)
                time.sleep(0.3)
                continue

            if 'member_ready' in states:
                self.state = 'battle'
                self.do_use_hero()
                r_click(states['member_ready'][0])
                self.member_ready_acc += 1
                delay = -0.5
                continue

            if 'battle_ready' in states:
                self.state = 'battle'
                r_click(states['battle_ready'][0])
                continue

            if 'treasure_list' in states or 'treasure_replace' in states:
                self.state = 'map'
                self.do_treasure_list()

                if self.member_ready_acc >= max_member_ready + 1 or self.buf_ready_acc >= max_buf_ready:
                    time.sleep(0.9)
                    self.give_up()
                    
                continue

            if 'skill_select' in states or 'not_ready_dots' in states:
                self.state = 'battle'
                x_click(self.start_game_relative_loc)
                time.sleep(0.1)
                self.do_skill_select()
                time.sleep(0.1)
                x_click(self.start_battle_loc)
                continue

            if 'final_reward' in states or 'final_reward2' in states:
                reward_locs = self.rewards_locs[self.reward_count]
                for loc in reward_locs:
                    x_moveTo(loc)
                    r_click()

                time.sleep(0.3)
                x_moveTo(self.rewards_cfm_loc)
                r_click()
                [x_click(self.start_game_relative_loc) for _ in range(5)]

                self.member_ready_acc = 0
                self.buf_ready_acc = 0
                self.shutdown_acc = 0
                
                time.sleep(0.3)
                x_click(self.cfm_done_loc)
                continue

            if 'cfm_done' in states:
                r_click(states['cfm_done'][0])
                continue

            if 'cfm_reward' in states:
                r_click(states['cfm_reward'][0])
                continue
                
            x_moveTo(self.start_game_relative_loc)
            r_click()
            time.sleep(10) if 'start_game' in states else time.sleep(self.while_delay)

    def run_pve_break(self, no='2-5', for_jy=False):
        global rect

        self.acc, self.state, self.no = 0, '', no
        delay, self.empty_acc, is_first = 0.5, 0, True
        last_states = {}
        while True:
            time.sleep((np.random.rand() + delay) if delay > 0 else 0.3)
            states, rect = self.check_state()

            delay = (delay + 0.1) if not states else delay
            self.empty_acc = (self.empty_acc + 1) if not states or 'cfm_done' in states else 0
            delay = delay if delay < 3 else 3
            print(_t(), 'states:', states, self.empty_acc, round(delay, 2))

            if self.empty_acc >= 10:
                self.empty_acc = 0
                self.give_up()
                continue

            if 'map_not_ready' in states and 'start_point' not in states:
                if last_states and 'treasure_list' in last_states:
                    self.give_up()
                    continue

                time.sleep(1.5)
                new_states, rect = self.check_state()
                print(_t(), 'states_:', new_states, self.empty_acc, round(delay, 2))

                x_moveTo(self.start_game_relative_loc)
                r_click()

                if 'start_game' in new_states or not new_states:
                    time.sleep(10) if 'start_game' in new_states else time.sleep(self.while_delay)
                else:
                    self.give_up()
                    continue

            last_states = states

            if self.no in states:
                r_click(states[self.no][0])
                x_click(self.start_game_relative_loc)
                if not is_first:
                    self.mutil_click_start()
                is_first = False
                continue

            if 'team_list' in states:
                x_click(self.team_loc)
                if 'team_lock' in states:
                    r_click(states['team_lock'][0])
                x_click(self.start_team_loc)
                time.sleep(0.3)
                continue

            if 'member_ready' in states:
                self.do_use_hero()
                r_click(states['member_ready'][0])
                delay = -0.5
                continue

            if 'battle_ready' in states:
                r_click(states['battle_ready'][0])
                continue

            if 'treasure_list' in states or 'treasure_replace' in states:
                self.do_treasure_list()
                time.sleep(0.9)
                self.give_up()
                [x_click(self.start_game_relative_loc) for _ in range(5)]
                continue

            if 'skill_select' in states or 'not_ready_dots' in states:
                x_click(self.start_game_relative_loc)
                time.sleep(0.2)
                if for_jy:
                    time.sleep(23.2)
                self.do_skill_select()
                time.sleep(0.2)
                x_click(self.start_battle_loc)
                continue

            x_moveTo(self.start_game_relative_loc)
            r_click()

            time.sleep(10) if 'start_game' in states else time.sleep(self.while_delay)

    def check_state(self, ext_buf=False, ext_sp=None, ext_reward=None):
        self.acc += 1

        if ext_sp is None:
            ext_sp = self.no != '1-1' and ext_buf

        if ext_reward is None:
            ext_reward = self.no == '1-1'
            
        lushi, image = find_lushi_window()
        output_list = {}
        try_keys = ['battle_ready', 'member_ready', 'treasure_list', 'treasure_replace', 'skill_select', 'not_ready_dots', self.no]
        try_keys = (try_keys + ['visitor_list']) if ext_sp else try_keys

        ext_keys = []
        if self.no == '1-1':
            ext_keys = (ext_keys + ['b-fh', 'b-try', 'f-fh']) if ext_buf else ext_keys
        else:
            ext_keys = (ext_keys + ['b-fh', 'b-zs', 'b-fs', 'b-ck', 'b-try', 'f-fh', 'f-buf']) if ext_buf else ext_keys
            
        ext_keys = (['b-sp', ] + ext_keys + ['stranger', 'blue_portal', 'destroy', 'boom']) if ext_sp else ext_keys
        
        try_keys = (try_keys + ['final_reward', 'final_reward2', 'cfm_done', 'cfm_reward']) if ext_reward else try_keys
        base_keys = ['start_game', 'map_not_ready', 'start_point']
        base_keys = (base_keys + ['team_lock', 'team_list']) if self.acc < 90 else base_keys

        need_keys = try_keys + base_keys + ext_keys
        first_check = [(kk, self.icons[kk]) for kk in try_keys if kk in self.icons]
        second_check = [(kk, self.icons[kk]) for kk in need_keys if kk not in first_check and kk in self.icons]

        for k, v in first_check:
            success, click_loc, conf = self.find_icon(k, v, lushi, image)
            if success:
                output_list[k] = (click_loc, conf)
                return output_list, lushi

        for k, v in second_check:
            pre = ''
            pre = 'b-' if k.startswith('b-') else pre
            pre = 'f-' if k.startswith('f-') else pre

            if pre and pre in output_list:
                continue
                
            success, click_loc, conf = self.find_icon(k, v, lushi, image)
            if success:
                output_list[k] = (click_loc, conf)
                if pre:
                    output_list[pre] = (click_loc, conf)

        return output_list, lushi

    def find_icon(self, k, icon, lushi, image):
        success, X, Y, conf = find_icon_location(k, image, icon)
        if success:
            click_loc = (X + lushi[0], Y + lushi[1])
        else:
            click_loc = None
        return success, click_loc, conf


def main():
    pyautogui.confirm(text="请启动炉石，将炉石调至窗口模式，分辨率设为1600x900，画质设为高 参考 config.txt 修改配置文件")

    with open('config.txt', 'r', encoding='utf-8') as f:
        lines = f.readlines()

    team_id, heros_id, skills_id, targets_id, while_delay, delay = lines

    heros_id = [int(s.strip()) for s in heros_id.strip().split(' ') if not s.startswith('#')]
    skills_id = [int(s.strip()) for s in skills_id.strip().split(' ') if not s.startswith('#')]
    targets_id = [int(s.strip()) for s in targets_id.strip().split(' ') if not s.startswith('#')]
    team_id, hero_cnt = [int(s.strip()) for s in team_id.strip().split(' ') if not s.startswith('#')]
    while_delay = float(while_delay.split('#')[0].strip())
    delay = float(delay.split('#')[0].strip())

    print(_t(), 'heros_id:', heros_id, 'skills_id:', skills_id)
    assert (len(skills_id) == 3 and len(targets_id) == 3 and len(heros_id) == 3)
    assert (team_id in [0, 1, 2] and hero_cnt <= 6)

    pyautogui.PAUSE = delay

    agent = Agent(team_id=team_id, heros_id=heros_id, skills_id=skills_id, targets_id=targets_id, hero_cnt=hero_cnt,
                  while_delay=while_delay)
    agent.run()


if __name__ == '__main__':
    main()