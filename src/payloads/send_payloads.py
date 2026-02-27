from abc import ABC
from typing import Any, ClassVar, Literal, Self, Type

from pydantic import (BaseModel, ConfigDict, Field, SerializeAsAny,
                      model_validator)


# Abstract base class for all the payload data
# base model for all the payloads
class PayloadData(BaseModel, ABC):
    _registry: ClassVar[dict[str, Type["PayloadData"]]] = {}

    def __init_subclass__(cls, **kwargs: Any):
        super().__init_subclass__(**kwargs)
        # Always register by class name
        cls._registry[cls.__name__] = cls
    # try to ensure we don't have extra fields, and we can use arbitrary classes to validate
    model_config = ConfigDict(extra='forbid', from_attributes=True)

class SendMessage(BaseModel):
    message: str | None = None
    payload: SerializeAsAny[PayloadData]

    @model_validator(mode='after')
    def set_message(self) -> Self:
        message = self.message
        # payload already exists and is validated
        if message is None:
            setattr(self, "message", self.payload.__class__.__name__)
        return self

# USAGE:
# You can put just "payload" and it will pull the name
# SendMessage(payload=ButtonPos(x=1, y=2))
# WARNING: class __name__ should be the same as the class
# __name__ for it to work properly!



class ButtonPos(PayloadData):
    x: int
    y: int

class Preference(PayloadData):
    preferenceName: str
    preferenceValue: int
    preferenceForced: bool
    preferenceState: str

class General(PayloadData):
    preferences: list[Preference]

class Gameplay(PayloadData):
    preferences: list[Preference]
    zoomOptionsHd: list[int]
    zoomOptionsSd: list[int]
    currentSelectedZoom: int

class Input(PayloadData):
    preferences: list[Preference]
    customKeys: str

class Video(PayloadData):
    monitorlist: list[dict[str, Any]]
    monitorSelected: int
    displayModes: list[dict[str, Any]]
    displayMode: int
    preferences: list[Preference]

class Sound(PayloadData):
    preferences: list[Preference]
    audioDevicelist: list[dict[str, Any]]
    audioDeviceIndex: int
    PREF_SOUND_MUSIC_OVERRIDE: str
    locales: list[str]
    musicOverrideIndex: int

class Hotkeys(PayloadData):
    definitions: list[dict[str, Any]]

class SetAndSaveOptionAll(PayloadData):
    general: General
    gameplay: Gameplay
    input: Input
    video: Video
    sound: Sound
    hotkeys: Hotkeys
    reforged: General
    isRefresh: bool

class SetOptionSingle(PayloadData):
    name: str
    value: int

class SendGameChatMessage(PayloadData):
    content: str

class JoinGame(PayloadData):
    gameId: int
    password: str = Field(default='')
    mapFile: str

class SetComputerSlot(PayloadData):
    slot: int
    difficulty: int

class MapSettings(PayloadData):
    flagLockTeams: bool
    flagPlaceTeamsTogether: bool
    flagFullSharedUnitControl: bool
    flagRandomRaces: bool
    flagRandomHero: bool
    settingObservers: Literal[0, 1, 2, 3]
    settingVisibility: Literal[0, 1, 2, 3]

class CreateLobby(PayloadData):
    filename: str
    gameName: str
    gameSpeed: Literal[0, 1, 2, 3]
    privateGame: bool
    mapSettings: MapSettings

class GetMaplist(PayloadData):
    useLastMap: bool

class SetIMEEnabled(PayloadData):
    enable: bool

class SetGameMode(PayloadData):
    gameMode: str
    race: str

class GetChatMemberStats(PayloadData):
    battleTag: str
    gatewayId: int

class GetPlayerLeaderboardTournamentPage(PayloadData):
    query: str
    tournamentState: str

class GetMapVetosFromGameMode(PayloadData):
    gameMode: str
    seasonId: str

class OnCustomCampaignToggle(PayloadData):
    customCampaign: bool

class SetInReplayMenu(PayloadData):
    inReplayMenu: bool

class PlaySound(PayloadData):
    sound: str

class PlayAmbientSound(PayloadData):
    sound: str
    labelAsFilename: bool

class ScreenTransitionInfo(PayloadData):
    screen: str = Field(default="LOGIN_DOORS")
    type: str = Field(default="Screen")
    time: str

class SetHandicap(PayloadData):
    slot: int
    handicap: Literal[50, 60, 70, 80, 90, 100]

class SetTeam(PayloadData):
    slot: int
    team: int

class CloseSlot(PayloadData):
    slot: int

class OpenSlot(PayloadData):
    slot: int

class BanPlayerFromGameLobby(PayloadData):
    slot: int

class KickPlayerFromGameLobby(PayloadData):
    slot: int

class LobbyStart(PayloadData):
    pass

class LeaveGame(PayloadData):
    pass

class ExitGame(PayloadData):
    pass

class LobbyCancel(PayloadData):
    pass

class GetGameList(PayloadData):
    pass

class SendGameListing(PayloadData):
    pass

class GetLocalPlayerName(PayloadData):
    pass

class FriendsGetInvitations(PayloadData):
    pass

class FriendsGetFriends(PayloadData):
    pass

class MultiplayerSendRecentPlayers(PayloadData):
    pass

class ClanGetClanInfo(PayloadData):
    pass

class ClanGetMembers(PayloadData):
    pass

class StopOverworldMusic(PayloadData):
    pass

class StopAmbientSound(PayloadData):
    pass

class LoginDoorClose(PayloadData):
    pass

class OnWebUILoad(PayloadData):
    pass
