"""Opponent comment system inspired by the comedy script."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .game import Game, Player


@dataclass
class Commentator:
    """Generates witty feedback based on game events."""

    rng: random.Random = field(default_factory=random.Random)

    def comment_on_move(self, game: "Game", coord: Tuple[int, int]) -> str:
        row, col = coord
        column_label = chr(ord("A") + col)
        opponent = game.current_player.opponent
        templates = self._move_templates(game.player_alias(opponent))
        line = self.rng.choice(templates)
        return line.replace("{coord}", f"{column_label}{row}")

    def comment_on_skill(self, skill_name: str) -> str:
        templates = self._skill_templates(skill_name)
        return self.rng.choice(templates)

    def comment_on_overlay(self, result: str) -> List[str]:
        options = self._overlay_templates(result)
        return self.rng.choice(options)

    def _move_templates(self, speaker_label: str) -> List[str]:
        return [
            f"{speaker_label}：老师你好像快输了——再挺挺？",
            "技能五：问得好！虽然我没问，但我还是要点评一下。",
            "子棋：挺胸提臀，稳住，这手落子还有转机。",
            "技能五：别瞪子棋，眼神放在棋盘上！",
            "子棋：这颗落在 {coord}，嗯……老师快表演技能了没？",
            "张呈：有人吗？有人吗？哦，原来落子在 {coord}！",
            "技能五：外练筋骨皮，内练五子棋——先把 {coord} 卡住！",
            "子棋：老师，这手有点要爆了的感觉！",
            "技能五：别喊，棋子已经稳稳拍在 {coord}。",
            "张呈：你们这是传统五子棋还是要给我随机技能？",
            "子棋：请！落子 {coord}，老师别再把棋子扔什刹海了。",
            "技能五：问得好，这步棋为下一次飞沙走石做准备。",
            "王金宝：下棋就是为了赢？那你把 {coord} 先占上。",
            "技能五：呀嘞呀嘞，这颗小子居然落在 {coord}。",
            "张呈：我只是九年义务教育，但我知道 {coord} 很关键。",
            "子棋：老师，我是不是得再喊一声“请”才能跟上这一手？",
            "技能五：孩子，你有多久没有边唱边落在 {coord} 了？",
            "张呈：这叫棒球？不，这是棋子滑进 {coord} 的完美弧线。",
            "技能五：擒住天地之精华，也别忘了抓稳 {coord}。",
            "子棋：老师，你别再假装听不见，这手已经落下去了！",
        ]

    def _skill_templates(self, skill_name: str) -> List[str]:
        base: Dict[str, List[str]] = {
            "飞沙走石": [
                "技能五：飞沙走石！棋子直接扔进什刹海，别问就丢。",
                "张呈：飞沙走石？没问啊！哪有什刹海？你这叫棒球！",
                "子棋：老师一喊‘请’，飞沙走石就把对手棋子送去旅行了。",
                "技能五&子棋：嘿嘿吼嘿哈——飞沙又走石！",
                "王金宝：老王的学生可没教过飞沙走石这么乱扔，但气势很足。",
            ],
            "静如止水": [
                "子棋：静如止水！老师已经完全动不了了。",
                "技能五：问得好——静如止水把时间都凝结住了，先别喊。",
                "张呈：静如止水这啥意思呀？老师多久能活？我先走了啊。",
                "技能五：外练筋骨皮，内练静如止水，这把稳。",
                "王金宝：小子，静如止水把人冻住可不算赢，算是闹腾。",
            ],
            "力拔山兮": [
                "技能五：力拔山兮！棋盘清空，顺便把地也拖了。",
                "张呈：力拔山兮还能算下棋吗？你这是寻衅滋事。",
                "子棋：老师不在就开不了学，这一招力拔山兮太耍赖。",
                "技能五&子棋：呀嘞呀嘞——力拔山兮棋子全没了。",
                "王金宝：胜天半子，也得留点子吧？力拔山兮太狠。",
            ],
            "擒擒拿拿": [
                "技能五：擒拿擒拿，擒擒又拿拿，擒擒拿拿让棋子搬家笑哈哈。",
                "张呈：擒擒拿拿我没使劲，你别喊疼！",
                "子棋：这是我和校长的擒擒拿拿组合技，厉害吧？",
                "技能五：擒住天地之精华，擒擒拿拿顺便拿走对面的气势。",
                "张呈：你说这是擒擒拿拿技能，我怎么听着像按摩？",
            ],
        }
        fallback = ["技能五：问得好！这技能我都想学。"]
        return base.get(skill_name, fallback)

    def _overlay_templates(self, result: str) -> List[List[str]]:
        victory_black = [
            [
                "技能五：孩子，你现在明白五子棋的真谛了吗？",
                "王金宝：外练筋骨皮，内练五子棋——老王的教学没白忙。",
            ],
            [
                "张呈：老师，这么玩真能赢？居然真的赢了！",
                "技能五：问得好，这把就是要爆了，老师先别走！",
            ],
            [
                "技能五：Super idol 的笑容都没你甜，笑一个吧！",
                "张呈：别唱了，老师，先把奖杯给我。",
            ],
            [
                "王金宝：胜天半子，徒弟，这一手漂亮，老师在旁边都乐坏了。",
                "技能五：呀嘞呀嘞，这学生把老师都震惊了。",
            ],
        ]

        victory_white = [
            [
                "张呈：老师你好像快输了！",
                "技能五：冷静，飞沙走石还能再来一遍吗？",
            ],
            [
                "技能五：老王的学生今天状态不在线啊。",
                "子棋：老师，我是不是得再梅开二度？",
            ],
            [
                "王金宝：张呈，站起来！老师还等着看你翻盘。",
                "张呈：教练，我坐高铁来的，不是来挨打的！",
            ],
            [
                "技能五：问得好，可惜答案是‘再来一把’。",
                "子棋：老师，你都被定住了，还能喊？",
            ],
        ]

        draw_options = [
            [
                "子棋：平局？那我们再挺胸提臀重来！",
                "技能五：真正的技能在心里，老师先喘口气再继续。",
            ],
            [
                "张呈：这叫传统五子棋的疲劳期。",
                "技能五：要爆了的感觉还差一点，老师再喊一声请。",
            ],
            [
                "技能五：问得好，平局也要唱歌跳舞吗老师？",
                "王金宝：孩子，老王在这儿教你笑一个。",
            ],
        ]

        fallback = [
            ["技能五：问得好！老师说继续下一局。"],
            ["子棋：老师，他又喊人吗？不管了，继续请！"],
        ]

        if result == "victory_black":
            return victory_black
        if result == "victory_white":
            return victory_white
        if result == "draw":
            return draw_options
        return fallback
