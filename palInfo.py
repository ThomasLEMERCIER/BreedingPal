import copy
import json
import os
import sys
import traceback
from enum import Enum
import uuid
import copy
import math

from emptyObjects import *

xpthresholds = [
    0,
    25,
    56,
    93,
    138,
    207,
    306,
    440,
    616,
    843,
    1131,
    1492,
    1941,
    2495,
    3175,
    4007,
    5021,
    6253,
    7747,
    9555,
    11740,
    14378,
    17559,
    21392,
    26007,
    31561,
    38241,
    46272,
    55925,
    67524,
    81458,
    98195,
    118294,
    142429,
    171406,
    206194,
    247955,
    298134,
    358305,
    430525,
    517205,
    621236,
    746089,
    895928,
    1075751,
    1291554,
    1550533,
    1861323,
    2234286,
    2681857
]
if len(xpthresholds) < 50:
    print("Something is wrong with the thresholds")


class PalGender(Enum):
    MALE = "#02A3FE"
    FEMALE = "#EC49A6"
    UNKNOWN = "darkgrey"


class PalObject:
    def __init__(self, name, code_name, primary, secondary="None", human=False, tower=False, scaling=None, suits={}):
        self._name = name
        self._code_name = code_name
        self._img = None
        self._primary = primary
        self._secondary = secondary
        self._human = human
        self._tower = tower
        self._scaling = scaling
        self._suits = suits

    def GetName(self):
        return PalSpecies[self._code_name]._name # Update PalEdit.listdisplay

    def GetCodeName(self):
        return self._code_name

    def IsTower(self):
        return self._tower

    def GetPrimary(self):
        return self._primary

    def GetSecondary(self):
        return self._secondary

    def GetScaling(self):
        return self._scaling


class PalEntity:

    def __init__(self, data):

        self._data = data
        self._obj = data['value']['RawData']['value']['object']['SaveParameter']['value']

        self.owner = ""
        if "OwnerPlayerUId" in self._obj:
            self.owner = self._obj["OwnerPlayerUId"]['value']

        if "IsPlayer" in self._obj:
            raise Exception("This is a player character")

        if not "IsRarePal" in self._obj:
            self._obj["IsRarePal"] = copy.deepcopy(EmptyRarePalObject)
        self.isLucky = self._obj["IsRarePal"]['value']

        typename = self._obj['CharacterID']['value']
        # print(f"Debug: typename1 - {typename}")

        self.isBoss = False
        if typename[:5].lower() == "boss_":
            typename = typename[5:]  # if first 5 characters match boss_ then cut the first 5 characters off
            # typename = typename.replace("BOSS_", "") # this causes bugs
            self.isBoss = True if not self.isLucky else False
            if typename == "LazyCatFish":  # BOSS_LazyCatFish and LazyCatfish
                typename = "LazyCatfish"

        # print(f"Debug: typename2 - '{typename}'")
        if typename.lower() == "sheepball":
            typename = "Sheepball"

            # Strangely, Boss and Lucky Lamballs have camelcasing
            # Regular ones... don't
        # print(f"Debug: typename3 - '{typename}'")

        self._type = PalSpecies[typename]

        if "Gender" in self._obj:
            if self._obj['Gender']['value']['value'] == "EPalGenderType::Male":
                self._gender = "Male ♂"
            else:
                self._gender = "Female ♀"
        else:
            self._gender = "Unknown"

        self._workspeed = self._obj['CraftSpeed']['value']

        if not "Talent_HP" in self._obj:
            self._obj['Talent_HP'] = copy.deepcopy(EmptyMeleeObject)
            self._talent_hp = 0  # we set 0, so if its not changed it should be removed by the game again.
        self._talent_hp = self._obj['Talent_HP']['value']

        if not "Talent_Melee" in self._obj:
            self._obj['Talent_Melee'] = copy.deepcopy(EmptyMeleeObject)
        self._melee = self._obj['Talent_Melee']['value']

        if not "Talent_Shot" in self._obj:
            self._obj['Talent_Shot'] = copy.deepcopy(EmptyShotObject)
        self._ranged = self._obj['Talent_Shot']['value']

        if not "Talent_Defense" in self._obj:
            self._obj['Talent_Defense'] = copy.deepcopy(EmptyDefenceObject)
        self._defence = self._obj['Talent_Defense']['value']

        if not "Rank" in self._obj:
            self._obj['Rank'] = copy.deepcopy(EmptyRankObject)
        self._rank = self._obj['Rank']['value']

        # Fix broken ranks
        if self.GetRank() < 1 or self.GetRank() > 5:
            self.SetRank(1)

        if not "PassiveSkillList" in self._obj:
            self._obj['PassiveSkillList'] = copy.deepcopy(EmptySkillObject)
        self._skills = self._obj['PassiveSkillList']['value']['values']
        self.CleanseSkills()

        if not "Level" in self._obj:
            self._obj['Level'] = copy.deepcopy(EmptyLevelObject)
        self._level = self._obj['Level']['value']

        if not "Exp" in self._obj:
            self._obj['Exp'] = copy.deepcopy(EmptyExpObject)
        # We don't store Exp yet

        self._nickname = ""
        if "NickName" in self._obj:
            self._nickname = self._obj['NickName']['value']

        self.isTower = self._type.IsTower()

        self._storedLocation = self._obj['SlotID']
        self.storageId = self._storedLocation["value"]["ContainerId"]["value"]["ID"]["value"]
        self.storageSlot = self._storedLocation["value"]["SlotIndex"]["value"]

        if not "EquipWaza" in self._obj:
            self._obj["EquipWaza"] = copy.deepcopy(EmptyMovesObject)

        if not "MasteredWaza" in self._obj:
            self._obj["MasteredWaza"] = copy.deepcopy(EmptyMovesObject)

        self._learntMoves = self._obj["MasteredWaza"]["value"]["values"]
        self._equipMoves = self._obj["EquipWaza"]["value"]["values"]

        self.CleanseAttacks()
        if not "HP" in self._obj:
            self._obj["HP"] = copy.deepcopy(EmptyHpObject)
        self.UpdateMaxHP()

    def IsHuman(self):
        return self._type._human

    def IsTower(self):
        return self._type._tower

    def SwapGender(self):
        if self._obj['Gender']['value']['value'] == "EPalGenderType::Male":
            self._obj['Gender']['value']['value'] = "EPalGenderType::Female"
            self._gender = "Female ♀"
        else:
            self._obj['Gender']['value']['value'] = "EPalGenderType::Male"
            self._gender = "Male ♂"

    def CleanseSkills(self):
        i = 0
        while i < len(self._skills):
            if self._skills[i].lower() == "none":
                self._skills.pop(i)
            else:
                i += 1

    def GetAvailableSkills(self):
        avail_skills = []
        for skill_codename in SkillExclusivity:
            if skill_codename == '':
                continue
            if SkillExclusivity[skill_codename] is None or self._type.GetCodeName() in SkillExclusivity[skill_codename]:
                avail_skills.append(skill_codename)

        avail_skills.sort(key=lambda e: PalAttacks[e])
        avail_skills.remove("None")
        return avail_skills

    def CleanseAttacks(self):
        i = 0
        while i < len(self._learntMoves):
            remove = False
            if self._learntMoves[i] in ["None", "EPalWazaID::None"]:
                remove = True
            else:
                # Check skill has Exclusivity
                if not (SkillExclusivity[self._learntMoves[i]] is None):
                    if not self._type.GetCodeName() in SkillExclusivity[self._learntMoves[i]]:
                        remove = True
                # Check level are available for Skills
                if self._learntMoves[i] in PalLearnSet[self._type.GetCodeName()]:
                    if not self._level >= PalLearnSet[self._type.GetCodeName()][self._learntMoves[i]]:
                        if not self._learntMoves[i] in self._equipMoves:
                            remove = True

            if remove:
                if self._learntMoves[i] in self._equipMoves:
                    self._equipMoves.remove(self._learntMoves[i])
                self._learntMoves.pop(i)
            else:
                i += 1

        for skill_CodeName in PalLearnSet[self._type.GetCodeName()]:
            if not skill_CodeName in self._learntMoves:
                if PalLearnSet[self._type.GetCodeName()][skill_CodeName] <= self._level:
                    self._learntMoves.append(skill_CodeName)

        for i in self._equipMoves:
            if not i in self._learntMoves:
                self._learntMoves.append(i)

    def GetType(self):
        return self._type

    def SetType(self, value):
        self._obj['CharacterID']['value'] = ("BOSS_" if (self.isBoss or self.isLucky) else "") + value
        self._type = PalSpecies[value]
        self.CleanseAttacks()

        ss = copy.deepcopy(EmptySuitObject)
        for i in ss["value"]["values"]:
            t = i["WorkSuitability"]["value"]["value"].split("::")[1]
            i["Rank"]["value"] = self._type._suits[t]
        self._obj["CraftSpeeds"] = ss

    def GetObject(self) -> PalObject:
        return self._type

    def GetGender(self):
        return self._gender

    def GetWorkSpeed(self):
        return self._workspeed

    def SetWorkSpeed(self, value):
        self._obj['CraftSpeed']['value'] = self._workspeed = value

    def SetAttack(self, mval, rval):
        self._obj['Talent_Melee']['value'] = self._melee = mval
        self._obj['Talent_Shot']['value'] = self._ranged = rval

    def GetTalentHP(self):
        return self._talent_hp

    def SetTalentHP(self, value):
        self._obj['Talent_HP']['value'] = self._talent_hp = value

    # the soul bonus, 1 -> 3%, 10 -> 30%
    def GetRankHP(self):
        if "Rank_HP" in self._obj:
            return self._obj["Rank_HP"]["value"]
        return 0

    def GetRankAttack(self):
        if "Rank_Attack" in self._obj:
            return self._obj["Rank_Attack"]["value"]
        return 0

    def GetRankDefence(self):
        if "Rank_Defence" in self._obj:
            return self._obj["Rank_Defence"]["value"]
        return 0

    def GetRankWorkSpeed(self):
        if "Rank_CraftSpeed" in self._obj:
            return self._obj["Rank_CraftSpeed"]["value"]
        return 0

    def SetRankHP(self, value):
        if not "Rank_HP" in self._obj:
            self._obj["Rank_HP"] = copy.deepcopy(EmptySoulObject)
        self._obj["Rank_HP"]["value"] = value

    def SetRankAttack(self, value):
        if not "Rank_Attack" in self._obj:
            self._obj["Rank_Attack"] = copy.deepcopy(EmptySoulObject)
        self._obj["Rank_Attack"]["value"] = value

    def SetRankDefence(self, value):
        if not "Rank_Defence" in self._obj:
            self._obj["Rank_Defence"] = copy.deepcopy(EmptySoulObject)
        self._obj["Rank_Defence"]["value"] = value

    def SetRankWorkSpeed(self, value):
        if not "Rank_CraftSpeed" in self._obj:
            self._obj["Rank_CraftSpeed"] = copy.deepcopy(EmptySoulObject)
        self._obj["Rank_CraftSpeed"]["value"] = value

    def GetMaxHP(self):
        del self._obj['MaxHP']
        return # We dont need to get this anymore; its gone
    
        #return self._obj['MaxHP']['value']['Value']['value']

    def CalculateIngameStats(self):
        LEVEL = self.GetLevel()
        SCALING = self.GetObject().GetScaling()

        HP_SCALE = SCALING["HP"]
        if self.isBoss and "HP_BOSS" in SCALING:
            HP_SCALE = SCALING["HP_BOSS"]
        HP_IV = self.GetTalentHP() * 0.3 / 100
        HP_SOUL = self.GetRankHP() * 0.03
        HP_RANK = (self.GetRank() - 1) * 0.05
        HP_BONUS = 0

        HP_STAT = math.floor(500 + 5 * LEVEL + HP_SCALE * 0.5 * LEVEL * (1 + HP_IV))
        HP_STAT = math.floor(HP_STAT * (1 + HP_BONUS) * (1 + HP_SOUL) * (1 + HP_RANK))

        AT_SCALE = SCALING["ATK"]
        AT_IV = self.GetAttackRanged() * 0.3 / 100
        AT_SOUL = self.GetRankAttack() * 0.03
        AT_RANK = (self.GetRank() - 1) * 0.05
        AT_BONUS = 0

        AT_STAT = math.floor(100 + AT_SCALE * 0.075 * LEVEL * (1 + AT_IV))
        AT_STAT = math.floor(AT_STAT * (1 + AT_BONUS) * (1 + AT_SOUL) * (1 + AT_RANK))

        DF_SCALE = SCALING["DEF"]
        DF_IV = self.GetDefence() * 0.3 / 100
        DF_SOUL = self.GetRankDefence() * 0.03
        DF_RANK = (self.GetRank() - 1) * 0.05
        DF_BONUS = 0

        DF_STAT = math.floor(50 + DF_SCALE * 0.075 * LEVEL * (1 + DF_IV))
        DF_STAT = math.floor(DF_STAT * (1 + DF_BONUS) * (1 + DF_SOUL) * (1 + DF_RANK))
        return {"HP": HP_STAT, "ATK": AT_STAT, "DEF": DF_STAT}


    def UpdateMaxHP(self):
        return #this seems to be handled by the game itself now; impressive
        
        if self.IsTower() or self.IsHuman():
            return
        new_hp = self.CalculateIngameStats()["HP"]
        self._obj['MaxHP']['value']['Value']['value'] = new_hp * 1000
        self._obj['HP']['value']['Value']['value'] = new_hp * 1000

    def OLD_UpdateMaxHP(self, changes: dict, hp_scaling=None) -> bool:
        # do not manually pass in hp_scaling unless you are 100% sure that the value is correct!
        factors = {
            'level': self.GetLevel(),
            'rank': self.GetRank(),
            'hp_rank': self.GetRankHP(),
            'hp_iv': self.GetTalentHP()
        }

        old_hp = self.GetMaxHP()
        if hp_scaling is None:
            # assume old MaxHP is valid
            possible_hp_scaling = (old_hp / 1000 - 500 - 5 * factors['level']) / (
                    0.5 * factors['level'] * (1 + factors['hp_iv'] * 0.3 / 100) * (
                    1 + factors['hp_rank'] * 3 / 100) * (1 + (factors['rank'] - 1) * 5 / 100))
            print("--------")
            print("Derived Specie HP Scaling (from og MaxHP): ." % possible_hp_scaling)
            hp_scaling = possible_hp_scaling
            specie_scaling = self.GetObject().GetScaling()
            if specie_scaling:
                bossKey = "HP_BOSS"
                key = "HP"
                if self.isBoss and bossKey in specie_scaling:
                    hp_scaling = specie_scaling[bossKey]
                else:
                    hp_scaling = specie_scaling[key]
                    if self.isBoss and abs(possible_hp_scaling - hp_scaling) > 1 and 'species' not in changes:
                        return (possible_hp_scaling, hp_scaling)
                print(". HP Scaling: ." % (self.GetName(), hp_scaling))
            else:
                print("HP scaling data missing, using derived value.")
        print("Calculating MaxHP using the following stats:")
        for valkey in factors:
            if valkey in changes:
                factors[valkey] = changes[valkey]
            print("- .: ." % (valkey, factors[valkey]))
        print("- hp_scaling: ." % hp_scaling)

        new_hp = int((500 + 5 * factors['level'] + hp_scaling * 0.5 * factors['level'] * (
                1 + factors['hp_iv'] * 0.3 / 100) * (1 + factors['hp_rank'] * 3 / 100) * (
                              1 + (factors['rank'] - 1) * 5 / 100))) * 1000
        self._obj['MaxHP']['value']['Value']['value'] = new_hp
        self._obj['HP']['value']['Value']['value'] = new_hp
        print(". MaxHP: . -> ." % (self.GetFullName(), old_hp, new_hp))

    def GetAttackMelee(self):
        return self._melee

    def SetAttackMelee(self, value):
        self._obj['Talent_Melee']['value'] = self._melee = value

    def GetAttackRanged(self):
        return self._ranged

    def SetAttackRanged(self, value):
        self._obj['Talent_Shot']['value'] = self._ranged = value

    def GetDefence(self):
        return self._defence

    def SetDefence(self, value):
        self._obj['Talent_Defense']['value'] = self._defence = value

    def GetName(self):
        return self.GetObject().GetName()

    def GetCodeName(self):
        return self.GetObject().GetCodeName()

    def GetImage(self):
        return self.GetObject().GetImage()

    def GetPrimary(self):
        return self.GetObject().GetPrimary()

    def GetSecondary(self):
        return self.GetObject().GetSecondary()

    def GetSkills(self):
        self.CleanseSkills()
        return self._skills

    def SkillCount(self):
        return len(self._skills)

    def SetSkill(self, slot, skill):
        print("set slot %d  -> ." % (slot, skill))
        if slot > len(self._skills) - 1:
            self._skills.append(skill)
        else:
            self._skills[slot] = skill

    def SetAttackSkill(self, slot, attack):
        if slot > len(self._equipMoves) - 1:
            self._equipMoves.append(attack)
        else:
            self._equipMoves[slot] = attack
        self.CleanseAttacks()

    def GetOwner(self):
        return self.owner

    def GetLevel(self):
        return self._level

    def SetLevel(self, value):
        # We need this check until we fix adding missing nodes
        if "Level" in self._obj and "Exp" in self._obj:
            self._obj['Level']['value'] = self._level = value
            self._obj['Exp']['value'] = xpthresholds[value - 1]
            self.CleanseAttacks()  # self.SetLevelMoves()
        else:
            print(f"[ERROR:] Failed to update level for: '{self.GetName()}'")

    ##    def SetLevelMoves(self):
    ##        value = self._level
    ##        self._obj["MasteredWaza"]["value"]["values"] = self._learntMoves = self._learntBackup[:]
    ##        for i in PalLearnSet[self._type.GetCodeName()]:
    ##            if value >= PalLearnSet[self._type.GetCodeName()][i]:
    ##                if not find(i) in self._obj["MasteredWaza"]["value"]["values"]:
    ##                    self._obj["MasteredWaza"]["value"]["values"].append(find(i))
    ##            elif find(i) in self._obj["MasteredWaza"]["value"]["values"]:
    ##                self._obj["MasteredWaza"]["value"]["values"].remove(find(i))
    ##
    ##        for i in self._equipMoves:
    ##            if not matches(self._type.GetCodeName(), i):
    ##                self._equipMoves.remove(i)
    ##                self._obj["EquipWaza"]["value"]["values"] = self._equipMoves
    ##            elif not i in self._obj["MasteredWaza"]["value"]["values"]:
    ##                self._obj["MasteredWaza"]["value"]["values"].append(i)
    ##
    ##        self._learntMoves = self._obj["MasteredWaza"]["value"]["values"]
    ##        print("------")
    ##        for i in self._learntMoves:
    ##            print(i)

    def GetRank(self):
        return self._rank

    def SetRank(self, value):
        if "Rank" in self._obj:
            self._obj['Rank'][
                'value'] = self._rank = value  # we dont +1 here, since we have methods to patch rank in PalEdit.py
        else:
            print(
                f"[ERROR:] Failed to update rank for: '{self.GetName()}'")  # we probably could get rid of this line, since you add rank if missing - same with level

    def PurgeAttack(self, slot):
        if slot >= len(self._equipMoves):
            return
        p = self._equipMoves.pop(slot)
        if not p in PalLearnSet[self.GetCodeName()]:
            self._learntMoves.remove(p)
        else:
            if PalLearnSet[self.GetCodeName()][p] > self.GetLevel():
                self._learntMoves.remove(p)

    def StripAttack(self, name):
        strip = False
        if not name in self._equipMoves:
            if not name in PalLearnSet[self.GetCodeName()]:
                strip = True
            elif PalLearnSet[self.GetCodeName()][name] > self.GetLevel():
                strip = True
        if strip:
            self._learntMoves.remove(name)

    def FruitAttack(self, name):
        if not name in self._learntMoves:
            self._learntMoves.append(name)

    def RemoveSkill(self, slot):
        if slot < len(self._skills):
            self._skills.pop(slot)

    def RemoveAttack(self, slot):
        if slot < len(self._equipMoves):
            self._equipMoves.pop(slot)
        self.CleanseAttacks()

    def GetNickname(self):
        return self.GetName() if self._nickname == "" else self._nickname

    def GetFullName(self):
        return self.GetObject().GetName() + (" 💀" if self.isBoss else "") + (" ♖" if self.isTower else "") + (
            " ✨" if self.isLucky else "") + (f" - '{self._nickname}'" if not self._nickname == "" else "")

    def SetLucky(self, v=True):
        self._obj["IsRarePal"]['value'] = self.isLucky = v
        self.SetType(self._type.GetCodeName())
        if v:
            if self.isBoss:
                self.isBoss = False

    def SetBoss(self, v=True):
        self.isBoss = v
        self.SetType(self._type.GetCodeName())
        if v:
            if self.isLucky:
                self.SetLucky(False)

    def GetEquippedMoves(self):
        return self._equipMoves

    def GetLearntMoves(self):
        return self._learntMoves

    def InitializationPal(self, newguid, player, group, slot):
        self._data['key']['PlayerUId']['value'] = player
        self._obj["OwnerPlayerUId"]['value'] = player
        self._obj["OldOwnerPlayerUIds"]['value']['values'] = [player]
        self.SetPalInstanceGuid(newguid)
        self.SetSlotGuid(slot)
        self.SetGroupGuid(group)

    def GetGroupGuid(self):
        return self._data['value']['RawData']['value']['group_id']

    def SetGroupGuid(self, v: str):
        self._data['value']['RawData']['value']['group_id'] = v

    def GetSlotGuid(self):
        return self._obj['SlotID']['value']['ContainerId']['value']['ID']['value']

    def SetSlotGuid(self, v: str):
        self._obj['SlotID']['value']['ContainerId']['value']['ID']['value'] = v

    def GetSlotIndex(self):
        return self._obj['SlotID']['value']['SlotIndex']['value']

    def SetSoltIndex(self, v: int):
        self._obj['SlotID']['value']['SlotIndex']['value'] = v

    def GetPalInstanceGuid(self):
        return self._data['key']['InstanceId']['value']

    def SetPalInstanceGuid(self, v: str):
        self._data['key']['InstanceId']['value'] = v


class PalGuid:
    def __init__(self, data):
        self._data = data
        self._CharacterContainerSaveData = \
            data['properties']['worldSaveData']['value']['CharacterContainerSaveData']['value']
        self._GroupSaveDataMap = data['properties']['worldSaveData']['value']['GroupSaveDataMap']['value']

    def GetPlayerslist(self):
        players = list(filter(lambda x: 'IsPlayer' in x['value'], [
            {'uid': x['key']['PlayerUId'],
             'value': x['value']['RawData']['value']['object']['SaveParameter']['value']
             } for x in self._data['properties']['worldSaveData']['value']['CharacterSaveParameterMap']['value']]))

        out = {}
        for x in players:
            g = str(x['uid']['value'])
            if g.replace("0", "").replace("-", "") == "1":
                out[x['value']['NickName']['value'] + " (HOST)"] = g
            elif not x['value']['NickName']['value'] in out:
                out[x['value']['NickName']['value']] = g
            else:
                v = 2
                while f"{x['value']['NickName']['value']} #{v}" in out:
                    v += 1
                out[x['value']['NickName']['value'] + f" #{v}"] = g
            
        return out #{x['value']['NickName']['value']: str(x['uid']['value']) for x in players}

    def ConvertGuid(guid_str):
        guid_str = guid_str
        guid = uuid.UUID(guid_str)
        guid_bytes = guid.bytes
        guid_list = [b for b in guid_bytes]
        result_list = [0] * 16
        for n in range(0, len(guid_list), 4):
            result_list.extend(guid_list[n:n + 4][::-1])
        result_list.append(0)
        result_list[12] = 1
        return result_list

    def SetContainerSave(self, SoltGuid: str, SlotIndex: int, PalGuid: str):
        if any(guid == "00000000-0000-0000-0000-000000000000" for guid in [SoltGuid, PalGuid]):
            return
        for e in self._CharacterContainerSaveData:
            if (e['key']['ID']['value'] == SoltGuid):
                e['value']['Slots']['value']['values'][SlotIndex]['RawData']['value']['instance_id'] = PalGuid
                e['value']['Slots']['value']['values'][SlotIndex]['RawData']['value'][
                    'player_uid'] = "00000000-0000-0000-0000-000000000001"

    def AddGroupSaveData(self, GroupGuid: str, PalGuid: str):
        if any(guid == "00000000-0000-0000-0000-000000000000" for guid in [GroupGuid, PalGuid]):
            return
        for e in self._GroupSaveDataMap:
            if (e['key'] == GroupGuid):
                for ee in e['value']['RawData']['value']['individual_character_handle_ids']:
                    if (ee['instance_id'] == PalGuid):
                        return
                tmp = {"guid": "00000000-0000-0000-0000-000000000001", "instance_id": PalGuid}
                e['value']['RawData']['value']['individual_character_handle_ids'].append(tmp)

    def GetSoltMaxCount(self, SoltGuid: str):
        if SoltGuid == "00000000-0000-0000-0000-000000000000":
            return 0
        for e in self._CharacterContainerSaveData:
            if (e['key']['ID']['value'] == SoltGuid):
                return len(e['value']['Slots']['value']['values'])

    def GetEmptySlotIndex(self, SoltGuid: str):
        if SoltGuid == "00000000-0000-0000-0000-000000000000":
            return -1
        for e in self._CharacterContainerSaveData:
            if (e['key']['ID']['value'] == SoltGuid):
                Solt = e['value']['Slots']['value']['values']
                for i in range(len(Solt)):
                    if Solt[i]['RawData']['value']['instance_id'] == "00000000-0000-0000-0000-000000000000":
                        return i
        return -1

    def GetAdminGuid(self):
        for e in self._GroupSaveDataMap:
            if "admin_player_uid" in e['value']['RawData']['value']:
                return e['value']['RawData']['value']['admin_player_uid']

    def GetAdminGroupGuid(self):
        for e in self._GroupSaveDataMap:
            if "admin_player_uid" in e['value']['RawData']['value']:
                return e['key']

    def GetGroupGuid(self, playerguid):        
        for e in self._GroupSaveDataMap:
            if "players" in e['value']['RawData']['value']:
                for player in e['value']['RawData']['value']['players']:
                    if player['player_uid'] == playerguid:
                        return e['key']

    def RemanePlayer(self, PlayerGuid: str, NewName: str):
        for e in self._GroupSaveDataMap:
            if "players" in e['value']['RawData']['value']:
                for p in e['value']['RawData']['value']['players']:
                    if p['player_uid'] == PlayerGuid:
                        p['player_info']['player_name'] = NewName

    def Save(self, svdata):
        if 'properties' in svdata:
            svdata['properties']['worldSaveData']['value']['CharacterContainerSaveData'][
                'value'] = self._CharacterContainerSaveData
            svdata['properties']['worldSaveData']['value']['GroupSaveDataMap']['value'] = self._GroupSaveDataMap
        return svdata


class PalPlayerEntity:
    def __init__(self, data):
        self._data = data
        self._obj = self._data['properties']['SaveData']['value']
        self._record = self._obj['RecordData']['value']
        self._inventoryinfo = self._obj['inventoryInfo']['value']

    def GetPlayerGuid(self):
        return self._obj['PlayerUId']['value']

    def GetPlayerIndividualId(self):
        return self._obj['IndividualId']['value']['InstanceId']['value']

    def GetTravelPalInventoryGuid(self):
        return self._obj['OtomoCharacterContainerId']['value']['ID']['value']

    def GetPalStorageGuid(self):
        return self._obj['PalStorageContainerId']['value']['ID']['value']

    def GetCommonItemInventoryGuid(self):
        self._inventoryinfo['CommonContainerId']['value']['ID']['value']

    def GetKeyItemInventoryGuid(self):
        self._inventoryinfo['EssentialContainerId']['value']['ID']['value']

    def GetWeaponLoadOutInventoryGuid(self):
        self._inventoryinfo['WeaponLoadOutContainerId']['value']['ID']['value']

    def GetFoodInventoryGuid(self):
        self._inventoryinfo['FoodEquipContainerId']['value']['ID']['value']

    def GetPlayerEquipArmorGuid(self):
        self._inventoryinfo['PlayerEquipArmorContainerId']['value']['ID']['value']

    def SetLifmunkEffigyCount(self, v: int):
        if 'RelicPossessNum' in self._record:
            self._record['RelicPossessNum']['value'] = v
        else:
            self._record['RelicPossessNum'] = {'id': None, 'value': v, 'type': 'IntProperty'}

    def SetTechnologyPoint(self, v: int):
        self._obj['TechnologyPoint']['value'] = v

    def SetAncientTechnologyPoint(self, v: int):
        self._obj['bossTechnologyPoint']['value'] = v

    def dump(self):
        return self._data


with open("./resources/data/elements.json", "r", encoding="utf8") as elementfile:
    PalElements = {}
    for i in json.loads(elementfile.read())["values"]:
        PalElements[i['Name']] = i['Color']

PalSpecies = {}
# PalLearnSet: Pal Skills require Level
PalLearnSet = {}


def LoadPals(lang="en-GB"):
    global PalSpecies, PalLearnSet

    if lang == "":
        lang = "en-GB"

    if lang is not None and not os.path.exists(f"./resources/data/{lang}/pals.json"):
        lang = "en-GB"
    
    with open("./resources/data/pals.json", "r", encoding="utf8") as datafile:
        with open(f"./resources/data/{lang}/pals.json", "r", encoding="utf8") as palfile:
            PalSpecies = {}
            PalLearnSet = {}

            d = json.loads(datafile.read())
            l = json.loads(palfile.read())
            
            for i in d["values"]:
                h = "Human" in i
                t = "Tower" in i
                p = i["Type"][0]
                s = "None"
                if len(i["Type"]) == 2:
                    s = i["Type"][1]
                PalSpecies[i["CodeName"]] = PalObject(l[i["CodeName"]], i["CodeName"], p, s, h, t,
                                                      i["Scaling"] if "Scaling" in i else None,
                                                      i["Suitabilities"] if "Suitabilities" in i else {})
                if t:
                    PalSpecies[i["CodeName"]]._suits = PalSpecies[i["CodeName"].replace("GYM_", "")]._suits
                    PalSpecies[i["CodeName"]]._scaling = PalSpecies[i["CodeName"].replace("GYM_", "")]._scaling
                PalLearnSet[i["CodeName"]] = i["Moveset"] if not t else PalLearnSet[i["CodeName"].replace("GYM_", "")]


LoadPals()

PalPassives = {}
PassiveDescriptions = {}
PassiveRating = {}


def LoadPassives(lang="en-GB"):
    global PalPassives, PassiveDescriptions, PassiveRating

    PalPassives = {}
    PassiveDescriptions = {}
    PassiveRating = {}

    if lang == "":
        lang = "en-GB"

    if lang is not None and not os.path.exists(f"./resources/data/{lang}/passives.json"):
        lang = "en-GB"

    with open("./resources/data/passives.json", "r",
              encoding="utf8") as datafile:
        with open(f"./resources/data/{lang}/passives.json", "r",
                  encoding="utf8") as passivefile:

            d = json.loads(datafile.read())
            l = json.loads(passivefile.read())
            
            for i in d:
                code = i
                PalPassives[code] = l[code]["Name"]
                PassiveDescriptions[code] = l[code]["Description"]
                PassiveRating[code] = d[i]["Rating"]
            PalPassives = dict(sorted(PalPassives.items()))


LoadPassives()

# PalAttacks CodeName -> Name
PalAttacks = {}
AttackPower = {}
AttackTypes = {}
SkillExclusivity = {}


def LoadAttacks(lang="en-GB"):
    global PalAttacks, AttackPower, AttackTypes, SkillExclusivity

    if lang == "":
        lang = "en-GB"

    if lang is not None and not os.path.exists(f"./resources/data/{lang}/attacks.json"):
        lang = "en-GB"

    with open("./resources/data/attacks.json", "r",
              encoding="utf8") as datafile:
        with open(f"./resources/data/{lang}/attacks.json", "r",
                  encoding="utf8") as attackfile:
            PalAttacks = {}
            AttackPower = {}
            AttackTypes = {}
            SkillExclusivity = {}

            d = json.loads(datafile.read())
            l = json.loads(attackfile.read())

            #debugOutput = d["values"]

            for i in d:
                code = i
                PalAttacks[code] = l[code]
                AttackPower[code] = d[i]["Power"]
                AttackTypes[code] = d[i]["Type"]
                if "Exclusive" in d[i]:
                    SkillExclusivity[code] = d[i]["Exclusive"]
                else:
                    SkillExclusivity[code] = None

            PalAttacks = dict(sorted(PalAttacks.items()))

LoadAttacks()

PALWORLD_TYPE_HINTS: dict[str, str] = {
    ".worldSaveData.CharacterContainerSaveData.Key": "StructProperty",
    ".worldSaveData.CharacterSaveParameterMap.Key": "StructProperty",
    ".worldSaveData.CharacterSaveParameterMap.Value": "StructProperty",
    ".worldSaveData.FoliageGridSaveDataMap.Key": "StructProperty",
    ".worldSaveData.FoliageGridSaveDataMap.Value.ModelMap.Value": "StructProperty",
    ".worldSaveData.FoliageGridSaveDataMap.Value.ModelMap.Value.InstanceDataMap.Key": "StructProperty",
    ".worldSaveData.FoliageGridSaveDataMap.Value.ModelMap.Value.InstanceDataMap.Value": "StructProperty",
    ".worldSaveData.FoliageGridSaveDataMap.Value": "StructProperty",
    ".worldSaveData.ItemContainerSaveData.Key": "StructProperty",
    ".worldSaveData.MapObjectSaveData.MapObjectSaveData.ConcreteModel.ModuleMap.Value": "StructProperty",
    ".worldSaveData.MapObjectSaveData.MapObjectSaveData.Model.EffectMap.Value": "StructProperty",
    ".worldSaveData.MapObjectSpawnerInStageSaveData.Key": "StructProperty",
    ".worldSaveData.MapObjectSpawnerInStageSaveData.Value": "StructProperty",
    ".worldSaveData.MapObjectSpawnerInStageSaveData.Value.SpawnerDataMapByLevelObjectInstanceId.Key": "Guid",
    ".worldSaveData.MapObjectSpawnerInStageSaveData.Value.SpawnerDataMapByLevelObjectInstanceId.Value": "StructProperty",
    ".worldSaveData.MapObjectSpawnerInStageSaveData.Value.SpawnerDataMapByLevelObjectInstanceId.Value.ItemMap.Value": "StructProperty",
    ".worldSaveData.WorkSaveData.WorkSaveData.WorkAssignMap.Value": "StructProperty",
    ".worldSaveData.BaseCampSaveData.Key": "Guid",
    ".worldSaveData.BaseCampSaveData.Value": "StructProperty",
    ".worldSaveData.BaseCampSaveData.Value.ModuleMap.Value": "StructProperty",
    ".worldSaveData.ItemContainerSaveData.Value": "StructProperty",
    ".worldSaveData.CharacterContainerSaveData.Value": "StructProperty",
    ".worldSaveData.GroupSaveDataMap.Key": "Guid",
    ".worldSaveData.GroupSaveDataMap.Value": "StructProperty",
    ".worldSaveData.EnemyCampSaveData.EnemyCampStatusMap.Value": "StructProperty",
    ".worldSaveData.DungeonSaveData.DungeonSaveData.MapObjectSaveData.MapObjectSaveData.Model.EffectMap.Value": "StructProperty",
    ".worldSaveData.DungeonSaveData.DungeonSaveData.MapObjectSaveData.MapObjectSaveData.ConcreteModel.ModuleMap.Value": "StructProperty",
    ".worldSaveData.InvaderSaveData.Key": "Guid",
    ".worldSaveData.InvaderSaveData.Value": "StructProperty",
}

from typing import Any, Callable

from palworld_save_tools.archive import FArchiveReader, FArchiveWriter
from palworld_save_tools.rawdata import (
    base_camp,
    base_camp_module,
    character,
    character_container,
    dynamic_item,
    foliage_model,
    foliage_model_instance,
    group,
    item_container,
    item_container_slots,
    map_object,
    work,
    work_collection,
    worker_director,
)

PALWORLD_CUSTOM_PROPERTIES: dict[
    str,
    tuple[
        Callable[[FArchiveReader, str, int, str], dict[str, Any]],
        Callable[[FArchiveWriter, str, dict[str, Any]], int],
    ],
] = {
    ".worldSaveData.GroupSaveDataMap": (group.decode, group.encode),
    ".worldSaveData.CharacterSaveParameterMap.Value.RawData": (
        character.decode,
        character.encode,
    ),
    ".worldSaveData.ItemContainerSaveData.Value.RawData": (
        item_container.decode,
        item_container.encode,
    ),
    ".worldSaveData.ItemContainerSaveData.Value.Slots.Slots.RawData": (
        item_container_slots.decode,
        item_container_slots.encode,
    ),
    # This isn't actually serialised into at all?
    # ".worldSaveData.CharacterContainerSaveData.Value.RawData": (debug.decode, debug.encode),
    # This duplicates the data already serialised into the Slots UObject?
    ".worldSaveData.CharacterContainerSaveData.Value.Slots.Slots.RawData": (
        character_container.decode,
        character_container.encode,
    ),
    ".worldSaveData.DynamicItemSaveData.DynamicItemSaveData.RawData": (
        dynamic_item.decode,
        dynamic_item.encode,
    ),
    ".worldSaveData.FoliageGridSaveDataMap.Value.ModelMap.Value.RawData": (
        foliage_model.decode,
        foliage_model.encode,
    ),
    ".worldSaveData.FoliageGridSaveDataMap.Value.ModelMap.Value.InstanceDataMap.Value.RawData": (
        foliage_model_instance.decode,
        foliage_model_instance.encode,
    ),
    ".worldSaveData.BaseCampSaveData.Value.RawData": (
        base_camp.decode,
        base_camp.encode,
    ),
    ".worldSaveData.BaseCampSaveData.Value.WorkerDirector.RawData": (
        worker_director.decode,
        worker_director.encode,
    ),
    ".worldSaveData.BaseCampSaveData.Value.WorkCollection.RawData": (
        work_collection.decode,
        work_collection.encode,
    ),
    ".worldSaveData.BaseCampSaveData.Value.ModuleMap": (
        base_camp_module.decode,
        base_camp_module.encode,
    ),
    ".worldSaveData.WorkSaveData": (work.decode, work.encode),
    ".worldSaveData.MapObjectSaveData": (
        map_object.decode,
        map_object.encode,
    ),
}

def skip_decode(
        reader: FArchiveReader, type_name: str, size: int, path: str
):
    if type_name == "ArrayProperty":
        array_type = reader.fstring()
        value = {
            "skip_type": type_name,
            "array_type": array_type,
            "id": reader.optional_guid(),
            "value": reader.read(size)
        }
    elif type_name == "MapProperty":
        key_type = reader.fstring()
        value_type = reader.fstring()
        _id = reader.optional_guid()
        value = {
            "skip_type": type_name,
            "key_type": key_type,
            "value_type": value_type,
            "id": _id,
            "value": reader.read(size),
        }
    elif type_name == "StructProperty":
        value = {
            "skip_type": type_name,
            "struct_type": reader.fstring(),
            "struct_id": reader.guid(),
            "id": reader.optional_guid(),
            "value": reader.read(size),
        }
    else:
        raise Exception(
            f"Expected ArrayProperty or MapProperty or StructProperty, got {type_name} in {path}"
        )
    return value


def skip_encode(
        writer: FArchiveWriter, property_type: str, properties: dict
) -> int:
    if "skip_type" not in properties:
        if properties['custom_type'] in PALWORLD_CUSTOM_PROPERTIES is not None:
            # print("process parent encoder -> ", properties['custom_type'])
            return PALWORLD_CUSTOM_PROPERTIES[properties["custom_type"]][1](
                writer, property_type, properties
            )
        else:
            # Never be run to here
            return writer.property_inner(writer, property_type, properties)
    if property_type == "ArrayProperty":
        del properties["custom_type"]
        del properties["skip_type"]
        writer.fstring(properties["array_type"])
        writer.optional_guid(properties.get("id", None))
        writer.write(properties["value"])
        return len(properties["value"])
    elif property_type == "MapProperty":
        del properties["custom_type"]
        del properties["skip_type"]
        writer.fstring(properties["key_type"])
        writer.fstring(properties["value_type"])
        writer.optional_guid(properties.get("id", None))
        writer.write(properties["value"])
        return len(properties["value"])
    elif property_type == "StructProperty":
        del properties["custom_type"]
        del properties["skip_type"]
        writer.fstring(properties["struct_type"])
        writer.guid(properties["struct_id"])
        writer.optional_guid(properties.get("id", None))
        writer.write(properties["value"])
        return len(properties["value"])
    else:
        raise Exception(
            f"Expected ArrayProperty or MapProperty or StructProperty, got {property_type}"
        )


PALEDIT_PALWORLD_CUSTOM_PROPERTIES = copy.deepcopy(PALWORLD_CUSTOM_PROPERTIES)
PALEDIT_PALWORLD_CUSTOM_PROPERTIES[".worldSaveData.MapObjectSaveData"] = (skip_decode, skip_encode)
PALEDIT_PALWORLD_CUSTOM_PROPERTIES[".worldSaveData.FoliageGridSaveDataMap"] = (skip_decode, skip_encode)
PALEDIT_PALWORLD_CUSTOM_PROPERTIES[".worldSaveData.MapObjectSpawnerInStageSaveData"] = (skip_decode, skip_encode)
PALEDIT_PALWORLD_CUSTOM_PROPERTIES[".worldSaveData.DynamicItemSaveData"] = (skip_decode, skip_encode)
#PALEDIT_PALWORLD_CUSTOM_PROPERTIES[".worldSaveData.CharacterContainerSaveData"] = (skip_decode, skip_encode)
PALEDIT_PALWORLD_CUSTOM_PROPERTIES[".worldSaveData.ItemContainerSaveData"] = (skip_decode, skip_encode)
#PALEDIT_PALWORLD_CUSTOM_PROPERTIES[".worldSaveData.GroupSaveDataMap"] = (skip_decode, skip_encode)

import zlib

MAGIC_BYTES = b"PlZ"


def decompress_sav_to_gvas(data: bytes) -> tuple[bytes, int]:
    uncompressed_len = int.from_bytes(data[0:4], byteorder="little")
    compressed_len = int.from_bytes(data[4:8], byteorder="little")
    magic_bytes = data[8:11]
    save_type = data[11]
    data_start_offset = 12
    # Check for magic bytes
    if magic_bytes == b"CNK":
        uncompressed_len = int.from_bytes(data[12:16], byteorder="little")
        compressed_len = int.from_bytes(data[16:20], byteorder="little")
        magic_bytes = data[20:23]
        save_type = data[23]
        data_start_offset = 24
    if magic_bytes != MAGIC_BYTES:
        if (
            magic_bytes == b"\x00\x00\x00"
            and uncompressed_len == 0
            and compressed_len == 0
        ):
            raise Exception(
                f"not a compressed Palworld save, found too many null bytes, this is likely corrupted"
            )
        raise Exception(
            f"not a compressed Palworld save, found {magic_bytes!r} instead of {MAGIC_BYTES!r}"
        )
    # Valid save types
    if save_type not in [0x30, 0x31, 0x32]:
        raise Exception(f"unknown save type: {save_type}")
    # We only have 0x31 (single zlib) and 0x32 (double zlib) saves
    if save_type not in [0x31, 0x32]:
        raise Exception(f"unhandled compression type: {save_type}")
    if save_type == 0x31:
        # Check if the compressed length is correct
        if compressed_len != len(data) - data_start_offset:
            raise Exception(f"incorrect compressed length: {compressed_len}")
    # Decompress file
    uncompressed_data = zlib.decompress(data[data_start_offset:])
    if save_type == 0x32:
        # Check if the compressed length is correct
        if compressed_len != len(uncompressed_data):
            raise Exception(f"incorrect compressed length: {compressed_len}")
        # Decompress file
        uncompressed_data = zlib.decompress(uncompressed_data)
    # Check if the uncompressed length is correct
    if uncompressed_len != len(uncompressed_data):
        raise Exception(f"incorrect uncompressed length: {uncompressed_len}")

    return uncompressed_data, save_type


def compress_gvas_to_sav(data: bytes, save_type: int) -> bytes:
    uncompressed_len = len(data)
    compressed_data = zlib.compress(data)
    compressed_len = len(compressed_data)
    if save_type == 0x32:
        compressed_data = zlib.compress(compressed_data)

    # Create a byte array and append the necessary information
    result = bytearray()
    result.extend(uncompressed_len.to_bytes(4, byteorder="little"))
    result.extend(compressed_len.to_bytes(4, byteorder="little"))
    result.extend(MAGIC_BYTES)
    result.extend(bytes([save_type]))
    result.extend(compressed_data)

    return bytes(result)

def find(name):
    for i in PalSpecies:
        if PalSpecies[i].GetName() == name:
            return i
    for i in PalPassives:
        if PalPassives[i] == name:
            return i
    for i in PalAttacks:
        if PalAttacks[i] == name:
            return i
    return "None"

def loadpal(paldata, palguidmanager):
    palbox = {}
    players = {}
    players = palguidmanager.GetPlayerslist()
    for p in players:
        palbox[players[p]] = []
    nullmoves = []

    erroredpals = []
    for i in paldata:
        try:
            p = PalEntity(i)
            if not str(p.owner) in palbox:
                palbox[str(p.owner)] = []
            palbox[str(p.owner)].append(p)

            n = p.GetFullName()

            for m in p.GetLearntMoves():
                if not m in nullmoves:
                    if not m in PalAttacks:
                        nullmoves.append(m)
        except Exception as e:
            if str(e) == "This is a player character":
                print(f"Found player character: {i['key']['InstanceId']['value']}")
            else:
                try:
                    erroredpals.append(i)
                except:
                    erroredpals.append(None)
                print(f"Error occured on {i['key']['InstanceId']['value']}")
    
    return palbox

from gvas import GvasFile

def loadPalData(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
        raw_gvas, _  = decompress_sav_to_gvas(data)

    gvas_file = GvasFile.read(raw_gvas, PALWORLD_TYPE_HINTS, PALEDIT_PALWORLD_CUSTOM_PROPERTIES)
    data = {
            'gvas_file': gvas_file,
            'properties': gvas_file.properties
    }
    paldata = data['properties']['worldSaveData']['value']['CharacterSaveParameterMap']['value']
    palguidmanager = PalGuid(data)
    palbox = loadpal(paldata, palguidmanager)
    return palbox, palguidmanager
