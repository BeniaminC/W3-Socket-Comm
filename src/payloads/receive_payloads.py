from abc import ABC
from typing import Any, ClassVar, Type

from pydantic import (BaseModel, ConfigDict, Field, SerializeAsAny,
                      ValidationInfo, field_validator, model_validator)


# base model for all the payloads
class PayloadData(BaseModel, ABC):
    _registry: ClassVar[dict[str, Type["PayloadData"]]] = {}

    # every time we create a class we add it to the registry
    def __init_subclass__(cls, **kwargs: Any):
        super().__init_subclass__(**kwargs)
        # Always register by class name
        cls._registry[cls.__name__] = cls

    model_config = ConfigDict(extra="forbid", from_attributes=True)


class RecMessage(BaseModel):
    messageType: str
    payload: SerializeAsAny[PayloadData]

    @field_validator("payload", mode="before")
    @classmethod
    def validate_payload(cls, v: PayloadData, info: ValidationInfo):
        message_type = info.data.get("messageType")
        if message_type not in PayloadData._registry:
            raise ValueError(f"BaseModel not registered: {message_type}")
        model_class = PayloadData._registry[message_type]
        if isinstance(v, model_class):
            return v  # already the right subclass
        return model_class.model_validate(v)  # coerce dict into subclass

    # run validation
    @model_validator(mode="after")
    def verify_payload(self) -> "RecMessage":
        if self.messageType not in PayloadData._registry:
            raise ValueError(f"BaseModel not registered: {self.messageType}")
        model_class = PayloadData._registry[self.messageType]
        self.payload = model_class.model_validate(self.payload)
        return self


# USAGE:
# You can put just messageType
# rec = RecMessage(messageType="GameVersion")
# rec = RecMessage(messageType="GameVersion",
#                  payload=GameVersion(gameVersion="1.0.0")
#                  )
# WARNING: You should create the class __name__ the same
# as the messageType for registration to work properly


class KeyValue(PayloadData):
    key: str
    value: str

class ListModel(PayloadData):
    KeyValues: list[KeyValue]

class LocalizationValues(PayloadData):
    list: ListModel

class GameVersion(PayloadData):
    gameVersion: str

class BuildType(PayloadData):
    buildType: str

class PreloadComplete(PayloadData):
    empty: str = Field(..., alias="")

class HideModal(PayloadData):
    empty: str = Field(..., alias="")

class SetMainMenuTheme(PayloadData):
    mainMenuTheme: int

class localeInfo(PayloadData):
    fonts: list["Font"]
    locale: str

class Font(PayloadData):
    name: str
    path: str

class LocaleInfo(PayloadData):
    localeInfo: localeInfo

class UpdateUserInfo(PayloadData):
    user: "User"

class User(PayloadData):
    toonName: str | None = Field(default=None)
    username: str
    localPlayerName: str
    battleTag: str
    avatarId: str
    isSelf: bool
    shouldDisableCustomGames: bool
    isAuthenticated: bool
    isTeamMember: bool
    isTeamLeader: bool
    isInGame: bool
    ageRatingRequired: str
    userRegion: str
    regionBlockedContent: bool
    gatewayId: int
    seasonalInfoSeen: bool
    isHDModeEnabled: bool
    hasRequiredHDHardware: bool
    hasReforged: bool
    isOfflineAllowed: bool

class SetGlueScreen(PayloadData):
    screen: str

class GameModeUpdated(PayloadData):
    message: "Message"

class Message(PayloadData):
    gameMode: int

class ClanInfoData(PayloadData):
    data: "Data"

class Data(PayloadData):
    clanId: int
    clanName: str
    clanAbbreviation: str
    description: str
    motd: str

class ClanMembersData(PayloadData):
    data: "Data2"

class Data2(PayloadData):
    members: list[Any]

class OnChannelLeave(PayloadData):
    channel: "Channel | None" = Field(default=None)
    gameChat: "GameChat | None" = Field(default=None)
    clan: dict[str, Any] | None = Field(default=None)

class FriendsInvitationUpdated(PayloadData):
    data: "Data3"

class Data3(PayloadData):
    invitationId: str
    toonName: str

class ShowAgeRatingScreen(PayloadData):
    message: "Message2"

class Message2(PayloadData):
    ageRatingScreenRequired: str

class OnNetProviderChanged(PayloadData):
    providerId: str

class OnGetAgeRatingRequired(PayloadData):
    message: "Message3"

class Message3(PayloadData):
    ageRatingRequired: str

class HotkeysIds(PayloadData):
    keycodes: "Keycodes"

class Keycodes(PayloadData):
    ids: list[str]

class ChatMessage(PayloadData):
    message: "Message4"

class Message4(PayloadData):
    content: str | None = Field(default=None)
    type: str | None = Field(default=None)
    sender: str | None = Field(default=None)
    channelName: str | None = Field(default=None)
    channelDisplayName: str | None = Field(default=None)
    source: str | None = Field(default=None)
    isSquelched: bool | None = Field(default=None)
    channelId: str | None = Field(default=None)
    auroraId: int | None = Field(default=None)
    clanAbbr: str | None = Field(default=None)

class UpdateToonList(PayloadData):
    toons: "Toons"

class Toons(PayloadData):
    toons: list["Toon"]

class Toon(PayloadData):
    id: int
    gatewayId: int
    name: str

class ProfileAvatarId(PayloadData):
    data: "Data4"

class Data4(PayloadData):
    avatarId: str
    battleTag: str
    gatewayId: int

class RankedSeasonalInfoUpdate(PayloadData):
    seasonInfo: "SeasonInfo"

class SeasonInfo(PayloadData):
    seasonId: int
    startTime: int
    endTime: int
    divisions: list["Division"]

class Division(PayloadData):
    lowerBoundMMR: int
    upperBoundMMR: int
    divisionId: int
    topDivision: bool

class ArrangedTeamStats(PayloadData):
    message: "Message5"

class Message5(PayloadData):
    gameTypes: list[Any]

class Member(PayloadData):
    id: str | None = Field(default=None)
    name: str | None = Field(default=None)
    isOnline: bool | None = Field(default=None)
    isAway: bool | None = Field(default=None)
    isBusy: bool | None = Field(default=None)
    avatarId: str | None = Field(default=None)
    status: int | None = Field(default=None)
    channelType: int | None = Field(default=None)
    isSquelched: bool | None = Field(default=None)
    clanAbbr: str | None = Field(default=None)
    clanId: int | None = Field(default=None)
    isInClan: bool | None = Field(default=None)
    xp: int | None = Field(default=None)
    gatewayId: int | None = Field(default=None)
    playerRegion: str | None = Field(default=None)

class GameChat(PayloadData):
    name: str
    gameName: str
    members: list[Member]

class OnChannelJoin(PayloadData):
    gameChat: GameChat | None = Field(default=None)
    channel: "Channel | None" = Field(default=None)

class OnChannelJoinMembersEntity(PayloadData):
    id: str
    name: str
    status: int
    avatarId: str
    isSquelched: bool

class OnChannelUpdate(PayloadData):
    channel: "Channel | None" = Field(default=None)
    members: list[Member] | None = Field(default=None)
    isConnected: bool | None = Field(default=None)
    source: str | None = Field(default=None)
    gameChat: GameChat | None = Field(default=None)


class Channel(PayloadData):
    name: str | None = Field(default=None)
    displayName: str | None = Field(default=None)
    channelId: str | None = Field(default=None)
    auroraId: int | None = Field(default=None)
    channelNumber: int | None = Field(default=None)
    channelType: int | None = Field(default=None)
    members: list[Member] | None = Field(default=None)
    isConnected: bool | None = Field(default=None)
    source: str | None = Field(default=None)

class IsGameUIActive(PayloadData):
    isActive: bool

class UpdateSelectedGameMode(PayloadData):
    message: "Message6"

class Message6(PayloadData):
    gameMode: str
    triggeredByTeamHost: bool | None = Field(default=None)

class FriendsFriendUpdated(PayloadData):
    data: "Data5"

class Data5(PayloadData):
    accountId: int
    friend: "Friend"

class Friend(PayloadData):
    localRichPresenceAttributes: list[Any]
    accountId: int | None = Field(default=None)
    fullName: str | None = Field(default=None)
    battleTag: str | None = Field(default=None)
    isOnline: bool | None = Field(default=None)
    isFriend: bool | None = Field(default=None)
    isAway: bool | None = Field(default=None)
    isBusy: bool | None = Field(default=None)
    inProgram: bool | None = Field(default=None)
    inParty: bool | None = Field(default=None)
    currentProgram: str | None = Field(default=None)
    globalRichPresence: str | None = Field(default=None)
    gatewayId: int | None = Field(default=None)
    avatarId: str | None = Field(default=None)

class TeamsInformation(PayloadData):
    message: "Message7"

class PartyMember(PayloadData):
    memberId: int
    gatewayId: int
    auroraId: int
    joinOrder: int
    teamOrder: int
    isOwner: bool
    isSelf: bool
    isReady: bool
    toonName: str
    clanName: str
    battleTag: str
    preferredRace: str
    avatarId: str


class Message7(PayloadData):
    lobbyId: int
    memberCount: int
    partyMembers: list[Any]
    isHost: bool

class OnNetProviderInitialized(PayloadData):
    message: "Message8"

class Message8(PayloadData):
    isOnline: bool

class GameModeResolved(PayloadData):
    message: "Clan"

class Clan(PayloadData):
    # Empty object - use dict[str, Any] if needed
    pass

class UpdateMapVetos(PayloadData):
    message: "Message12"

class Message12(PayloadData):
    mapVetos: list[Any]

class UpdateIsUnranked(PayloadData):
    message: "Message11"

class Message11(PayloadData):
    isUnranked: bool

class UpdateLobbySelectedRace(PayloadData):
    message: "Message10"

class Message10(PayloadData):
    selectedRace: str

class FriendsFriendRemoved(PayloadData):
    data: "Data6"

class Data6(PayloadData):
    accountId: int

class UpdateReadyState(PayloadData):
    message: "Message9"

class Message9(PayloadData):
    readyUpState: str
    memberCount: int
    memberList: list[Any]
    isHost: bool

class UpdateGameModes(PayloadData):
    gameModes: "GameModes"

class GameModes(PayloadData):
    tournament: "Tournament"
    sffa: "Sffa"
    mode_1v1: "Sffa" = Field(..., alias="1v1")
    mode_2v2: "Sffa" = Field(..., alias="2v2")
    mode_3v3: "Sffa" = Field(..., alias="3v3")
    mode_4v4: "Sffa" = Field(..., alias="4v4")
    isBreak: bool | None =  Field(default=None)

class Sffa(PayloadData):
    name: str
    numMapVetosAllowed: int
    minNumPlayers: int
    maxNumPlayers: int

class Tournament(PayloadData):
    name: str
    numMapVetosAllowed: int
    minNumPlayers: int
    maxNumPlayers: int
    tournamentInfo: "TournamentInfo"
    nextTournamentInfos: list["TournamentInfo"]

class TournamentInfo(PayloadData):
    isBreak: bool
    name: str
    startTimeEpoch: int
    teamPlayerCount: int
    tournamentState: int
    maps: list["Map"] | None = Field(default=None)
    allowedRaces: list[str]
    preliminaryInfo: "PreliminaryInfo"
    preliminaryToEliminiationBreakDurationMins: int
    eliminationRoundInfo: list["EliminationRoundInfo"]
    finalsStartTimeEpoch: int
    endTimeEpoch: int

class EliminationRoundInfo(PayloadData):
    roundDurationMins: int
    roundQueueDurationMins: int
    matchFinishSoonTriggerTimeMins: int
    matchFinishTimeMins: int

class PreliminaryInfo(PayloadData):
    preliminaryMatchmakingDurationMins: int
    preliminaryNoMatchmakingDurationMins: int
    matchFinishSoonTriggerTimeMins: int
    matchFinishTimeMins: int

class Map(PayloadData):
    map_filename: str
    player_slots: int
    sha1: str
    author: str
    description: str
    name: str
    suggested_players: str
    map_size: str
    mapAllowsSD: bool
    mapAllowsHD: bool

class MultiplayerGameListFilters(PayloadData):
    data: "Data10"

class Data10(PayloadData):
    filterText: str
    filterMinPlayers: int
    filterMaxPlayers: int
    filterRegion: str
    filterGameSpeed: int
    filterObservers: int
    filterMapSize: int
    filterMapType: int
    filterMapCreator: int
    filterLatency: int

class UpdateChatMemberStats(PayloadData):
    stats: "Stats"

class BaseMessage(PayloadData):
    sender: str
    content: str

class GameChatMessage(PayloadData):
    message: ChatMessage

class Stats(PayloadData):
    name: str
    gatewayId: int
    xp: int

class FriendsFriendData(PayloadData):
    data: "Data9"

class Data9(PayloadData):
    friendCount: int
    friends: list["Friend2"]

class Friend2(PayloadData):
    localRichPresenceAttributes: list["LocalRichPresenceAttribute"]
    accountId: int
    fullName: str
    battleTag: str
    isOnline: bool
    isFriend: bool
    isAway: bool
    isBusy: bool
    inProgram: bool
    inParty: bool
    currentProgram: str
    globalRichPresence: str
    gatewayId: int
    avatarId: str

class LocalRichPresenceAttribute(PayloadData):
    key: str
    value: str
    valueSize: int

class FriendsInvitationData(PayloadData):
    data: "Data8"

class Data8(PayloadData):
    invitationCount: int
    invitations: list[Data3]

class OnGameFocus(PayloadData):
    data: "Data7"

class Data7(PayloadData):
    focus: bool

class GameListRemove(PayloadData):
    game: "Game2"

class Game2(PayloadData):
    id: int

class GameList(PayloadData):
    games: list["Game"]

class Game(PayloadData):
    id: int
    name: str
    currentPlayers: int
    maxPlayers: int
    creationTime: int
    region: str
    ping: int
    mapFile: str
    mapProperties: "MapProperties"
    mapSettings: "MapSettings"

class MapSettings(PayloadData):
    flagLockTeams: bool
    flagPlaceTeamsTogether: bool
    flagFullSharedUnitControl: bool
    flagRandomRaces: bool
    flagRandomHero: bool
    settingObservers: str
    typeObservers: int
    settingVisibility: str
    typeVisibility: int

class MapProperties(PayloadData):
    mapSize: str
    mapSpeed: str
    mapName: str
    mapPath: str
    mapAuthor: str
    description: str
    suggested_players: str
    mapAllowsSD: bool
    mapAllowsHD: bool
    playerHost: str

class MultiplayerGameCreateStarted(PayloadData):
    empty: str = Field(..., alias="")

class GameLobbySetup(PayloadData):
    isHost: bool
    playerHost: str | None = Field(default=None)
    maxTeams: int
    isCustomForces: bool
    isCustomPlayers: bool
    mapData: "MapData"
    lobbyName: str
    mapFlags: MapSettings
    teamData: "TeamData"
    availableTeamColors: dict[str, list[int]] | None = Field(default=None)
    availableColors: list[int] | None = Field(default=None)
    players: list["Player"]

class FriendData(PayloadData):
    accountId: int
    fullName: str
    globalRichPresence: str
    isOnline: bool
    isFriend: bool
    isAway: bool
    isBusy: bool
    inProgram: bool
    inParty: bool
    currentProgram: str
    battleTag: str
    gatewayId: int

class Player(PayloadData):
    slotStatus: int | None = Field(default=None)
    slot: int | None = Field(default=None)
    team: int | None = Field(default=None)
    slotType: int | None = Field(default=None)
    isObserver: bool | None = Field(default=None)
    isSelf: bool | None = Field(default=None)
    slotTypeChangeEnabled: bool | None = Field(default=None)
    id: int | None = Field(default=None)
    name: str | None = Field(default=None)
    playerRegion: str | None = Field(default=None)
    gatewayId: int | None = Field(default=None)
    color: int | None = Field(default=None)
    colorChangeEnabled: bool | None = Field(default=None)
    teamChangeEnabled: bool | None = Field(default=None)
    race: int | None = Field(default=None)
    raceChangeEnabled: bool | None = Field(default=None)
    handicap: int | None = Field(default=None)
    handicapChangeEnabled: bool | None = Field(default=None)
    playerId: int | None = Field(default=None)
    teamColorId: int | None = Field(default=None)
    isReady: bool | None = Field(default=None)
    battletag: str | None = Field(default=None)
    clanName: str | None = Field(default=None)
    avatarId: str | None = Field(default=None)
    friendData: FriendData | None = Field(default=None)
    mmr: int | None = Field(default=None)
    xp: int | None = Field(default=None)
    gatewayId: int | None = Field(default=None)


class TeamData(PayloadData):
    teams: list["Team"]
    playableSlots: int
    filledPlayableSlots: int
    observerSlotsRemaining: int

class Team(PayloadData):
    team: int | None = Field(default=None)
    name: str | None = Field(default=None)
    filledSlots: int | None = Field(default=None)
    totalSlots: int | None = Field(default=None)
    team_id: int | None = Field(default=None)
    team_name: str | None = Field(default=None)
    players: list[Player] | None = Field(default=None)


class MapData(PayloadData):
    mapSize: str
    mapSpeed: str
    mapName: str
    mapPath: str
    mapAuthor: str
    description: str
    suggested_players: str
    mapAllowsSD: bool
    mapAllowsHD: bool

class MapList2(PayloadData):
    mapList: "MapList"

class MapList(PayloadData):
    maps: list["Map2"]
    currentDir: str
    lastUsedMap: str
    parentDirectory: str
    isBackDirectory: bool

class Map2(PayloadData):
    filename: str
    filepath: str
    isFolder: bool
    title: str
    maxPlayers: int | None = Field(default=None)
    author: str | None = Field(default=None)
    description: str | None = Field(default=None)
    name: str | None = Field(default=None)
    suggested_players: str | None = Field(default=None)
    map_size: str | None = Field(default=None)
    mapAllowsSD: bool | None = Field(default=None)
    mapAllowsHD: bool | None = Field(default=None)

class IMEUpdated(PayloadData):
    ime: "Ime"

class Ime(PayloadData):
    isEnabled: bool
    languageMode: str

class GameListUpdate(PayloadData):
    game: "Game3"

class Game3(PayloadData):
    id: int
    currentPlayers: int
    maxPlayers: int
    ping: int

class LobbyCountdown(PayloadData):
    details: "Details"

class Details(PayloadData):
    countdownActive: bool
    countdownLocked: bool

class MultiplayerGameLeave(PayloadData):
    empty: str = Field(..., alias="")

class ShowDownloadModal(PayloadData):
    fileName: str

class ProgressDownloadModal(PayloadData):
    downloadPercentage: int

class MultiplayerRecentPlayers(PayloadData):
    data: "RecentPlayers"

class RecentPlayers(PayloadData):
    recentPlayers: list["RecentPlayer"]

class RecentPlayer(PayloadData):
    localRichPresenceAttributes: list[LocalRichPresenceAttribute] | None = Field(default=None)
    accountId: int
    fullName: str
    battleTag: str
    gatewayId: int
    isFriend: bool
    isAway: bool
    isBusy: bool
    inProgram: bool
    inParty: bool
    globalRichPresence: str
    isOnline: bool
    currentProgram: str
    clanName: str
    avatarId: str
    encounterTime: float

class OptionsData(PayloadData):
    options: "Options"

class Options(PayloadData):
    general: "General"
    gameplay: "Gameplay"
    input: "Input"
    video: "Video"
    sound: "Sound"
    hotkeys: "Hotkeys"
    reforged: "General"
    isRefresh: bool

class Hotkeys(PayloadData):
    definitions: list["Definition"]

class Definition(PayloadData):
    id: str
    name: str
    race: str
    category: str
    hotkey: int
    defaultHotkey: int
    buttonPos: "ButtonPos"
    researchButtonPos: "ButtonPos"
    relatedStrIds: list[str]
    buildStrIds: list[str]
    modifier: int | None = Field(default=None)
    researchOnly: bool | None = Field(default=None)

class ButtonPos(PayloadData):
    x: int
    y: int

class Sound(PayloadData):
    preferences: list["Preference"]
    audioDeviceList: list["MonitorList"]
    audioDeviceIndex: int
    PREF_SOUND_MUSIC_OVERRIDE: str
    locales: list[str]

class Video(PayloadData):
    monitorList: list["MonitorList"]
    monitorSelected: int
    displayModes: list["DisplayMode"]
    displayMode: int
    preferences: list["Preference"]

class DisplayMode(PayloadData):
    bpp: int
    height: int
    refreshRate: int
    width: int
    id: int

class MonitorList(PayloadData):
    name: str
    id: int

class Input(PayloadData):
    preferences: list["Preference"]
    customKeys: str

class Gameplay(PayloadData):
    preferences: list["Preference"]
    zoomOptionsHd: list[int]
    zoomOptionsSd: list[int]
    currentSelectedZoom: int

class General(PayloadData):
    preferences: list["Preference"]

class Preference(PayloadData):
    preferenceName: str
    preferenceValue: int
    preferenceForced: bool
    preferenceState: str

class SetGameplaySDCampaignScreens(PayloadData):
    showSDCampaignScreens: int

class RankedSeasonStatsUpdate(PayloadData):
    seasonStats: "SeasonStats"

class SeasonStats(PayloadData):
    seasonId: int
    startTime: int
    endTime: int
    divisions: list[Division]
    placementMatches: list[Any] | None = Field(default=None)
    placementMatchesRequired: int | None = Field(default=None)
    wins: int | None = Field(default=None)
    losses: int | None = Field(default=None)
    highestRank: int | None = Field(default=None)
    xp: int | None = Field(default=None)
    isArrangedTeam: bool | None = Field(default=None)
    stats: "Stats2 | None" = Field(default=None)
    rank: int | None = Field(default=None)

class Stats2(PayloadData):
    mode_1v1: Clan = Field(..., alias="1v1")

class Maps(PayloadData):
    maps: list[Map]

class UpdateMapPool(PayloadData):
    mapPool: Maps

class ResumeUI(PayloadData):
    empty: str = Field(..., alias="")

class Success(PayloadData):
    success: bool

class MultiplayerGameCreateResult(PayloadData):
    details: Success

class SetOverlayScreen(PayloadData):
    screen: str

class SwitchToNextScreenInstantly(PayloadData):
    empty: str = Field(..., alias="")

class CancelTeamInvitations(PayloadData):
    empty: str = Field(..., alias="")

class ExitedGame(PayloadData):
    empty: str = Field(..., alias="")

class PlayerId(PayloadData):
    playerId: int

class LoadingPlayerReadyList(PayloadData):
    loadingPlayerReadyList: list[PlayerId]

class LoadingPlayerReadyUpdate(PayloadData):
    data: LoadingPlayerReadyList

class GameLobbyGracefulExit(PayloadData):
    screen: str

class MapInfo(PayloadData):
    name: str
    author: str
    description: str
    hasCustomBackground: bool
    isCampaignMapBackground: bool
    campaignBackgroundId: int
    customSubTitle: str
    customText: str

class TeamGame(PayloadData):
    team_id: int
    team_name: str
    players: list[Player]

class GameData(PayloadData):
    mapInfo: MapInfo
    isLoadGame: str
    gameType: str
    teams: list[Team]
    playerCount: int


class UpdateLoadingScreenInfo(PayloadData):
    gameData: GameData | None = Field(default=None)

class Details2(PayloadData):
    fillPercentage: float

class LoadProgressUpdate(PayloadData):
    details: Details2

class Data11(PayloadData):
    type: str
    canExit: bool

class ShowModal(PayloadData):
    data: Data11

class Error(PayloadData):
    name: str
    message: str

class AccountManagementError(PayloadData):
    error: Error

class LoggedOut(PayloadData):
    empty: str = Field(..., alias="")

class GameListClear(PayloadData):
    empty: str = Field(..., alias="")

class ClearDeferTournamentNotificationCheck(PayloadData):
    empty: str = Field(..., alias="")

import json
import keyword
import re

from textwrap import indent
from typing import Any, ClassVar, Type
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializeAsAny,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)

# ============================================================
# Type inference helpers
# ============================================================

ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ISO_DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


def unify_types(type_list: list[str]) -> str:
    """Unify multiple inferred types into a single annotation."""
    unique = set(type_list)
    if len(unique) == 1:
        return unique.pop()
    if "float" in unique and "int" in unique:
        return "float"
    return "Any"


def sanitize_field_name(key: str) -> tuple[str, str | None]:
    """
    Return (safe_name, alias).
    If safe_name differs from original, alias is the original key.
    """
    safe = key

    if key == "":
        return "empty", key

    # Replace illegal characters
    safe = safe.replace("-", "_").replace(" ", "_")

    # Prefix if starts with digit
    if safe[0].isdigit():
        safe = "mode_" + safe

    # Reserved keywords
    if keyword.iskeyword(safe):
        safe = safe + "_"

    alias = key if safe != key else None
    return safe, alias


def infer_type(value: Any, class_name_hint: str | None = None, depth: int = 0) -> tuple[str, list[str]]:
    """
    Infer Pydantic type for a JSON value.
    Returns: (annotation_str, nested_class_definitions)
    """
    nested_defs: list[str] = []

    if value is None:
        return "str | None", []

    if isinstance(value, bool):
        return "bool", []

    if isinstance(value, int):
        return "int", []

    if isinstance(value, float):
        return "int" if value.is_integer() else "float", []

    if isinstance(value, str):
        if ISO_DATETIME_RE.match(value):
            return "datetime", []
        if ISO_DATE_RE.match(value):
            return "date", []
        try:
            UUID(value)
            return "UUID", []
        except Exception:
            pass
        if value.isnumeric():
            return "str  # (looks numeric)", []
        return "str", []

    if isinstance(value, list):
        if not value:
            return "list[Any]", []
        inferred = [infer_type(v, class_name_hint, depth + 1)[0] for v in value[:5]]
        unified = unify_types(inferred)
        if isinstance(value[0], dict):
            nested_class_name = (class_name_hint or "NestedModel").capitalize()
            _, nested = infer_type(value[0], nested_class_name, depth + 1)
            nested_defs.extend(nested)
            return f"list[{nested_class_name}]", nested_defs
        return f"list[{unified}]", nested_defs

    if isinstance(value, dict):
        nested_class_name = (class_name_hint or "NestedModel").capitalize()
        fields = []
        for k, v in value.items():
            safe_name, alias = sanitize_field_name(k)
            field_type, nested = infer_type(v, k.capitalize(), depth + 1)
            nested_defs.extend(nested)
            if alias:
                fields.append(
                    f'    {safe_name}: {field_type} | None = Field(default=None, alias="{alias}")'
                )
            else:
                fields.append(f"    {safe_name}: {field_type} | None = Field(default=None)")
        nested_class = f"""
class {nested_class_name}(PayloadData):
{chr(10).join(fields)}
"""
        nested_defs.append(nested_class)
        return nested_class_name, nested_defs

    return "Any", []


# ============================================================
# Validation Advisor
# ============================================================

class ValidationAdvisor(BaseModel):
    original_data: dict[str, Any]
    model_name: str | None = None
    suggestions: list[str] = []
    class_stub: str | None = None

    @classmethod
    def from_exception(cls, e: ValidationError, data: dict[str, Any]) -> "ValidationAdvisor":
        message_type = data.get("messageType")
        payload = data.get("payload", {})

        suggestions: list[str] = []
        class_stub: str | None = None

        if message_type not in PayloadData._registry:
            # Generate a new class stub
            fields = []
            nested_defs: list[str] = []
            for k, v in payload.items():
                safe_name, alias = sanitize_field_name(k)
                field_type, nested = infer_type(v, k.capitalize())
                nested_defs.extend(nested)
                if alias:
                    fields.append(
                        f'    {safe_name}: {field_type} | None = Field(default=None, alias="{alias}")'
                    )
                else:
                    fields.append(f"    {safe_name}: {field_type} | None = Field(default=None)")

            main_class = f"""
class {message_type}(PayloadData):
{chr(10).join(fields)}
"""
            all_defs = "\n".join(nested_defs + [main_class])
            class_stub = all_defs
            suggestions.append(f"Suggested new class for `{message_type}` generated.")
        else:
            model_class = PayloadData._registry[message_type]
            model_fields = set(model_class.model_fields.keys())
            payload_fields = set(payload.keys())

            missing_fields = model_fields - payload_fields
            if missing_fields:
                suggestions.append(
                    f"Payload is missing required fields: {missing_fields}. "
                    f"Consider making them optional or ensure they are included."
                )

            extra_fields = payload_fields - model_fields
            if extra_fields:
                suggestions.append(
                    f"Payload contains unexpected fields: {extra_fields}. "
                    f"Consider adding them to `{message_type}` or removing them from input."
                )

            for error in e.errors():
                field = " -> ".join(str(loc) for loc in error["loc"])
                suggestions.append(
                    f"Field `{field}` failed: {error['msg']} (type={error['type']})"
                )

        return cls(
            original_data=data, model_name=message_type,
            suggestions=suggestions, class_stub=class_stub
        )

    def pretty_print(self) -> None:
        print(f"\nValidation failed for model: {self.model_name}")
        print("\nOriginal payload JSON:")
        print(indent(json.dumps(self.original_data, indent=4), "    "))
        for s in self.suggestions:
            print("\nSuggestion:", s)
        if self.class_stub:
            print("\nSuggested model stub:\n")
            print(indent(self.class_stub.strip(), "    "))


# ============================================================
# Example usage in a message handler
# ============================================================

# async def handle_message(msg: str) -> bool:
#     try:
#         data = json.loads(msg)
#         message_type = data["messageType"]
#         payload = data["payload"]
#         message = RecMessage(messageType=message_type, payload=payload)

#         # Example success/failure conditions
#         # if success_message_condition(message): return True
#         # elif failure_message_condition(message): return False
#         return True

#     except json.JSONDecodeError:
#         print(f"Received non-JSON message: {msg}")
#         return False

#     except ValidationError as e:
#         advisor = ValidationAdvisor.from_exception(e, data)
#         advisor.pretty_print()
#         return False
