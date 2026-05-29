# ============================================================
# WORLD TRIGGER BORDER BOT – Complete Turn‑Based Tactical Edition
# ============================================================
import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import asyncio
import json
import random
import time
import os
import traceback
from dotenv import load_dotenv

# ============================================================
# CONFIG
# ============================================================
load_dotenv()
TOKEN   = os.getenv("TOKEN")
DB_NAME = "world_trigger.db"
COLOR   = 0x1abc9c

# ============================================================
# DATA — FACTIONS
# ============================================================
FACTIONS = {
    "Kido": {
        "emoji": "🛡️",
        "description": "Believe all Neighbors are enemies and must be completely destroyed.",
        "buffs": {"attack": 1}
    },
    "Shinoda": {
        "emoji": "⚖️",
        "description": "Neutral; prioritize immediate safety of citizens without anti-Neighbor prejudice.",
        "buffs": {"defense": 1}
    },
    "Tamakoma": {
        "emoji": "🌟",
        "description": "Believe some Neighbors are good; seek to befriend them and form alliances.",
        "buffs": {"mobility": 1}
    }
}

# ============================================================
# DATA — CLASSES
# ============================================================
CLASSES = {
    "Attacker":    {"emoji": "⚔️",  "strong_against": "Sniper",
                    "description": "Close combat specialist. Closes distance quickly to overwhelm snipers."},
    "Sniper":      {"emoji": "🎯",  "strong_against": "Gunner",
                    "description": "Long-range precision. Outranges and punishes gunner positioning."},
    "Gunner":      {"emoji": "🔫",  "strong_against": "Shooter",
                    "description": "Accurate suppressive fire. More reliable than unpredictable shooter trajectories."},
    "Shooter":     {"emoji": "💥",  "strong_against": "All Rounder",
                    "description": "Unpredictable trajectories that overwhelm balanced all-rounders."},
    "All Rounder": {"emoji": "🌟",  "strong_against": "Attacker",
                    "description": "Versatile and adaptive. Handles close combat rushdown with ease."},
}
CLASS_ADVANTAGE_MULT = 1.3

# ============================================================
# DATA — TRIGGERS (now with skill trees / moves)
# ============================================================
TRIGGERS = {
    # Main triggers
    "Kogetsu": {
        "price": 80, "trion_cost": 2, "type": "main",
        "buffs": {"attack": 5, "defense": 1},
        "moves": [
            {"name": "Slash",         "dmg": 1.0, "cost": 0, "level": 1},
            {"name": "Senkū (Extend)", "dmg": 1.5, "cost": 1, "level": 3},
            {"name": "Whirlwind",     "dmg": 1.8, "cost": 2, "level": 5}
        ]
    },
    "Raygust": {
        "price": 90, "trion_cost": 3, "type": "main",
        "buffs": {"attack": 3, "defense": 4},
        "moves": [
            {"name": "Shield Bash",   "dmg": 0.8, "cost": 0, "level": 1},
            {"name": "Raygust Slash", "dmg": 1.2, "cost": 1, "level": 2},
            {"name": "Full Guard",    "defend": 2.0, "cost": 2, "level": 4}  # Full Guard is a defend move
        ]
    },
    "Scorpion": {
        "price": 100, "trion_cost": 2, "type": "main",
        "buffs": {"attack": 4, "mobility": 3},
        "moves": [
            {"name": "Sting",        "dmg": 1.2, "cost": 0, "level": 1},
            {"name": "Mole Claw",    "dmg": 1.5, "cost": 1, "level": 2},
            {"name": "Scorpion Pin", "dmg": 1.7, "cost": 2, "level": 4}
        ]
    },
    "Asteroid": {
        "price": 50, "trion_cost": 1, "type": "main",
        "buffs": {"attack": 3},
        "moves": [
            {"name": "Asteroid Shot", "dmg": 1.0, "cost": 0, "level": 1},
            {"name": "Rapid Fire",    "dmg": 1.3, "cost": 1, "level": 2},
            {"name": "Full Burst",    "dmg": 1.6, "cost": 2, "level": 4}
        ]
    },
    "Meteor": {
        "price": 80, "trion_cost": 3, "type": "main",
        "buffs": {"attack": 5, "trion_control": 1},
        "moves": [
            {"name": "Meteor Bomb",  "dmg": 1.2, "cost": 0, "level": 1},
            {"name": "Meteor Storm", "dmg": 1.5, "cost": 1, "level": 2},
            {"name": "Meteor Crash", "dmg": 1.9, "cost": 2, "level": 5}
        ]
    },
    "Hound": {
        "price": 90, "trion_cost": 2, "type": "main",
        "buffs": {"attack": 4, "intelligence": 1},
        "moves": [
            {"name": "Hound Chaser", "dmg": 1.1, "cost": 0, "level": 1},
            {"name": "Hound Volley", "dmg": 1.4, "cost": 1, "level": 2},
            {"name": "Hound Swarm",  "dmg": 1.6, "cost": 2, "level": 4}
        ]
    },
    "Viper": {
        "price": 120, "trion_cost": 3, "type": "main",
        "buffs": {"attack": 4, "intelligence": 2},
        "moves": [
            {"name": "Viper Bite",   "dmg": 1.2, "cost": 0, "level": 1},
            {"name": "Viper Path",   "dmg": 1.5, "cost": 1, "level": 2},
            {"name": "Viper Cage",   "dmg": 1.8, "cost": 2, "level": 4}
        ]
    },
    "Ibis": {
        "price": 150, "trion_cost": 5, "type": "main",
        "buffs": {"attack": 8, "trion_control": 2},
        "moves": [
            {"name": "Ibis Pierce",  "dmg": 1.5, "cost": 0, "level": 1},
            {"name": "Ibis Break",   "dmg": 2.0, "cost": 2, "level": 3},
            {"name": "Ibis Siege",   "dmg": 2.5, "cost": 3, "level": 5}
        ]
    },
    "Egret": {
        "price": 100, "trion_cost": 3, "type": "main",
        "buffs": {"attack": 5, "perception": 1},
        "moves": [
            {"name": "Egret Snipe",  "dmg": 1.2, "cost": 0, "level": 1},
            {"name": "Egret Focus",  "dmg": 1.5, "cost": 1, "level": 2},
            {"name": "Egret Eagle",  "dmg": 1.8, "cost": 2, "level": 4}
        ]
    },
    "Lightning": {
        "price": 80, "trion_cost": 2, "type": "main",
        "buffs": {"attack": 4, "mobility": 1},
        "moves": [
            {"name": "Lightning Bolt", "dmg": 1.1, "cost": 0, "level": 1},
            {"name": "Lightning Flash","dmg": 1.4, "cost": 1, "level": 2},
            {"name": "Lightning Storm","dmg": 1.7, "cost": 2, "level": 4}
        ]
    },
    # Optional triggers (no moves, just passives)
    "Grasshopper":    {"price": 60,  "trion_cost": 1, "type": "optional", "buffs": {"mobility": 5}, "moves": []},
    "Bagworm":        {"price": 50,  "trion_cost": 1, "type": "optional", "buffs": {"evasion": 3, "mobility": 1}, "moves": []},
    "Shield":         {"price": 40,  "trion_cost": 1, "type": "optional", "buffs": {"defense": 4}, "moves": []},
    "Chameleon":      {"price": 90,  "trion_cost": 2, "type": "optional", "buffs": {"evasion": 5}, "moves": []},
    "Spider":         {"price": 70,  "trion_cost": 2, "type": "optional", "buffs": {"attack": 2, "intelligence": 1}, "moves": []},
    "Escudo":         {"price": 75,  "trion_cost": 2, "type": "optional", "buffs": {"defense": 5, "attack": 1}, "moves": []},
    "Thruster":       {"price": 80,  "trion_cost": 2, "type": "optional", "buffs": {"mobility": 4, "attack": 1}, "moves": []},
    "Silencer":       {"price": 60,  "trion_cost": 1, "type": "optional", "buffs": {"evasion": 2, "perception": 1}, "moves": []},
    "Dummy Beacon":   {"price": 55,  "trion_cost": 1, "type": "optional", "buffs": {"intelligence": 3}, "moves": []},
    "Shadow Cloak":   {"price": 120, "trion_cost": 2, "type": "optional", "buffs": {"evasion": 5}, "moves": []},
    "Wallbreaker":    {"price": 70,  "trion_cost": 1, "type": "optional", "buffs": {"attack": 3}, "moves": []},
}

# ============================================================
# DATA — NEIGHBORS (weakened)
# ============================================================
NEIGHBORS = {
    "Bamster": {"hp": 30, "damage": 6},
    "Marmod":  {"hp": 25, "damage": 8},
    "Rabbit":  {"hp": 40, "damage": 10},
    "Ilgar":   {"hp": 35, "damage": 9},
    "Bander":  {"hp": 28, "damage": 7},
    "Rad":     {"hp": 10, "damage": 3},
    "Dog":     {"hp": 20, "damage": 5},
    "Idra":    {"hp": 25, "damage": 6},
}

def random_neighbor():
    name  = random.choice(list(NEIGHBORS.keys()))
    stats = NEIGHBORS[name]
    return name, stats["hp"], stats["damage"]

# ============================================================
# DATA — SIDE EFFECTS
# ============================================================
COMMON_EFFECTS = [
    {"name": "Enhanced Vision",   "buffs": {"perception": 1}},
    {"name": "Enhanced Hearing",  "buffs": {"perception": 1}},
    {"name": "Emotion Detection", "buffs": {"intelligence": 1}},
    {"name": "Quick Reflexes",    "buffs": {"mobility": 1}},
    {"name": "Adaptive Thinking", "buffs": {"intelligence": 1}},
]
RARE_EFFECTS = [
    {"name": "Future Sight",     "buffs": {"attack": 2, "intelligence": 2}},
    {"name": "Lie Detection",    "buffs": {"intelligence": 2, "perception": 2}},
    {"name": "Combat Instinct",  "buffs": {"attack": 2, "mobility": 1}, "passive": "crit"},
    {"name": "Trion Efficiency", "buffs": {"trion_control": 2}},
    {"name": "Sniper Precision", "buffs": {"attack": 2, "perception": 1}},
    {"name": "Battle Foresight", "buffs": {"intelligence": 2, "mobility": 1}},
    {"name": "Enhanced Agility", "buffs": {"mobility": 2}},
]

def roll_side_effect():
    if random.random() <= 0.6:
        return random.choice(COMMON_EFFECTS) if random.random() <= 0.85 else random.choice(RARE_EFFECTS)
    return None

# ============================================================
# DATA — TRION
# ============================================================
def roll_trion():
    roll = random.randint(1, 100)
    if roll <= 50:  return random.randint(2, 6)
    if roll <= 85:  return random.randint(7, 12)
    if roll <= 97:  return random.randint(13, 20)
    return random.randint(21, 38)

# ============================================================
# DATA — STAT CAPS PER RANK
# ============================================================
RANK_CAPS = {
    "C-Rank": {"elo_min": 0,    "elo_max": 1199, "cap": 15},
    "B-Rank": {"elo_min": 1200, "elo_max": 1599, "cap": 30},
    "A-Rank": {"elo_min": 1600, "elo_max": 9999, "cap": 50},
}

def get_rank(elo):
    if elo >= 1600: return "A-Rank"
    if elo >= 1200: return "B-Rank"
    return "C-Rank"

def get_stat_cap(elo):
    return RANK_CAPS[get_rank(elo)]["cap"]

# ============================================================
# UTILITY — ELO
# ============================================================
def win_elo(current):
    return current + random.randint(15, 30)

def lose_elo(current):
    return max(current - random.randint(15, 30), 0)

# ============================================================
# UTILITY — DAMAGE CALCULATION (now with move support)
# ============================================================
async def calculate_damage(user_id, trion, side_effect=None, triggers=None, stats=None,
                            attacker_class=None, defender_class=None, faction=None, move=None):
    if stats is None:
        stats = {"attack": 1, "defense": 1, "mobility": 1,
                 "intelligence": 1, "trion_control": 1, "perception": 1}

    base            = trion * 10
    buff            = 0
    remaining_trion = trion

    if side_effect:
        for stat, value in side_effect.get("buffs", {}).items():
            weights = {"attack": 5, "mobility": 2, "perception": 2,
                       "intelligence": 3, "trion_control": 4, "defense": 1, "evasion": 1}
            buff += value * weights.get(stat, 1)

    if triggers:
        for trig_name in triggers:
            trig = TRIGGERS.get(trig_name)
            if not trig:
                continue
            cost = trig.get("trion_cost", 0)
            if remaining_trion >= cost:
                remaining_trion -= cost
                for stat, value in trig.get("buffs", {}).items():
                    weights = {"attack": 5, "mobility": 2, "defense": 3,
                               "evasion": 1, "intelligence": 3, "trion_control": 4, "perception": 2}
                    buff += value * weights.get(stat, 1)

    if faction and faction in FACTIONS:
        faction_buffs = FACTIONS[faction].get("buffs", {})
        for stat, value in faction_buffs.items():
            weights = {"attack": 5, "defense": 1, "mobility": 2,
                       "intelligence": 3, "trion_control": 4, "perception": 2}
            buff += value * weights.get(stat, 1)

    buff += stats.get("attack", 1)        * 5
    buff += stats.get("mobility", 1)      * 2
    buff += stats.get("intelligence", 1)  * 3
    buff += stats.get("trion_control", 1) * 4
    buff += stats.get("perception", 1)    * 2
    buff += stats.get("defense", 1)       * 1

    damage = base + buff + random.randint(0, 10)

    # Apply move multiplier
    if move and "dmg" in move:
        damage *= move["dmg"]

    if side_effect and side_effect.get("passive") == "crit":
        if random.random() < 0.2:
            damage *= 1.5

    if attacker_class and defender_class:
        cls = CLASSES.get(attacker_class)
        if cls and cls["strong_against"] == defender_class:
            damage *= CLASS_ADVANTAGE_MULT

    return int(damage)

# ============================================================
# UTILITY — TRIGGER MASTERY
# ============================================================
async def gain_trigger_xp(db, user_id, trigger_name, amount=10):
    await db.execute(
        "INSERT INTO trigger_mastery (user_id, trigger, xp, level) VALUES (?,?,?,?) "
        "ON CONFLICT(user_id, trigger) DO UPDATE SET xp = xp + ?",
        (user_id, trigger_name, amount, 1, amount)
    )
    cursor = await db.execute(
        "SELECT xp, level FROM trigger_mastery WHERE user_id=? AND trigger=?",
        (user_id, trigger_name)
    )
    xp, level = await cursor.fetchone()
    new_level = 1 + xp // 100
    if new_level > level:
        await db.execute(
            "UPDATE trigger_mastery SET level = ? WHERE user_id=? AND trigger=?",
            (new_level, user_id, trigger_name)
        )

# ============================================================
# TURN‑BASED BATTLE VIEW (PvE)
# ============================================================
class TurnBattleView(discord.ui.View):
    def __init__(self, ctx, player, ai, callback):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.player = player      # dict with user, name, trion, base_trion, stats, triggers, class, faction, side_effect, mastery
        self.ai = ai              # dict with name, trion, damage
        self.turn = 1
        self.battle_log = []
        self.callback = callback  # async function to call when battle ends
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        main_trig = None
        for trig in self.player["triggers"]:
            if TRIGGERS.get(trig) and TRIGGERS[trig]["type"] == "main":
                main_trig = trig
                break
        if not main_trig:
            self.add_item(discord.ui.Button(label="No attacks available", disabled=True))
            return

        trig_data = TRIGGERS[main_trig]
        moves = trig_data.get("moves", [])
        player_mastery = self.player["mastery"].get(main_trig, 1)
        available_moves = [m for m in moves if m["level"] <= player_mastery]
        if not available_moves:
            available_moves = [m for m in moves if m["level"] == 1]  # fallback

        for move in available_moves:
            label = f"{move['name']} (⚡{move.get('cost',0)})"
            self.add_item(discord.ui.Button(label=label, style=discord.ButtonStyle.primary,
                                            custom_id=f"move_{move['name']}"))

        self.add_item(discord.ui.Button(label="🛡 Defend", style=discord.ButtonStyle.secondary,
                                        custom_id="defend"))
        self.add_item(discord.ui.Button(label="🚀 Bail Out", style=discord.ButtonStyle.danger,
                                        custom_id="bailout"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.player["user"].id

    @discord.ui.button(custom_id="move_placeholder", label="Placeholder", style=discord.ButtonStyle.primary, row=4)
    async def move_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        # This button is never actually shown; we use dynamic buttons with custom callbacks.
        # Instead, we handle interactions via the view's on_interaction event.
        pass

    async def on_interaction(self, interaction: discord.Interaction):
        custom_id = interaction.data["custom_id"]
        if custom_id.startswith("move_"):
            move_name = custom_id[5:]  # Remove "move_" prefix
            await self.handle_move(interaction, move_name)
        elif custom_id == "defend":
            await self.handle_defend(interaction)
        elif custom_id == "bailout":
            await self.handle_bailout(interaction)

    async def handle_move(self, interaction, move_name):
        main_trig = next((t for t in self.player["triggers"] if TRIGGERS.get(t) and TRIGGERS[t]["type"] == "main"), None)
        if not main_trig:
            await interaction.response.send_message("No main trigger equipped!", ephemeral=True)
            return
        moves = TRIGGERS[main_trig]["moves"]
        move = next((m for m in moves if m["name"] == move_name), None)
        if not move:
            await interaction.response.send_message("Invalid move.", ephemeral=True)
            return

        cost = move.get("cost", 0)
        if self.player["trion"] < cost:
            await interaction.response.send_message("Not enough trion!", ephemeral=True)
            return

        self.player["trion"] -= cost
        player_dmg = await calculate_damage(
            self.player["user"].id, self.player["base_trion"],
            side_effect=self.player["side_effect"],
            triggers=self.player["triggers"],
            stats=self.player["stats"],
            attacker_class=self.player["class"],
            defender_class=None,
            faction=self.player["faction"],
            move=move
        )
        self.ai["trion"] -= player_dmg
        log_entry = f"**{self.player['name']}** uses **{move_name}** and deals {player_dmg} damage."
        self.battle_log.append(log_entry)

        if self.ai["trion"] <= 0:
            self.ai["trion"] = 0
            await self.end_battle(interaction, True)
            return

        # AI turn
        ai_dmg = int(self.ai["damage"] * (1 + random.random()))
        self.player["trion"] -= ai_dmg
        log_ai = f"**{self.ai['name']}** attacks for {ai_dmg} damage."
        self.battle_log.append(log_ai)

        if self.player["trion"] <= 0:
            self.player["trion"] = 0
            await self.end_battle(interaction, False)
            return

        self.turn += 1
        self.update_buttons()
        await self.update_battle_message(interaction)

    async def handle_defend(self, interaction):
        ai_dmg = int(self.ai["damage"] * 0.5)
        self.player["trion"] -= ai_dmg
        log_entry = f"**{self.player['name']}** defends, reducing damage to {ai_dmg}."
        self.battle_log.append(log_entry)
        if self.player["trion"] <= 0:
            self.player["trion"] = 0
            await self.end_battle(interaction, False)
            return
        self.turn += 1
        self.update_buttons()
        await self.update_battle_message(interaction)

    async def handle_bailout(self, interaction):
        cost = max(1, self.player["trion"] // 3)
        self.player["trion"] -= cost
        self.battle_log.append(f"🚀 **{self.player['name']}** bails out! Lost {cost} Trion.")
        await self.end_battle(interaction, False, bailout=True)

    async def update_battle_message(self, interaction):
        status = f"**Turn {self.turn}**\n"
        status += f"🛡️ {self.player['name']}: {self.player['trion']} Trion\n"
        status += f"👾 {self.ai['name']}: {self.ai['trion']} HP\n\n"
        status += "\n".join(self.battle_log[-4:])
        await interaction.response.edit_message(content=status, view=self)

    async def end_battle(self, interaction, player_won, bailout=False):
        for child in self.children:
            child.disabled = True
        result = "🏆 **You won!**" if player_won else "💀 **You lost!**"
        if bailout:
            result += " (Bailed Out)"
        status = f"**Battle End**\n🛡️ {self.player['name']}: {self.player['trion']} Trion\n"
        status += f"👾 {self.ai['name']}: {self.ai['trion']} HP\n\n"
        status += "\n".join(self.battle_log[-10:])
        status += f"\n\n{result}"
        await interaction.response.edit_message(content=status, view=self)
        self.stop()
        if self.callback:
            await self.callback(player_won, bailout, self.player["trion"])

# ============================================================
# TURN‑BASED DUEL VIEW (PvP)
# ============================================================
class DuelTurnView(discord.ui.View):
    def __init__(self, player1, player2, callback):
        super().__init__(timeout=180)
        self.player1 = player1
        self.player2 = player2
        self.current_player = player1
        self.turn = 1
        self.battle_log = []
        self.callback = callback
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        main_trig = None
        for trig in self.current_player["triggers"]:
            if TRIGGERS.get(trig) and TRIGGERS[trig]["type"] == "main":
                main_trig = trig
                break
        if not main_trig:
            self.add_item(discord.ui.Button(label="No attacks available", disabled=True))
            return

        trig_data = TRIGGERS[main_trig]
        moves = trig_data.get("moves", [])
        player_mastery = self.current_player["mastery"].get(main_trig, 1)
        available_moves = [m for m in moves if m["level"] <= player_mastery]
        if not available_moves:
            available_moves = [m for m in moves if m["level"] == 1]

        for move in available_moves:
            label = f"{move['name']} (⚡{move.get('cost',0)})"
            self.add_item(discord.ui.Button(label=label, style=discord.ButtonStyle.primary,
                                            custom_id=f"move_{move['name']}"))

        self.add_item(discord.ui.Button(label="🛡 Defend", style=discord.ButtonStyle.secondary,
                                        custom_id="defend"))
        self.add_item(discord.ui.Button(label="🚀 Bail Out", style=discord.ButtonStyle.danger,
                                        custom_id="bailout"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.current_player["user"].id

    async def on_interaction(self, interaction: discord.Interaction):
        custom_id = interaction.data["custom_id"]
        if custom_id.startswith("move_"):
            move_name = custom_id[5:]
            await self.handle_move(interaction, move_name)
        elif custom_id == "defend":
            await self.handle_defend(interaction)
        elif custom_id == "bailout":
            await self.handle_bailout(interaction)

    async def handle_move(self, interaction, move_name):
        attacker = self.current_player
        defender = self.player2 if attacker == self.player1 else self.player1

        main_trig = next((t for t in attacker["triggers"] if TRIGGERS.get(t) and TRIGGERS[t]["type"] == "main"), None)
        if not main_trig: return
        moves = TRIGGERS[main_trig]["moves"]
        move = next((m for m in moves if m["name"] == move_name), None)
        if not move: return

        cost = move.get("cost", 0)
        if attacker["trion"] < cost:
            await interaction.response.send_message("Not enough trion!", ephemeral=True)
            return

        attacker["trion"] -= cost
        dmg = await calculate_damage(
            attacker["user"].id, attacker["base_trion"],
            side_effect=attacker["side_effect"],
            triggers=attacker["triggers"],
            stats=attacker["stats"],
            attacker_class=attacker["class"],
            defender_class=defender["class"],
            faction=attacker["faction"],
            move=move
        )
        defender["trion"] -= dmg
        log_entry = f"**{attacker['name']}** uses **{move_name}** on {defender['name']} for {dmg} damage."
        self.battle_log.append(log_entry)

        if defender["trion"] <= 0:
            defender["trion"] = 0
            await self.end_battle(interaction, winner=attacker)
            return

        # Switch turn
        self.current_player = defender
        self.turn += 1
        self.update_buttons()
        await self.update_battle_message(interaction)

    async def handle_defend(self, interaction):
        attacker = self.current_player
        defender = self.player2 if attacker == self.player1 else self.player1
        # Defending: attacker does nothing, but receives reduced damage next turn?
        # For simplicity, defender simply takes no damage this turn and attacker does nothing?
        # Better: attacker skips attack, and defender gets a defensive buff for next turn.
        # We'll just skip attack and switch turn.
        log_entry = f"**{attacker['name']}** takes a defensive stance."
        self.battle_log.append(log_entry)
        self.current_player = defender
        self.turn += 1
        self.update_buttons()
        await self.update_battle_message(interaction)

    async def handle_bailout(self, interaction):
        attacker = self.current_player
        cost = max(1, attacker["trion"] // 3)
        attacker["trion"] -= cost
        self.battle_log.append(f"🚀 **{attacker['name']}** bails out! Lost {cost} Trion.")
        winner = self.player2 if attacker == self.player1 else self.player1
        await self.end_battle(interaction, winner=winner, bailout=True)

    async def update_battle_message(self, interaction):
        status = f"**Turn {self.turn}**\n"
        status += f"🛡️ {self.player1['name']}: {self.player1['trion']} Trion\n"
        status += f"🛡️ {self.player2['name']}: {self.player2['trion']} Trion\n\n"
        status += "\n".join(self.battle_log[-4:])
        await interaction.response.edit_message(content=status, view=self)

    async def end_battle(self, interaction, winner=None, bailout=False):
        for child in self.children:
            child.disabled = True
        if winner:
            result = f"🏆 **{winner['name']} wins!**"
        else:
            result = "It's a draw!"
        if bailout:
            result += " (Bail Out)"
        status = f"**Battle End**\n"
        status += f"🛡️ {self.player1['name']}: {self.player1['trion']} Trion\n"
        status += f"🛡️ {self.player2['name']}: {self.player2['trion']} Trion\n\n"
        status += "\n".join(self.battle_log[-10:])
        status += f"\n\n{result}"
        await interaction.response.edit_message(content=status, view=self)
        self.stop()
        if self.callback:
            await self.callback(winner, loser=self.player2 if winner == self.player1 else self.player1 if winner else None,
                                final_trion1=self.player1["trion"], final_trion2=self.player2["trion"])

# ============================================================
# DATABASE SETUP
# ============================================================
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                user_id INTEGER PRIMARY KEY,
                trion INTEGER DEFAULT 2,
                side_effect TEXT,
                spins INTEGER DEFAULT 0,
                credits INTEGER DEFAULT 0,
                elo INTEGER DEFAULT 1000,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                class TEXT DEFAULT NULL,
                faction TEXT DEFAULT NULL,
                expedition_end REAL DEFAULT 0
            )""")
        for col in ["class", "faction", "expedition_end"]:
            try:
                await db.execute(f"ALTER TABLE agents ADD COLUMN {col} TEXT DEFAULT NULL")
            except Exception:
                pass

        await db.execute("""
            CREATE TABLE IF NOT EXISTS triggers (
                user_id INTEGER,
                trigger TEXT,
                PRIMARY KEY (user_id, trigger)
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS loadouts (
                user_id INTEGER,
                trigger TEXT,
                slot TEXT,
                PRIMARY KEY (user_id, slot)
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS redeem_codes (
                code TEXT PRIMARY KEY,
                reward_type TEXT,
                reward_amount INTEGER,
                reward_trigger TEXT,
                max_uses INTEGER,
                expires TIMESTAMP
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS redeemed_codes (
                user_id INTEGER,
                code TEXT,
                PRIMARY KEY (user_id, code)
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS story_progress (
                user_id INTEGER PRIMARY KEY,
                arc TEXT DEFAULT 'Prologue',
                chapter INTEGER DEFAULT 1,
                mission INTEGER DEFAULT 1
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS story_missions (
                arc TEXT,
                chapter INTEGER,
                mission INTEGER,
                type TEXT,
                description TEXT,
                choices TEXT,
                reward_type TEXT,
                reward_amount INTEGER,
                reward_trigger TEXT,
                replayable INTEGER DEFAULT 0,
                PRIMARY KEY (arc, chapter, mission)
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS agent_stats (
                user_id INTEGER PRIMARY KEY,
                attack INTEGER DEFAULT 1,
                defense INTEGER DEFAULT 1,
                mobility INTEGER DEFAULT 1,
                intelligence INTEGER DEFAULT 1,
                trion_control INTEGER DEFAULT 1,
                perception INTEGER DEFAULT 1,
                stat_points INTEGER DEFAULT 0
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS squads (
                squad_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                leader_id INTEGER,
                division TEXT DEFAULT 'C-Rank',
                elo INTEGER DEFAULT 1000,
                operator TEXT DEFAULT NULL
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS squad_members (
                squad_id INTEGER,
                user_id INTEGER,
                role TEXT
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS trigger_mastery (
                user_id INTEGER,
                trigger TEXT,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                PRIMARY KEY (user_id, trigger)
            )""")
        await db.commit()

        cursor = await db.execute("SELECT COUNT(*) FROM story_missions")
        if (await cursor.fetchone())[0] == 0:
            await populate_story(db)
            await db.commit()
            print("✅ Story missions populated")

async def populate_story(db):
    arc = "Prologue"
    missions = [
        (1, 1, "exploration", "You arrive at Mikado City. Explore the area.", None, "credits", 50, None, 1),
        (1, 2, "choice", "You hear a suspicious signal. Investigate carefully or rush in?",
         json.dumps([{"id": "investigate", "label": "Investigate Carefully"}, {"id": "rush", "label": "Rush In"}]),
         "spins", 2, None, 0),
        (1, 3, "arena", "Neighbors are attacking civilians! Engage them!", None, "credits", 100, None, 0),
        (2, 1, "exploration", "Investigate a suspicious warehouse for clues.", None, "credits", 75, None, 1),
        (2, 2, "choice", "A civilian asks for help. Escort or continue?",
         json.dumps([{"id": "escort", "label": "Escort Civilian"}, {"id": "investigate", "label": "Continue Investigation"}]),
         "spins", 3, None, 0),
        (2, 3, "arena", "Defend against a small group of Neighbors!", None, "credits", 150, None, 0),
        (3, 1, "boss", "The main Neighbor threat appears! Boss battle!", None, "trigger", 1, "Grasshopper", 0),
    ]
    for chapter, mission, m_type, desc, choices, r_type, r_amount, r_trigger, replayable in missions:
        await db.execute("""
            INSERT OR REPLACE INTO story_missions
            (arc, chapter, mission, type, description, choices, reward_type, reward_amount, reward_trigger, replayable)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (arc, chapter, mission, m_type, desc, choices, r_type, r_amount, r_trigger, replayable))

# ============================================================
# REDEEM CODES FROM ENVIRONMENT
# ============================================================
redeem_codes = {}

def load_redeem_codes():
    global redeem_codes
    raw = os.getenv("REDEEM_CODES")
    if raw:
        try:
            redeem_codes = json.loads(raw)
            print(f"✅ Loaded {len(redeem_codes)} redeem codes")
        except Exception:
            print("❌ Invalid REDEEM_CODES JSON")
    else:
        print("ℹ️ No REDEEM_CODES environment variable found.")

# ============================================================
# BOT SETUP
# ============================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

_arena_cooldowns = {}
ARENA_COOLDOWN = 30
EXPEDITION_COOLDOWN = 4 * 3600  # 4 hours

LOADOUT_SLOTS = ["Main", "Sub", "Optional"]
MAIN_COMPATIBLE_SLOTS = ["Main", "Sub"]
OPT_COMPATIBLE_SLOTS = ["Optional"]

# ============================================================
# HELPER
# ============================================================
async def agent_required(interaction: discord.Interaction, db):
    cursor = await db.execute("SELECT user_id FROM agents WHERE user_id=?", (interaction.user.id,))
    if not await cursor.fetchone():
        await interaction.response.send_message("Use `/joinborder` first.", ephemeral=True)
        return False
    return True

async def check_expedition(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT expedition_end FROM agents WHERE user_id=?", (user_id,))
        row = await cursor.fetchone()
        if row and row[0] <= time.time():
            credits = random.randint(500, 2000)
            spins = random.randint(3, 10)
            await db.execute("UPDATE agents SET credits = credits + ?, spins = spins + ?, expedition_end = 0 WHERE user_id=?",
                             (credits, spins, user_id))
            await db.commit()
            return credits, spins
    return None, None

# ============================================================
# /help
# ============================================================
@bot.tree.command(name="help", description="Show all available commands")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="🛡️ Border Trigger Bot Commands", color=COLOR)
    embed.add_field(name="Getting Started", value="`/joinborder` `/setclass` `/faction` `/profile`", inline=False)
    embed.add_field(name="Combat (Turn‑Based!)", value="`/arena` `/duel` `/mission` `/bailout` `/combostats`", inline=False)
    embed.add_field(name="Story", value="`/story` `/storymission`", inline=False)
    embed.add_field(name="Expedition", value="`/expedition` (B‑Rank+)", inline=False)
    embed.add_field(name="Triggers & Shop", value="`/shop` `/buytrigger` `/equip` `/loadout`", inline=False)
    embed.add_field(name="Stats & Ranking", value="`/stats` `/upgradestat` `/trionrank` `/leaderboard`", inline=False)
    embed.add_field(name="Side Effects", value="`/sideeffects` `/spin`", inline=False)
    embed.add_field(name="Classes & Factions", value="`/classes` `/faction`", inline=False)
    embed.add_field(name="Squads & Operators", value="`/squadcreate` `/squadinvite` `/squadinfo` `/squadleave` `/operator`", inline=False)
    embed.add_field(name="Other", value="`/triggers_mastered` `/neighborhood` `/baseinfo` `/trainers` `/train` `/redeem`", inline=False)
    await interaction.response.send_message(embed=embed)

# ============================================================
# /joinborder
# ============================================================
@bot.tree.command(name="joinborder", description="Become a Border agent")
async def joinborder(interaction: discord.Interaction):
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        if await agent_required(interaction, db):
            await interaction.response.send_message(
                embed=discord.Embed(title="⚠️ Already Registered",
                                    description="You are already a Border agent.",
                                    color=0xe67e22), ephemeral=True)
            return

        trion = roll_trion()
        side = roll_side_effect()
        side_json = json.dumps(side) if side else None

        await db.execute(
            "INSERT OR IGNORE INTO agents (user_id,trion,side_effect,spins,credits,elo,wins,losses) VALUES (?,?,?,?,?,?,?,?)",
            (user_id, trion, side_json, 5, 100, 1000, 0, 0))
        await db.execute("INSERT OR IGNORE INTO agent_stats (user_id) VALUES (?)", (user_id,))
        await db.execute("INSERT OR IGNORE INTO story_progress (user_id) VALUES (?)", (user_id,))
        await db.commit()

    rarity = "Low" if trion <= 6 else "Average" if trion <= 12 else "High" if trion <= 20 else "EXTREMELY RARE"
    embed = discord.Embed(title="🛡 Border Agent Registered",
                          description=f"Welcome to Border, {interaction.user.display_name}.",
                          color=COLOR)
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.add_field(name="🔋 Trion Level", value=f"{trion} ({rarity})", inline=True)
    embed.add_field(name="🧬 Side Effect", value=side["name"] if side else "None", inline=True)
    embed.add_field(name="🎰 Spins", value=5, inline=True)
    embed.add_field(name="💳 Credits", value=100, inline=True)
    embed.add_field(name="⚔️ Next Step", value="Use `/setclass` and `/faction`", inline=False)
    await interaction.response.send_message(embed=embed)

# ============================================================
# /setclass
# ============================================================
@bot.tree.command(name="setclass", description="Choose your Border combat class")
@app_commands.describe(class_name="Attacker / Sniper / Gunner / Shooter / All Rounder")
async def setclass(interaction: discord.Interaction, class_name: str):
    matched = next((c for c in CLASSES if c.lower() == class_name.lower()), None)
    if not matched:
        await interaction.response.send_message(
            embed=discord.Embed(title="❌ Invalid Class",
                                description=f"Choose from: {', '.join(CLASSES.keys())}",
                                color=0xe74c3c), ephemeral=True)
        return
    async with aiosqlite.connect(DB_NAME) as db:
        if not await agent_required(interaction, db):
            return
        await db.execute("UPDATE agents SET class=? WHERE user_id=?", (matched, interaction.user.id))
        await db.commit()

    cls = CLASSES[matched]
    embed = discord.Embed(title=f"{cls['emoji']} Class Set: {matched}",
                          description=cls["description"], color=COLOR)
    embed.add_field(name="⚡ Strong Against", value=cls["strong_against"])
    await interaction.response.send_message(embed=embed)

# ============================================================
# /faction
# ============================================================
@bot.tree.command(name="faction", description="Join a Border faction")
@app_commands.describe(faction_name="Kido / Shinoda / Tamakoma")
async def faction(interaction: discord.Interaction, faction_name: str):
    faction_name = faction_name.title()
    if faction_name not in FACTIONS:
        names = ", ".join(FACTIONS.keys())
        await interaction.response.send_message(
            embed=discord.Embed(title="❌ Invalid Faction",
                                description=f"Choose from: {names}",
                                color=0xe74c3c), ephemeral=True)
        return
    async with aiosqlite.connect(DB_NAME) as db:
        if not await agent_required(interaction, db):
            return
        await db.execute("UPDATE agents SET faction=? WHERE user_id=?", (faction_name, interaction.user.id))
        await db.commit()

    fac = FACTIONS[faction_name]
    embed = discord.Embed(title=f"{fac['emoji']} Faction Joined: {faction_name}",
                          description=fac["description"], color=COLOR)
    buffs = fac.get("buffs", {})
    if buffs:
        buff_text = ", ".join(f"{k}+{v}" for k, v in buffs.items())
        embed.add_field(name="📈 Faction Bonus", value=buff_text)
    await interaction.response.send_message(embed=embed)

# ============================================================
# /classes
# ============================================================
@bot.tree.command(name="classes", description="View all Border combat classes and matchups")
async def classes(interaction: discord.Interaction):
    embed = discord.Embed(title="⚔️ Border Combat Classes",
                          description=f"Each class deals **+{int((CLASS_ADVANTAGE_MULT-1)*100)}% damage** against its counter.\nUse `/setclass` to choose yours.",
                          color=COLOR)
    for name, data in CLASSES.items():
        embed.add_field(
            name=f"{data['emoji']} {name}",
            value=f"Strong vs **{data['strong_against']}**\n{data['description']}",
            inline=False)
    await interaction.response.send_message(embed=embed)

# ============================================================
# /profile (embed)
# ============================================================
@bot.tree.command(name="profile", description="View your agent profile")
async def profile(interaction: discord.Interaction):
    user_id = interaction.user.id
    # Check expedition
    credits_earned, spins_earned = await check_expedition(user_id)
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT trion, side_effect, spins, credits, elo, wins, losses, class, faction FROM agents WHERE user_id=?",
            (user_id,))
        agent = await cursor.fetchone()
        if not agent:
            await interaction.response.send_message("Use `/joinborder` first.", ephemeral=True)
            return
        trion, side, spins, credits, elo, wins, losses, agent_class, faction = agent

        cursor = await db.execute(
            "SELECT attack, defense, mobility, intelligence, trion_control, perception, stat_points FROM agent_stats WHERE user_id=?",
            (user_id,))
        s = await cursor.fetchone()
        stats = {"Attack": s[0], "Defense": s[1], "Mobility": s[2],
                 "Intelligence": s[3], "Trion Control": s[4], "Perception": s[5]}
        points = s[6]

        cursor = await db.execute("SELECT trigger FROM loadouts WHERE user_id=?", (user_id,))
        triggers = [row[0] for row in await cursor.fetchall()]

        cursor = await db.execute("SELECT arc, mission FROM story_progress WHERE user_id=?", (user_id,))
        story_row = await cursor.fetchone()
        story_arc, story_mission = story_row if story_row else ("Prologue", 1)

    rank = get_rank(elo)
    embed = discord.Embed(title=f"🛡️ Agent Profile: {interaction.user.display_name}", color=COLOR)
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.add_field(name="🔋 Trion", value=trion)
    embed.add_field(name="🧬 Side Effect", value=side if side else "None")
    if agent_class:
        embed.add_field(name="⚔️ Class", value=f"{CLASSES[agent_class]['emoji']} {agent_class}")
    if faction:
        embed.add_field(name="🏛️ Faction", value=f"{FACTIONS[faction]['emoji']} {faction}")
    embed.add_field(name="🏆 ELO", value=f"{elo} ({rank})")
    embed.add_field(name="W / L", value=f"{wins} / {losses}")
    embed.add_field(name="🎰 Spins", value=spins)
    embed.add_field(name="💳 Credits", value=credits)
    stat_text = "\n".join([f"**{k}**: {v}" for k, v in stats.items()])
    embed.add_field(name="📊 Stats", value=stat_text, inline=False)
    embed.add_field(name="⭐ Unspent Points", value=points)
    embed.add_field(name="⚡ Loadout", value=", ".join(triggers) if triggers else "Empty", inline=False)
    embed.add_field(name="📖 Story", value=f"{story_arc} — Mission {story_mission}")
    if credits_earned:
        embed.add_field(name="🌌 Expedition Returned!", value=f"Earned {credits_earned} credits and {spins_earned} spins.", inline=False)
    await interaction.response.send_message(embed=embed)

# ============================================================
# /shop, /sideeffects, /buytrigger, /loadout, /equip
# ============================================================
# (Paginated views omitted for brevity; they are identical to the original merged version.
# The full code for ShopView and SideEffectsView is exactly as in the file you provided.)
# I'm including them here in the final answer for completeness.

TRIGGERS_PER_PAGE = 5

class ShopView(discord.ui.View):
    def __init__(self, page=0):
        super().__init__(timeout=120)
        self.page = page
        self.trigger_list = list(TRIGGERS.items())
        self.total_pages = max(1, (len(self.trigger_list) + TRIGGERS_PER_PAGE - 1) // TRIGGERS_PER_PAGE)
        self._refresh_buttons()

    def _refresh_buttons(self):
        for item in self.children:
            if hasattr(item, "custom_id"):
                if item.custom_id == "shop_prev":
                    item.disabled = self.page == 0
                elif item.custom_id == "shop_next":
                    item.disabled = self.page >= self.total_pages - 1

    def get_embed(self):
        start = self.page * TRIGGERS_PER_PAGE
        page_entries = self.trigger_list[start : start + TRIGGERS_PER_PAGE]
        embed = discord.Embed(title="🛒 Border Trigger Shop",
                              description="Purchase triggers using Credits.",
                              color=COLOR)
        for name, data in page_entries:
            buff_text = ", ".join(f"{k}+{v}" for k, v in data["buffs"].items())
            embed.add_field(
                name=f"⚙️ {name}  ({data['type'].capitalize()})",
                value=f"💰 **{data['price']} Credits**  ⚡ Trion Cost: {data['trion_cost']}\n📊 {buff_text}",
                inline=False)
        embed.set_footer(text=f"Page {self.page+1}/{self.total_pages} · /buytrigger <name> to purchase")
        return embed

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary, custom_id="shop_prev")
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary, custom_id="shop_next")
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

EFFECTS_PER_PAGE = 5

class SideEffectsView(discord.ui.View):
    def __init__(self, page=0):
        super().__init__(timeout=120)
        self.page = page
        self.all_effects = (
            [("Common", e) for e in COMMON_EFFECTS] +
            [("Rare",   e) for e in RARE_EFFECTS]
        )
        self.total_pages = max(1, (len(self.all_effects) + EFFECTS_PER_PAGE - 1) // EFFECTS_PER_PAGE)
        self._refresh_buttons()

    def _refresh_buttons(self):
        for item in self.children:
            if hasattr(item, "custom_id"):
                if item.custom_id == "se_prev":
                    item.disabled = self.page == 0
                elif item.custom_id == "se_next":
                    item.disabled = self.page >= self.total_pages - 1

    def get_embed(self):
        start = self.page * EFFECTS_PER_PAGE
        page_entries = self.all_effects[start : start + EFFECTS_PER_PAGE]
        embed = discord.Embed(title="🧬 Side Effects Index",
                              description=f"**Common** — 85% chance when a side effect rolls\n"
                                           f"**Rare** — 15% chance when a side effect rolls\n"
                                           f"*(60% of agents receive a side effect at all)*",
                              color=COLOR)
        for rarity, effect in page_entries:
            colour = "🟡" if rarity == "Rare" else "🔵"
            buffs = ", ".join(f"{k}+{v}" for k, v in effect["buffs"].items())
            passive = f"\n✨ Passive: **{effect['passive']}**" if "passive" in effect else ""
            embed.add_field(
                name=f"{colour} {effect['name']}  [{rarity}]",
                value=f"📊 {buffs}{passive}",
                inline=False)
        embed.set_footer(text=f"Page {self.page+1}/{self.total_pages}")
        return embed

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary, custom_id="se_prev")
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary, custom_id="se_next")
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

@bot.tree.command(name="shop", description="Browse the Border Trigger Shop")
async def shop(interaction: discord.Interaction):
    view = ShopView(page=0)
    await interaction.response.send_message(embed=view.get_embed(), view=view)

@bot.tree.command(name="sideeffects", description="Browse all possible side effects")
async def sideeffects(interaction: discord.Interaction):
    view = SideEffectsView(page=0)
    await interaction.response.send_message(embed=view.get_embed(), view=view)

@bot.tree.command(name="buytrigger", description="Buy a trigger from the shop")
@app_commands.describe(trigger="Name of the trigger")
async def buytrigger(interaction: discord.Interaction, trigger: str):
    user_id = interaction.user.id
    trigger = trigger.title()
    if trigger not in TRIGGERS:
        await interaction.response.send_message(
            embed=discord.Embed(title="❌ Trigger Not Found",
                                description="Use `/shop` to browse.",
                                color=0xe74c3c), ephemeral=True)
        return
    price = TRIGGERS[trigger]["price"]
    async with aiosqlite.connect(DB_NAME) as db:
        if not await agent_required(interaction, db):
            return
        cursor = await db.execute("SELECT credits FROM agents WHERE user_id=?", (user_id,))
        agent = await cursor.fetchone()
        if agent[0] < price:
            await interaction.response.send_message(
                embed=discord.Embed(title="❌ Not Enough Credits",
                                    description=f"You need {price} Credits. You have {agent[0]}.",
                                    color=0xe74c3c), ephemeral=True)
            return
        cursor = await db.execute("SELECT 1 FROM triggers WHERE user_id=? AND trigger=?", (user_id, trigger))
        if await cursor.fetchone():
            await interaction.response.send_message(
                embed=discord.Embed(title="⚠️ Already Owned",
                                    description=f"You already own **{trigger}**.",
                                    color=0xf1c40f), ephemeral=True)
            return
        await db.execute("UPDATE agents SET credits = credits - ? WHERE user_id=?", (price, user_id))
        await db.execute("INSERT INTO triggers (user_id, trigger) VALUES (?,?)", (user_id, trigger))
        await db.commit()
    t = TRIGGERS[trigger]
    slot_hint = "Main or Sub" if t["type"] == "main" else "Optional"
    embed = discord.Embed(title="✅ Trigger Purchased",
                          description=f"You bought **{trigger}**!", color=0x2ecc71)
    embed.add_field(name="Slot", value=slot_hint)
    embed.add_field(name="Next Step", value=f"`/equip {trigger} {slot_hint.split()[0]}`")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="loadout", description="View your trigger loadout")
async def loadout(interaction: discord.Interaction):
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT trigger, slot FROM loadouts WHERE user_id=?", (user_id,))
        data = await cursor.fetchall()
    equipped = {slot: "None" for slot in LOADOUT_SLOTS}
    for trig, slot in data:
        equipped[slot] = trig
    embed = discord.Embed(title=f"⚡ {interaction.user.display_name}'s Loadout", color=COLOR)
    for slot in LOADOUT_SLOTS:
        embed.add_field(name=f"{slot} Trigger", value=equipped[slot], inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="equip", description="Equip a trigger into a loadout slot")
@app_commands.describe(trigger="Trigger name", slot="Main / Sub / Optional")
async def equip(interaction: discord.Interaction, trigger: str, slot: str):
    user_id = interaction.user.id
    trigger = trigger.title()
    slot = slot.title()
    if slot not in LOADOUT_SLOTS:
        await interaction.response.send_message("Slot must be: **Main**, **Sub**, **Optional**.", ephemeral=True)
        return
    if trigger not in TRIGGERS:
        await interaction.response.send_message("Trigger not found.", ephemeral=True)
        return
    t_type = TRIGGERS[trigger]["type"]
    if t_type == "main" and slot not in MAIN_COMPATIBLE_SLOTS:
        await interaction.response.send_message(f"**{trigger}** can only go in Main or Sub.", ephemeral=True)
        return
    if t_type == "optional" and slot not in OPT_COMPATIBLE_SLOTS:
        await interaction.response.send_message(f"**{trigger}** can only go in Optional slot.", ephemeral=True)
        return
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT 1 FROM triggers WHERE user_id=? AND trigger=?", (user_id, trigger))
        if not await cursor.fetchone():
            await interaction.response.send_message(f"You don't own **{trigger}**.", ephemeral=True)
            return
        await db.execute("INSERT OR REPLACE INTO loadouts (user_id, trigger, slot) VALUES (?,?,?)",
                         (user_id, trigger, slot))
        await db.commit()
    await interaction.response.send_message(
        embed=discord.Embed(title="✅ Equipped",
                            description=f"**{trigger}** equipped as **{slot} Trigger**.",
                            color=COLOR))

# ============================================================
# /spin
# ============================================================
@bot.tree.command(name="spin", description="Spend a spin to reroll Trion or Side Effect")
@app_commands.describe(spin_type="What to reroll: trion or side_effect")
@app_commands.choices(spin_type=[
    app_commands.Choice(name="Trion", value="trion"),
    app_commands.Choice(name="Side Effect", value="side_effect"),
])
async def spin(interaction: discord.Interaction, spin_type: str):
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT spins, trion, side_effect FROM agents WHERE user_id=?", (user_id,))
        data = await cursor.fetchone()
        if not data:
            await interaction.response.send_message("Use /joinborder first!", ephemeral=True)
            return
        spins, current_trion, current_side = data
        if spins <= 0:
            await interaction.response.send_message(
                embed=discord.Embed(title="❌ No Spins", description="You have no spins left!", color=0xe74c3c),
                ephemeral=True)
            return
        spins -= 1
        if spin_type == "trion":
            new_trion = roll_trion()
            await db.execute("UPDATE agents SET trion=?, spins=? WHERE user_id=?", (new_trion, spins, user_id))
            await db.commit()
            await interaction.response.send_message(
                embed=discord.Embed(title="🎲 Trion Rerolled",
                                    description=f"**{current_trion}** → **{new_trion}**\nSpins: {spins}",
                                    color=COLOR))
        else:
            new_side = roll_side_effect()
            new_side_json = json.dumps(new_side) if new_side else None
            old_name = json.loads(current_side)["name"] if current_side else "None"
            new_name = new_side["name"] if new_side else "None"
            await db.execute("UPDATE agents SET side_effect=?, spins=? WHERE user_id=?", (new_side_json, spins, user_id))
            await db.commit()
            await interaction.response.send_message(
                embed=discord.Embed(title="🎲 Side Effect Rerolled",
                                    description=f"**{old_name}** → **{new_name}**\nSpins: {spins}",
                                    color=COLOR))

# ============================================================
# /stats, /upgradestat
# ============================================================
@bot.tree.command(name="stats", description="View your agent stats")
async def stats(interaction: discord.Interaction):
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT attack, defense, mobility, intelligence, trion_control, perception, stat_points FROM agent_stats WHERE user_id=?",
            (user_id,))
        data = await cursor.fetchone()
        cursor2 = await db.execute("SELECT elo FROM agents WHERE user_id=?", (user_id,))
        elo_row = await cursor2.fetchone()
    if not data:
        await interaction.response.send_message("Use `/joinborder` first.", ephemeral=True)
        return
    attack, defense, mobility, intelligence, trion_control, perception, points = data
    elo = elo_row[0] if elo_row else 1000
    rank = get_rank(elo)
    cap = get_stat_cap(elo)
    used = (attack + defense + mobility + intelligence + trion_control + perception) - 6
    embed = discord.Embed(title="📊 Agent Stats", color=COLOR)
    embed.add_field(name="⚔️ Attack", value=attack)
    embed.add_field(name="🛡 Defense", value=defense)
    embed.add_field(name="🏃 Mobility", value=mobility)
    embed.add_field(name="🧠 Intelligence", value=intelligence)
    embed.add_field(name="🔋 Trion Control", value=trion_control)
    embed.add_field(name="👁 Perception", value=perception)
    embed.add_field(name="⭐ Unspent Points", value=points, inline=False)
    embed.add_field(name="📈 Stat Cap", value=f"{used}/{cap} used · {rank}")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="upgradestat", description="Spend a stat point to upgrade a stat")
@app_commands.describe(stat="attack / defense / mobility / intelligence / trion_control / perception")
async def upgradestat(interaction: discord.Interaction, stat: str):
    user_id = interaction.user.id
    stat = stat.lower()
    valid_stats = ["attack", "defense", "mobility", "intelligence", "trion_control", "perception"]
    if stat not in valid_stats:
        await interaction.response.send_message("Invalid stat.", ephemeral=True)
        return
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT attack, defense, mobility, intelligence, trion_control, perception, stat_points FROM agent_stats WHERE user_id=?",
            (user_id,))
        result = await cursor.fetchone()
        if not result:
            await interaction.response.send_message("Use `/joinborder` first.", ephemeral=True)
            return
        attack, defense, mobility, intelligence, trion_control, perception, points = result
        if points <= 0:
            await interaction.response.send_message("No stat points.", ephemeral=True)
            return
        cursor2 = await db.execute("SELECT elo FROM agents WHERE user_id=?", (user_id,))
        elo = (await cursor2.fetchone())[0] if cursor2 else 1000
        rank = get_rank(elo)
        cap = get_stat_cap(elo)
        used = (attack + defense + mobility + intelligence + trion_control + perception) - 6
        if used >= cap:
            await interaction.response.send_message(f"You've hit the **{rank}** cap ({cap} points).", ephemeral=True)
            return
        await db.execute(f"UPDATE agent_stats SET {stat} = {stat} + 1, stat_points = stat_points - 1 WHERE user_id=?",
                         (user_id,))
        await db.commit()
    await interaction.response.send_message(embed=discord.Embed(title="✅ Stat Upgraded",
                                                                 description=f"**{stat.replace('_',' ').title()}** +1",
                                                                 color=COLOR))

# ============================================================
# /leaderboard
# ============================================================
@bot.tree.command(name="leaderboard", description="View the top agents by ELO")
async def leaderboard(interaction: discord.Interaction):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT user_id, elo, class FROM agents ORDER BY elo DESC LIMIT 10")
        data = await cursor.fetchall()
    if not data:
        await interaction.response.send_message("No agents yet!", ephemeral=True)
        return
    embed = discord.Embed(title="🏆 Top Border Agents by ELO", color=0xf1c40f)
    for i, (uid, elo, agent_class) in enumerate(data, 1):
        try:
            user = await bot.fetch_user(uid)
            name = user.display_name
        except Exception:
            name = f"Unknown ({uid})"
        cls_emoji = CLASSES[agent_class]["emoji"] if agent_class and agent_class in CLASSES else "❓"
        embed.add_field(name=f"{i}. {name}", value=f"{cls_emoji} {get_rank(elo)} · ELO: {elo}", inline=False)
    await interaction.response.send_message(embed=embed)

# ============================================================
# TURN‑BASED ARENA
# ============================================================
@bot.tree.command(name="arena", description="Enter turn‑based Solo Arena")
async def arena(interaction: discord.Interaction):
    user_id = interaction.user.id
    now = time.time()
    last = _arena_cooldowns.get(user_id, 0)
    if now - last < ARENA_COOLDOWN:
        await interaction.response.send_message(
            embed=discord.Embed(title="⏳ Arena Cooldown",
                                description=f"Wait {int(ARENA_COOLDOWN - (now - last))}s.",
                                color=0xe67e22), ephemeral=True)
        return
    _arena_cooldowns[user_id] = now

    async with aiosqlite.connect(DB_NAME) as db:
        if not await agent_required(interaction, db):
            return
        cursor = await db.execute(
            "SELECT trion, side_effect, elo, wins, losses, class, faction FROM agents WHERE user_id=?", (user_id,))
        player_data = await cursor.fetchone()
        if not player_data:
            return
        trion, side, elo, wins, losses, agent_class, faction = player_data
        side = json.loads(side) if side else None

        cursor = await db.execute("SELECT trigger FROM loadouts WHERE user_id=?", (user_id,))
        triggers = [row[0] for row in await cursor.fetchall()]

        cursor = await db.execute(
            "SELECT attack, defense, mobility, intelligence, trion_control, perception FROM agent_stats WHERE user_id=?",
            (user_id,))
        s = await cursor.fetchone()
        stats_dict = {"attack": s[0], "defense": s[1], "mobility": s[2],
                      "intelligence": s[3], "trion_control": s[4], "perception": s[5]}

        cursor = await db.execute("SELECT trigger, level FROM trigger_mastery WHERE user_id=?", (user_id,))
        mastery = {row[0]: row[1] for row in await cursor.fetchall()}

    # Enemy stats
    wave_count = random.randint(2, 3)
    enemy_names = []
    total_dmg = 0
    for _ in range(wave_count):
        name, hp, dmg = random_neighbor()
        enemy_names.append(name)
        total_dmg += dmg
    ai_name = f"Neighbor Wave: {', '.join(enemy_names)}"
    ai_trion = total_dmg * 10  # simplified HP

    player = {
        "user": interaction.user,
        "name": interaction.user.display_name,
        "trion": trion,
        "base_trion": trion,
        "stats": stats_dict,
        "triggers": triggers,
        "class": agent_class,
        "faction": faction,
        "side_effect": side,
        "mastery": mastery
    }
    ai = {"name": ai_name, "trion": ai_trion, "damage": total_dmg}

    async def arena_callback(won, bailout, final_trion):
        async with aiosqlite.connect(DB_NAME) as db:
            if won:
                new_elo = win_elo(elo)
                wins_final = wins + 1
                losses_final = losses
                await db.execute("UPDATE agent_stats SET stat_points = stat_points + 1 WHERE user_id=?", (user_id,))
                for trig in triggers:
                    await gain_trigger_xp(db, user_id, trig, random.randint(8, 15))
            else:
                new_elo = lose_elo(elo)
                wins_final = wins
                losses_final = losses + 1
            await db.execute("UPDATE agents SET trion=?, elo=?, wins=?, losses=? WHERE user_id=?",
                             (max(1, final_trion), new_elo, wins_final, losses_final, user_id))
            await db.commit()

    view = TurnBattleView(interaction.channel, player, ai, callback=arena_callback)
    await interaction.response.send_message(
        f"⚔️ **{interaction.user.display_name}** enters the arena!\nTurn 1 begin!",
        view=view
    )

# ============================================================
# TURN‑BASED DUEL
# ============================================================
class DuelAcceptView(discord.ui.View):
    def __init__(self, challenger, opponent):
        super().__init__(timeout=60)
        self.challenger = challenger
        self.opponent = opponent

    @discord.ui.button(label="✅ Accept", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message("Only the challenged can accept.", ephemeral=True)
            return
        self.stop()
        await interaction.response.edit_message(content="Duel accepted! Preparing...", view=None)
        await self.start_duel(interaction)

    @discord.ui.button(label="❌ Decline", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message("Only the challenged can decline.", ephemeral=True)
            return
        self.stop()
        await interaction.response.edit_message(content="Duel declined.", view=None)

    async def start_duel(self, interaction):
        # Fetch both players' data
        async with aiosqlite.connect(DB_NAME) as db:
            p1_data = await db.execute(
                "SELECT trion, side_effect, elo, wins, losses, class, faction FROM agents WHERE user_id=?",
                (self.challenger.id,)).fetchone()
            p2_data = await db.execute(
                "SELECT trion, side_effect, elo, wins, losses, class, faction FROM agents WHERE user_id=?",
                (self.opponent.id,)).fetchone()
            if not p1_data or not p2_data:
                await interaction.followup.send("One player not registered.", ephemeral=True)
                return

            trion1, side1, elo1, wins1, losses1, class1, faction1 = p1_data
            trion2, side2, elo2, wins2, losses2, class2, faction2 = p2_data
            side1 = json.loads(side1) if side1 else None
            side2 = json.loads(side2) if side2 else None

            # Loadouts and stats
            cursor = await db.execute("SELECT trigger FROM loadouts WHERE user_id=?", (self.challenger.id,))
            triggers1 = [row[0] for row in await cursor.fetchall()]
            cursor = await db.execute("SELECT trigger FROM loadouts WHERE user_id=?", (self.opponent.id,))
            triggers2 = [row[0] for row in await cursor.fetchall()]

            cursor = await db.execute(
                "SELECT attack, defense, mobility, intelligence, trion_control, perception FROM agent_stats WHERE user_id=?",
                (self.challenger.id,))
            s1 = await cursor.fetchone()
            stats1 = {"attack": s1[0], "defense": s1[1], "mobility": s1[2],
                      "intelligence": s1[3], "trion_control": s1[4], "perception": s1[5]}

            cursor = await db.execute(
                "SELECT attack, defense, mobility, intelligence, trion_control, perception FROM agent_stats WHERE user_id=?",
                (self.opponent.id,))
            s2 = await cursor.fetchone()
            stats2 = {"attack": s2[0], "defense": s2[1], "mobility": s2[2],
                      "intelligence": s2[3], "trion_control": s2[4], "perception": s2[5]}

            cursor = await db.execute("SELECT trigger, level FROM trigger_mastery WHERE user_id=?", (self.challenger.id,))
            mastery1 = {row[0]: row[1] for row in await cursor.fetchall()}
            cursor = await db.execute("SELECT trigger, level FROM trigger_mastery WHERE user_id=?", (self.opponent.id,))
            mastery2 = {row[0]: row[1] for row in await cursor.fetchall()}

        player1 = {
            "user": self.challenger,
            "name": self.challenger.display_name,
            "trion": trion1,
            "base_trion": trion1,
            "stats": stats1,
            "triggers": triggers1,
            "class": class1,
            "faction": faction1,
            "side_effect": side1,
            "mastery": mastery1
        }
        player2 = {
            "user": self.opponent,
            "name": self.opponent.display_name,
            "trion": trion2,
            "base_trion": trion2,
            "stats": stats2,
            "triggers": triggers2,
            "class": class2,
            "faction": faction2,
            "side_effect": side2,
            "mastery": mastery2
        }

        async def duel_callback(winner=None, loser=None, final_trion1=0, final_trion2=0):
            async with aiosqlite.connect(DB_NAME) as db:
                if winner:
                    w_id = winner["user"].id
                    l_id = loser["user"].id
                    await db.execute(
                        "UPDATE agents SET elo=?, wins=wins+1, losses=losses WHERE user_id=?",
                        (win_elo(w_id == self.challenger.id and elo1 or elo2), w_id))
                    await db.execute(
                        "UPDATE agents SET elo=?, losses=losses+1 WHERE user_id=?",
                        (lose_elo(l_id == self.challenger.id and elo1 or elo2), l_id))
                    # Stat point to winner
                    await db.execute("UPDATE agent_stats SET stat_points = stat_points + 1 WHERE user_id=?", (w_id,))
                    # XP for winner's triggers
                    for trig in winner["triggers"]:
                        await gain_trigger_xp(db, w_id, trig, random.randint(8, 15))
                # Update trion
                await db.execute("UPDATE agents SET trion=? WHERE user_id=?", (max(1, final_trion1), self.challenger.id))
                await db.execute("UPDATE agents SET trion=? WHERE user_id=?", (max(1, final_trion2), self.opponent.id))
                await db.commit()

        view = DuelTurnView(player1, player2, callback=duel_callback)
        await interaction.followup.send(
            f"⚔️ **{player1['name']}** vs **{player2['name']}** — Turn 1 begin!\n{player1['name']}'s turn.",
            view=view)

@bot.tree.command(name="duel", description="Challenge another player to a turn‑based duel")
@app_commands.describe(opponent="The player to challenge")
async def duel(interaction: discord.Interaction, opponent: discord.Member):
    if opponent.id == interaction.user.id:
        await interaction.response.send_message("You can't duel yourself!", ephemeral=True)
        return
    if opponent.bot:
        await interaction.response.send_message("You can't duel a bot!", ephemeral=True)
        return
    async with aiosqlite.connect(DB_NAME) as db:
        if not await db.execute("SELECT 1 FROM agents WHERE user_id=?", (opponent.id,)).fetchone():
            await interaction.response.send_message(f"{opponent.mention} is not an agent.", ephemeral=True)
            return
    view = DuelAcceptView(interaction.user, opponent)
    embed = discord.Embed(title="⚔️ Duel Challenge",
                          description=f"{interaction.user.mention} challenges {opponent.mention}!",
                          color=0xe74c3c)
    await interaction.response.send_message(embed=embed, view=view)

# ============================================================
# /mission — random defense missions
# ============================================================
@bot.tree.command(name="mission", description="Accept a random defense mission")
async def mission(interaction: discord.Interaction):
    user_id = interaction.user.id
    now = time.time()
    last = _arena_cooldowns.get(user_id, 0)
    if now - last < ARENA_COOLDOWN:
        await interaction.response.send_message(
            embed=discord.Embed(title="⏳ Cooldown", description=f"Wait {int(ARENA_COOLDOWN - (now - last))}s.", color=0xe67e22),
            ephemeral=True)
        return
    _arena_cooldowns[user_id] = now

    async with aiosqlite.connect(DB_NAME) as db:
        if not await agent_required(interaction, db):
            return
        cursor = await db.execute(
            "SELECT trion, side_effect, elo, wins, losses, class, faction FROM agents WHERE user_id=?", (user_id,))
        player_data = await cursor.fetchone()
        if not player_data: return
        trion, side, elo, wins, losses, agent_class, faction = player_data
        side = json.loads(side) if side else None

        cursor = await db.execute("SELECT trigger FROM loadouts WHERE user_id=?", (user_id,))
        triggers = [row[0] for row in await cursor.fetchall()]

        cursor = await db.execute(
            "SELECT attack, defense, mobility, intelligence, trion_control, perception FROM agent_stats WHERE user_id=?",
            (user_id,))
        s = await cursor.fetchone()
        stats_dict = {"attack": s[0], "defense": s[1], "mobility": s[2],
                      "intelligence": s[3], "trion_control": s[4], "perception": s[5]}

        cursor = await db.execute("SELECT trigger, level FROM trigger_mastery WHERE user_id=?", (user_id,))
        mastery = {row[0]: row[1] for row in await cursor.fetchall()}

    # Random mission parameters
    mission_types = ["Civilian Rescue", "Neighbor Ambush", "Supply Defense"]
    mission_desc = random.choice(mission_types)
    wave_count = random.randint(2, 4)
    enemy_names = []
    total_dmg = 0
    for _ in range(wave_count):
        name, hp, dmg = random_neighbor()
        enemy_names.append(name)
        total_dmg += dmg
    ai_name = f"Mission: {mission_desc} ({', '.join(enemy_names)})"
    ai_trion = total_dmg * 8  # slightly weaker than arena

    player = {
        "user": interaction.user,
        "name": interaction.user.display_name,
        "trion": trion,
        "base_trion": trion,
        "stats": stats_dict,
        "triggers": triggers,
        "class": agent_class,
        "faction": faction,
        "side_effect": side,
        "mastery": mastery
    }
    ai = {"name": ai_name, "trion": ai_trion, "damage": total_dmg}

    async def mission_callback(won, bailout, final_trion):
        async with aiosqlite.connect(DB_NAME) as db:
            if won:
                # Bonus rewards for mission
                credits_bonus = random.randint(50, 200)
                spins_bonus = 1
                await db.execute("UPDATE agents SET credits = credits + ?, spins = spins + ? WHERE user_id=?",
                                 (credits_bonus, spins_bonus, user_id))
                await db.execute("UPDATE agent_stats SET stat_points = stat_points + 1 WHERE user_id=?", (user_id,))
                for trig in triggers:
                    await gain_trigger_xp(db, user_id, trig, random.randint(10, 20))
            # Update trion and cooldown already set
            await db.execute("UPDATE agents SET trion=? WHERE user_id=?", (max(1, final_trion), user_id))
            await db.commit()

    view = TurnBattleView(interaction.channel, player, ai, callback=mission_callback)
    await interaction.response.send_message(
        f"🆘 **{mission_desc}** — defend against the Neighbors!\nTurn 1 begin!",
        view=view)

# ============================================================
# STORY SYSTEM (fixed progression)
# ============================================================
@bot.tree.command(name="story", description="View your current story mission")
async def story(interaction: discord.Interaction):
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT arc, chapter, mission FROM story_progress WHERE user_id=?", (user_id,))
        progress = await cursor.fetchone()
        if not progress:
            await db.execute("INSERT OR IGNORE INTO story_progress (user_id) VALUES (?)", (user_id,))
            await db.commit()
            arc, chapter, mission = "Prologue", 1, 1
        else:
            arc, chapter, mission = progress
        cursor = await db.execute(
            "SELECT type, description, choices, reward_type, reward_amount, reward_trigger, replayable "
            "FROM story_missions WHERE arc=? AND chapter=? AND mission=?",
            (arc, chapter, mission))
        mission_data = await cursor.fetchone()
    if not mission_data:
        await interaction.response.send_message(
            embed=discord.Embed(title="📖 Story Mode",
                                description="You've completed all current missions. More coming soon!",
                                color=COLOR))
        return
    m_type, desc, choices_json, r_type, r_amount, r_trigger, replayable = mission_data
    embed = discord.Embed(title=f"📖 {arc} — Chapter {chapter}, Mission {mission}",
                          description=desc, color=COLOR)
    if m_type == "choice":
        embed.add_field(name="Choices", value="Use `/storymission` to make your choice.", inline=False)
    embed.add_field(name="🎁 Reward",
                    value=f"{r_amount} {r_type}" + (f" · Trigger: {r_trigger}" if r_trigger else ""), inline=True)
    embed.add_field(name="🔁 Type", value="Replayable" if replayable else "One-time", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="storymission", description="Continue your story")
async def storymission(interaction: discord.Interaction):
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT arc, chapter, mission FROM story_progress WHERE user_id=?", (user_id,))
        progress = await cursor.fetchone()
        if not progress:
            await db.execute("INSERT OR IGNORE INTO story_progress (user_id) VALUES (?)", (user_id,))
            await db.commit()
            arc, chapter, mission_num = "Prologue", 1, 1
        else:
            arc, chapter, mission_num = progress
        cursor = await db.execute(
            "SELECT type, description, choices, reward_type, reward_amount, reward_trigger, replayable "
            "FROM story_missions WHERE arc=? AND chapter=? AND mission=?",
            (arc, chapter, mission_num))
        mission_data = await cursor.fetchone()
    if not mission_data:
        await interaction.response.send_message("No mission found. You may have completed everything.")
        return

    m_type, desc, choices_json, r_type, r_amount, r_trigger, replayable = mission_data

    if m_type in ("arena", "boss"):
        await _handle_story_arena(interaction, arc, chapter, mission_num,
                                  m_type, r_type, r_amount, r_trigger)
    elif m_type == "choice":
        await _handle_story_choice(interaction, arc, chapter, mission_num,
                                   choices_json, r_type, r_amount, r_trigger)
    elif m_type == "exploration":
        await _handle_story_exploration(interaction, arc, chapter, mission_num,
                                        desc, r_type, r_amount, r_trigger)

async def _advance_story(db, user_id, arc, chapter, mission_num):
    next_mission = mission_num + 1
    cursor = await db.execute("SELECT 1 FROM story_missions WHERE arc=? AND chapter=? AND mission=?",
                              (arc, chapter, next_mission))
    if await cursor.fetchone():
        await db.execute("UPDATE story_progress SET mission=? WHERE user_id=?", (next_mission, user_id))
    else:
        next_chapter = chapter + 1
        cursor = await db.execute("SELECT 1 FROM story_missions WHERE arc=? AND chapter=?",
                                  (arc, next_chapter))
        if await cursor.fetchone():
            await db.execute("UPDATE story_progress SET chapter=?, mission=1 WHERE user_id=?",
                             (next_chapter, user_id))

async def _give_rewards(db, user_id, r_type, r_amount, r_trigger, won=True):
    if not won:
        return
    if r_type == "credits":
        await db.execute("UPDATE agents SET credits = credits + ? WHERE user_id=?", (r_amount, user_id))
    elif r_type == "spins":
        await db.execute("UPDATE agents SET spins = spins + ? WHERE user_id=?", (r_amount, user_id))
    elif r_type == "trigger" and r_trigger:
        await db.execute("INSERT OR IGNORE INTO triggers (user_id, trigger) VALUES (?,?)", (user_id, r_trigger))
    await db.execute("UPDATE agent_stats SET stat_points = stat_points + 1 WHERE user_id=?", (user_id,))
    cursor = await db.execute("SELECT trigger FROM loadouts WHERE user_id=?", (user_id,))
    for trig in [row[0] for row in await cursor.fetchall()]:
        await gain_trigger_xp(db, user_id, trig, random.randint(8, 15))

async def _handle_story_arena(interaction, arc, chapter, mission_num, m_type, r_type, r_amount, r_trigger):
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT trion, side_effect, faction FROM agents WHERE user_id=?", (user_id,))
        agent = await cursor.fetchone()
        if not agent:
            await interaction.response.send_message("Use `/joinborder` first.", ephemeral=True)
            return
        trion, side, faction = agent
        side = json.loads(side) if side else None
        cursor = await db.execute("SELECT trigger FROM loadouts WHERE user_id=?", (user_id,))
        triggers = [row[0] for row in await cursor.fetchall()]
        cursor = await db.execute(
            "SELECT attack, defense, mobility, intelligence, trion_control, perception FROM agent_stats WHERE user_id=?",
            (user_id,))
        s = await cursor.fetchone()
    stats_dict = {"attack": s[0], "defense": s[1], "mobility": s[2],
                  "intelligence": s[3], "trion_control": s[4], "perception": s[5]}
    dmg1 = await calculate_damage(user_id, trion, side, triggers, stats_dict, faction=faction)
    wave_count = random.randint(2, 3) if m_type != "boss" else 1
    enemy_names = []
    total_enemy_dmg = 0
    for _ in range(wave_count):
        name, hp, dmg = random_neighbor()
        if m_type == "boss":
            dmg = int(dmg * 1.5)
        enemy_names.append(name)
        total_enemy_dmg += dmg
    dmg2 = int(total_enemy_dmg * 1.5)
    log = (f"**Battle Start!**\n{interaction.user.display_name} deals **{int(dmg1)}** damage.\n"
           f"Neighbors ({', '.join(enemy_names)}) deal **{dmg2}** damage.\n")
    won = dmg1 >= dmg2
    log += "🏆 You won!" if won else "⚔️ You lost!"
    async with aiosqlite.connect(DB_NAME) as db:
        await _give_rewards(db, user_id, r_type, r_amount, r_trigger, won)
        await _advance_story(db, user_id, arc, chapter, mission_num)
        await db.commit()
    embed = discord.Embed(title="🛡️ Boss Fight" if m_type == "boss" else "⚔️ Story Battle",
                          description=log, color=COLOR)
    await interaction.response.send_message(embed=embed)

async def _handle_story_choice(interaction, arc, chapter, mission_num, choices_json, r_type, r_amount, r_trigger):
    choices = json.loads(choices_json)
    view = discord.ui.View(timeout=60)

    async def choice_callback(interaction: discord.Interaction, choice_id: str):
        user_id = interaction.user.id
        async with aiosqlite.connect(DB_NAME) as db:
            await _give_rewards(db, user_id, r_type, r_amount, r_trigger, True)
            await _advance_story(db, user_id, arc, chapter, mission_num)
            await db.commit()
        await interaction.response.edit_message(
            content=f"You chose **{choice_id}**. The story continues...", view=None, embed=None)

    for c in choices:
        button = discord.ui.Button(label=c["label"], style=discord.ButtonStyle.primary)
        button.callback = lambda i, cid=c["id"]: choice_callback(i, cid)
        view.add_item(button)

    embed = discord.Embed(title="📜 Choice Mission",
                          description="Make your choice wisely! ⚔️", color=COLOR)
    await interaction.response.send_message(embed=embed, view=view)

async def _handle_story_exploration(interaction, arc, chapter, mission_num, desc, r_type, r_amount, r_trigger):
    user_id = interaction.user.id
    embed = discord.Embed(title="🔍 Exploration Mission", description=desc, color=COLOR)
    await interaction.response.send_message(embed=embed)
    async with aiosqlite.connect(DB_NAME) as db:
        await _give_rewards(db, user_id, r_type, r_amount, r_trigger, True)
        await _advance_story(db, user_id, arc, chapter, mission_num)
        await db.commit()

# ============================================================
# SQUAD COMMANDS
# ============================================================
@bot.tree.command(name="squadcreate", description="Create a squad")
@app_commands.describe(name="Squad name")
async def squadcreate(interaction: discord.Interaction, name: str):
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        if await db.execute("SELECT 1 FROM squad_members WHERE user_id=?", (user_id,)).fetchone():
            await interaction.response.send_message("You are already in a squad.", ephemeral=True)
            return
        await db.execute("INSERT INTO squads (name, leader_id) VALUES (?,?)", (name, user_id))
        cursor = await db.execute("SELECT squad_id FROM squads WHERE leader_id=?", (user_id,))
        squad_id = (await cursor.fetchone())[0]
        await db.execute("INSERT INTO squad_members (squad_id, user_id, role) VALUES (?,?,?)",
                         (squad_id, user_id, "Leader"))
        await db.commit()
    await interaction.response.send_message(
        embed=discord.Embed(title="🛡 Squad Created", description=f"Squad **{name}** created.", color=COLOR))

@bot.tree.command(name="squadinvite", description="Invite a player to your squad")
@app_commands.describe(member="The player to invite")
async def squadinvite(interaction: discord.Interaction, member: discord.Member):
    inviter = interaction.user.id
    target = member.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT squad_id, role FROM squad_members WHERE user_id=?", (inviter,))
        data = await cursor.fetchone()
        if not data or data[1] != "Leader":
            await interaction.response.send_message("Only squad leaders can invite.", ephemeral=True)
            return
        squad_id = data[0]
        if await db.execute("SELECT 1 FROM squad_members WHERE user_id=?", (target,)).fetchone():
            await interaction.response.send_message("That player is already in a squad.", ephemeral=True)
            return
        if (await db.execute("SELECT COUNT(*) FROM squad_members WHERE squad_id=?", (squad_id,)))[0] >= 5:
            await interaction.response.send_message("Squad is full (max 5).", ephemeral=True)
            return
        await db.execute("INSERT INTO squad_members (squad_id, user_id, role) VALUES (?,?,?)",
                         (squad_id, target, "Member"))
        await db.commit()
    await interaction.response.send_message(f"{member.mention} joined your squad.")

@bot.tree.command(name="squadinfo", description="View your squad info")
async def squadinfo(interaction: discord.Interaction):
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT squad_id FROM squad_members WHERE user_id=?", (user_id,))
        row = await cursor.fetchone()
        if not row:
            await interaction.response.send_message("Not in a squad.", ephemeral=True)
            return
        squad_id = row[0]
        cursor = await db.execute("SELECT name, division, elo, operator FROM squads WHERE squad_id=?", (squad_id,))
        name, division, elo, operator = await cursor.fetchone()
        cursor = await db.execute("SELECT user_id, role FROM squad_members WHERE squad_id=?", (squad_id,))
        members = await cursor.fetchall()
    lines = ""
    for uid, role in members:
        try:
            user = await bot.fetch_user(uid)
            lines += f"{user.name} — {role}\n"
        except Exception:
            lines += f"Unknown ({uid}) — {role}\n"
    embed = discord.Embed(title=f"🛡 Squad: {name}", color=COLOR)
    embed.add_field(name="Division", value=division)
    embed.add_field(name="ELO", value=elo)
    embed.add_field(name="Operator", value=operator or "None")
    embed.add_field(name="Members", value=lines, inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="squadleave", description="Leave your squad")
async def squadleave(interaction: discord.Interaction):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM squad_members WHERE user_id=?", (interaction.user.id,))
        await db.commit()
    await interaction.response.send_message("Left squad.")

# ============================================================
# /expedition
# ============================================================
@bot.tree.command(name="expedition", description="Go on an expedition (B‑Rank+)")
async def expedition(interaction: discord.Interaction):
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        if not await agent_required(interaction, db): return
        cursor = await db.execute("SELECT elo, trion, expedition_end FROM agents WHERE user_id=?", (user_id,))
        elo, trion, end_time = await cursor.fetchone()
        rank = get_rank(elo)
        if rank not in ("B-Rank", "A-Rank"):
            await interaction.response.send_message("You must be B‑Rank or higher to go on an expedition.", ephemeral=True)
            return
        now = time.time()
        if end_time > now:
            remaining = int(end_time - now)
            await interaction.response.send_message(f"You are already on an expedition. Return in {remaining//3600}h {(remaining%3600)//60}m.", ephemeral=True)
            return
        await db.execute("UPDATE agents SET expedition_end = ? WHERE user_id=?", (now + EXPEDITION_COOLDOWN, user_id))
        await db.commit()
    await interaction.response.send_message(
        embed=discord.Embed(title="🌌 Expedition Started",
                            description="You have embarked on a 4‑hour expedition. You'll return with rewards!",
                            color=COLOR))

# ============================================================
# /operator
# ============================================================
OPERATORS = {
    "Shiori": {"buff": "cooldown_reduction", "value": 0.2},
    "Asami":  {"buff": "intelligence_bonus", "value": 2},
    "Hana":   {"buff": "credit_bonus", "value": 0.1},
}

@bot.tree.command(name="operator", description="Assign an operator to your squad")
@app_commands.describe(operator_name="Shiori / Asami / Hana")
async def operator(interaction: discord.Interaction, operator_name: str):
    user_id = interaction.user.id
    operator_name = operator_name.title()
    if operator_name not in OPERATORS:
        await interaction.response.send_message("Invalid operator.", ephemeral=True)
        return
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT squad_id FROM squad_members WHERE user_id=? AND role='Leader'", (user_id,))
        row = await cursor.fetchone()
        if not row:
            await interaction.response.send_message("You must be a squad leader to assign an operator.", ephemeral=True)
            return
        await db.execute("UPDATE squads SET operator=? WHERE squad_id=?", (operator_name, row[0]))
        await db.commit()
    await interaction.response.send_message(f"Operator **{operator_name}** assigned to your squad!")

# ============================================================
# REMAINING COMMANDS (bailout, trionrank, simulation, combostats, triggers_mastered, neighborhood, baseinfo, trainers, train, redeem)
# ============================================================
@bot.tree.command(name="bailout", description="Escape to safety with Bail Out — costs Trion")
async def bailout(interaction: discord.Interaction):
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT trion FROM agents WHERE user_id=?", (user_id,))
        agent = await cursor.fetchone()
        if not agent:
            await interaction.response.send_message("Use `/joinborder` first.", ephemeral=True)
            return
        trion = agent[0]
        cost = max(1, trion // 3)
        if trion <= 1:
            await interaction.response.send_message(
                embed=discord.Embed(title="❌ Not Enough Trion", description="Need at least 2 Trion.", color=0xe74c3c),
                ephemeral=True)
            return
        await db.execute("UPDATE agents SET trion = trion - ? WHERE user_id=?", (cost, user_id))
        await db.commit()
    await interaction.response.send_message(
        embed=discord.Embed(title="🚀 Bail Out!", description=f"Escaped! Lost **{cost}** Trion.", color=0x3498db))

@bot.tree.command(name="trionrank", description="Check your Border Division rank")
async def trionrank(interaction: discord.Interaction):
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT elo, class FROM agents WHERE user_id=?", (user_id,))
        data = await cursor.fetchone()
        if not data:
            await interaction.response.send_message("Use `/joinborder` first.", ephemeral=True)
            return
        elo, agent_class = data
    rank = get_rank(elo)
    details = {
        "C-Rank": {"color": 0x95a5a6, "desc": "New trainees."},
        "B-Rank": {"color": 0x3498db, "desc": "Experienced agents."},
        "A-Rank": {"color": 0xf39c12, "desc": "Elite operators."},
    }
    d = details[rank]
    embed = discord.Embed(title=f"🏅 Border Rank: {rank}", description=d["desc"], color=d["color"])
    embed.add_field(name="ELO", value=elo)
    embed.add_field(name="Class", value=agent_class or "None")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="simulation", description="Practice a trigger combo in simulation mode")
async def simulation(interaction: discord.Interaction):
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT trigger FROM loadouts WHERE user_id=?", (user_id,))
        triggers = [row[0] for row in await cursor.fetchall()]
    if not triggers:
        await interaction.response.send_message("Equip triggers first.", ephemeral=True)
        return
    info = "\n".join([f"⚙️ **{t}** — {TRIGGERS[t]['type'].capitalize()}" for t in triggers if t in TRIGGERS])
    embed = discord.Embed(title="🎮 Trigger Simulation", description="Risk-free practice.", color=COLOR)
    embed.add_field(name="Loadout", value=info or "None", inline=False)
    embed.add_field(name="Result", value="✅ Successful! No Trion consumed.", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="combostats", description="Preview your damage output with current gear")
async def combostats(interaction: discord.Interaction):
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT trion, side_effect, class, faction FROM agents WHERE user_id=?", (user_id,))
        agent = await cursor.fetchone()
        if not agent:
            await interaction.response.send_message("Use `/joinborder` first.", ephemeral=True)
            return
        trion, side, agent_class, faction = agent
        side = json.loads(side) if side else None
        cursor = await db.execute("SELECT trigger FROM loadouts WHERE user_id=?", (user_id,))
        triggers = [row[0] for row in await cursor.fetchall()]
        cursor = await db.execute(
            "SELECT attack, defense, mobility, intelligence, trion_control, perception FROM agent_stats WHERE user_id=?",
            (user_id,))
        s = await cursor.fetchone()
    stats_dict = {"attack": s[0], "defense": s[1], "mobility": s[2],
                  "intelligence": s[3], "trion_control": s[4], "perception": s[5]}
    dmg = await calculate_damage(user_id, trion, side, triggers, stats_dict, attacker_class=agent_class, faction=faction)
    embed = discord.Embed(title="💥 Combo Analysis", color=COLOR)
    embed.add_field(name="Trion", value=trion)
    embed.add_field(name="Class", value=agent_class or "None")
    embed.add_field(name="Faction", value=faction or "None")
    embed.add_field(name="Loadout", value=" | ".join(triggers) if triggers else "None")
    embed.add_field(name="Estimated Damage", value=f"**{int(dmg)}**", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="triggers_mastered", description="View your trigger mastery levels")
async def triggers_mastered(interaction: discord.Interaction):
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT trigger, xp, level FROM trigger_mastery WHERE user_id=? ORDER BY level DESC", (user_id,))
        mastery = await cursor.fetchall()
    if not mastery:
        await interaction.response.send_message("Use triggers in battle to gain mastery XP!", ephemeral=True)
        return
    embed = discord.Embed(title="🎖️ Trigger Mastery", color=COLOR)
    for trig, xp, level in mastery[:10]:
        embed.add_field(name=f"**{trig}**", value=f"Level **{level}** · {xp} XP", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="neighborhood", description="Scout the area for Neighbor activity")
async def neighborhood(interaction: discord.Interaction):
    name, hp, dmg = random_neighbor()
    threat = "🟢 Low" if dmg < 5 else "🟡 Medium" if dmg < 8 else "🔴 High"
    embed = discord.Embed(title="👁️ Neighborhood Report", description=f"Detected: **{name}**", color=0xe67e22)
    embed.add_field(name="Threat", value=threat)
    embed.add_field(name="HP", value=hp)
    embed.add_field(name="Damage", value=dmg)
    embed.add_field(name="Action", value="Use `/arena` or `/bailout`", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="baseinfo", description="Check Border HQ information")
async def baseinfo(interaction: discord.Interaction):
    async with aiosqlite.connect(DB_NAME) as db:
        total_agents = (await db.execute("SELECT COUNT(*) FROM agents")).fetchone()[0]
        total_squads = (await db.execute("SELECT COUNT(*) FROM squads")).fetchone()[0]
        total_credits = (await db.execute("SELECT SUM(credits) FROM agents")).fetchone()[0] or 0
    embed = discord.Embed(title="🏢 Border HQ Status", color=0x1abc9c)
    embed.add_field(name="Agents", value=total_agents)
    embed.add_field(name="Squads", value=total_squads)
    embed.add_field(name="Credits in Circulation", value=total_credits)
    await interaction.response.send_message(embed=embed)

TRAINERS = {
    "Shinoda":   {"specialty": "Intelligence",   "stat": "intelligence",   "boost": 2, "cost": 150},
    "Kido":      {"specialty": "Trion Control",  "stat": "trion_control",  "boost": 2, "cost": 150},
    "Karasuma":  {"specialty": "Combat",         "stat": None, "boost": (1,1), "stats": ("attack","defense"), "cost":200},
    "Yūma":      {"specialty": "Mobility",       "stat": "mobility",       "boost": 2, "cost": 120},
}

@bot.tree.command(name="trainers", description="View available trainers for stat boosts")
async def trainers(interaction: discord.Interaction):
    embed = discord.Embed(title="👨‍🏫 Available Trainers", color=COLOR)
    for t, d in TRAINERS.items():
        desc = f"+{d['boost']} {d['specialty']}" if isinstance(d['boost'], int) else f"+1 Attack, +1 Defense"
        embed.add_field(name=f"🧑 {t}", value=f"{desc} | Cost: {d['cost']} Credits", inline=False)
    embed.set_footer(text="Use /train <trainer_name>")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="train", description="Train with a Border trainer")
@app_commands.describe(trainer_name="Shinoda / Kido / Karasuma / Yūma")
async def train(interaction: discord.Interaction, trainer_name: str):
    user_id = interaction.user.id
    trainer_name = trainer_name.title()
    if trainer_name not in TRAINERS:
        await interaction.response.send_message("Invalid trainer.", ephemeral=True)
        return
    data = TRAINERS[trainer_name]
    async with aiosqlite.connect(DB_NAME) as db:
        if not await agent_required(interaction, db):
            return
        cursor = await db.execute("SELECT credits FROM agents WHERE user_id=?", (user_id,))
        creds = (await cursor.fetchone())[0]
        if creds < data["cost"]:
            await interaction.response.send_message(f"Need {data['cost']} credits.", ephemeral=True)
            return
        cursor = await db.execute(
            "SELECT attack, defense, mobility, intelligence, trion_control, perception FROM agent_stats WHERE user_id=?",
            (user_id,))
        stats = await cursor.fetchone()
        elo = (await db.execute("SELECT elo FROM agents WHERE user_id=?", (user_id,)))[0]
        cap = get_stat_cap(elo)
        used = sum(stats) - 6
        if isinstance(data["boost"], tuple):
            if used + 2 > cap:
                await interaction.response.send_message("Not enough cap space.", ephemeral=True)
                return
            await db.execute(f"UPDATE agent_stats SET {data['stats'][0]} = {data['stats'][0]} + 1, {data['stats'][1]} = {data['stats'][1]} + 1 WHERE user_id=?", (user_id,))
        else:
            if used + data["boost"] > cap:
                await interaction.response.send_message("Cap reached.", ephemeral=True)
                return
            await db.execute(f"UPDATE agent_stats SET {data['stat']} = {data['stat']} + {data['boost']} WHERE user_id=?", (user_id,))
        await db.execute("UPDATE agents SET credits = credits - ? WHERE user_id=?", (data["cost"], user_id))
        await db.commit()
    await interaction.response.send_message(embed=discord.Embed(title="💪 Training Complete", description=f"Trained with {trainer_name}!", color=COLOR))

@bot.tree.command(name="redeem", description="Redeem a special code for rewards")
@app_commands.describe(code="The code to redeem")
async def redeem(interaction: discord.Interaction, code: str):
    user_id = interaction.user.id
    code = code.upper()
    if code not in redeem_codes:
        await interaction.response.send_message(
            embed=discord.Embed(title="❌ Invalid Code", description="That code does not exist.", color=0xe74c3c),
            ephemeral=True)
        return
    rewards = redeem_codes[code]
    async with aiosqlite.connect(DB_NAME) as db:
        if not await agent_required(interaction, db):
            return
        cursor = await db.execute("SELECT 1 FROM redeemed_codes WHERE user_id=? AND code=?", (user_id, code))
        if await cursor.fetchone():
            await interaction.response.send_message("You have already redeemed this code.", ephemeral=True)
            return
        credits = rewards.get("credits", 0)
        spins = rewards.get("spins", 0)
        triggers_list = rewards.get("triggers", [])
        await db.execute("UPDATE agents SET credits = credits + ?, spins = spins + ? WHERE user_id=?",
                         (credits, spins, user_id))
        for trig in triggers_list:
            await db.execute("INSERT OR IGNORE INTO triggers (user_id, trigger) VALUES (?,?)", (user_id, trig))
        await db.execute("INSERT INTO redeemed_codes (user_id, code) VALUES (?,?)", (user_id, code))
        await db.commit()
    reward_msg = []
    if credits: reward_msg.append(f"💳 +{credits} Credits")
    if spins: reward_msg.append(f"🎰 +{spins} Spins")
    if triggers_list: reward_msg.append(f"⚙️ Triggers: {', '.join(triggers_list)}")
    await interaction.response.send_message(
        embed=discord.Embed(title="✅ Code Redeemed!",
                            description="\n".join(reward_msg) or "Nothing received.",
                            color=COLOR))

# ============================================================
# EVENTS
# ============================================================
@bot.event
async def on_ready():
    print(f"🔑 Logged in as {bot.user}")
    await init_db()
    load_redeem_codes()
    try:
        synced = await bot.tree.sync()
        print(f"⚡ Synced {len(synced)} commands")
    except Exception as e:
        print("❌ Sync failed:", e)

@bot.event
async def on_message(message):
    if message.author.bot: return
    if bot.user in message.mentions:
        await message.channel.send(
            embed=discord.Embed(title="👋 Welcome Agent!",
                                description=f"Hello {message.author.mention}! Start with **/joinborder**.",
                                color=COLOR))
    await bot.process_commands(message)

# ============================================================
# MAIN
# ============================================================
async def main():
    print("🚀 Starting bot...")
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
