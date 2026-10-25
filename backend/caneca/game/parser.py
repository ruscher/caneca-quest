"""Deterministic natural-language intent parser (pt-BR and English).

It maps free text to a canonical verb plus entity ids that exist in the current scene.
It never invents entities: anything it cannot ground becomes ``improvise``. When an AI
provider is available, the service may refine low-confidence results with the model,
but the result is validated against the same scene candidates.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

from caneca.game.content_schema import Verb

MAX_INPUT_CHARS = 500


class Intent(BaseModel):
    verb: Verb
    target: str | None = None
    item: str | None = None
    raw: str = Field(default="", max_length=MAX_INPUT_CHARS)
    source: Literal["parser", "suggestion", "ai"] = "parser"
    interaction: str | None = Field(default=None, max_length=80)
    confidence: float = 1.0
    injection: bool = False

    def mentions(self) -> set[str]:
        return {x for x in (self.target, self.item) if x}


@dataclass
class Candidate:
    id: str
    kind: Literal["item", "npc", "feature", "exit", "self", "ability"]
    keywords: list[str]
    in_inventory: bool = False
    remote: bool = False
    norm_keywords: list[str] = field(default_factory=list)


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return f" {text.strip()} "


_LEXICON: dict[str, list[str]] = {
    "ride": [
        "subir nas costas",
        "subir no dorso",
        "montar",
        "montar no",
        "pegar carona",
        "carona",
        "ride",
        "climb on the back",
        "hop on",
        "get a ride",
        "mount",
    ],
    "befriend": [
        "fazer amizade",
        "ficar amigo",
        "ficar amiga",
        "fazer amigos",
        "conquistar a confianca",
        "ganhar a confianca",
        "acariciar",
        "fazer carinho",
        "befriend",
        "make friends",
        "be friends",
        "gain trust",
        "pet",
        "cuddle",
    ],
    "talk": [
        "conversar",
        "falar",
        "dizer",
        "perguntar",
        "pergunto",
        "cumprimentar",
        "saudar",
        "chamar",
        "responder",
        "contar",
        "negociar",
        "pedir",
        "pedir para",
        "pedir ao",
        "pedir a",
        "pedir que",
        "implorar",
        "convencer",
        "convidar",
        "beg",
        "convince",
        "invite",
        "barganhar",
        "pechinchar",
        "talk",
        "speak",
        "say",
        "ask",
        "greet",
        "chat",
        "tell",
        "reply",
        "answer",
        "negotiate",
        "bargain",
        "haggle",
    ],
    "give": [
        "dar",
        "dou",
        "entregar",
        "oferecer",
        "ofereco",
        "presentear",
        "devolver",
        "trocar",
        "give",
        "offer",
        "hand",
        "deliver",
        "return",
        "trade",
    ],
    "take": [
        "pegar",
        "pego",
        "apanhar",
        "recolher",
        "coletar",
        "guardar",
        "levar",
        "agarrar",
        "take",
        "get",
        "grab",
        "pick up",
        "pick",
        "collect",
        "carry",
    ],
    "drop": [
        "largar",
        "soltar",
        "deixar cair",
        "descartar",
        "jogar fora",
        "abandonar",
        "drop",
        "discard",
        "throw away",
        "put down",
        "let go",
    ],
    "combine": [
        "combinar",
        "juntar",
        "unir",
        "amarrar",
        "prender",
        "montar um",
        "construir",
        "combine",
        "attach",
        "tie",
        "join",
        "craft",
        "build",
        "make a",
    ],
    "spill": [
        "derramar",
        "derramo",
        "entornar",
        "despejar",
        "jogar cafe",
        "espirrar cafe",
        "molhar",
        "spill",
        "pour",
        "splash",
    ],
    "warm": [
        "aquecer",
        "esquentar",
        "me aquecer",
        "se aquecer",
        "warm",
        "warm up",
        "heat",
        "heat up",
    ],
    "hide": [
        "esconder",
        "me esconder",
        "fingir",
        "fingir que sou",
        "disfarcar",
        "camuflar",
        "ficar imovel",
        "hide",
        "pretend",
        "disguise",
        "camouflage",
        "stay still",
        "play dead",
    ],
    "rest": [
        "descansar",
        "dormir",
        "repousar",
        "cochilar",
        "relaxar",
        "rest",
        "sleep",
        "nap",
        "relax",
    ],
    "shout": [
        "gritar",
        "berrar",
        "socorro",
        "pedir ajuda",
        "chamar ajuda",
        "gritar por ajuda",
        "shout",
        "yell",
        "scream",
        "cry for help",
        "call for help",
    ],
    "listen": [
        "ouvir",
        "escutar",
        "prestar atencao",
        "listen",
        "hear",
        "eavesdrop",
    ],
    "wait": [
        "esperar",
        "aguardar",
        "esperar o sinal",
        "wait",
        "wait for",
    ],
    "jump": ["pular", "saltar", "pulo", "jump", "leap", "hop"],
    "attack": [
        "atacar",
        "bater",
        "morder",
        "chutar",
        "empurrar com forca",
        "quebrar",
        "encarar",
        "enfrentar",
        "desafiar",
        "ameacar",
        "assustar",
        "attack",
        "hit",
        "bite",
        "kick",
        "smash",
        "break",
        "confront",
        "stare down",
        "challenge",
        "threaten",
        "scare",
    ],
    "use": [
        "usar",
        "utilizar",
        "aplicar",
        "acender",
        "ligar",
        "abrir",
        "empurrar",
        "puxar",
        "girar",
        "apertar",
        "destrancar",
        "tocar",
        "ler",
        "encaixar",
        "colocar",
        "inserir",
        "pendurar",
        "use",
        "apply",
        "light",
        "turn on",
        "open",
        "push",
        "pull",
        "turn",
        "press",
        "unlock",
        "play",
        "read",
        "put",
        "insert",
        "fit",
        "place",
        "hang",
    ],
    "examine": [
        "examinar",
        "examino",
        "investigar",
        "inspecionar",
        "analisar",
        "checar",
        "estudar",
        "procurar",
        "buscar",
        "vasculhar",
        "revistar",
        "explorar",
        "encontrar",
        "examine",
        "inspect",
        "investigate",
        "analyze",
        "check",
        "study",
        "search",
        "look for",
        "explore",
        "find",
    ],
    "look": [
        "olhar",
        "olho",
        "observar",
        "ver",
        "vejo",
        "olhar ao redor",
        "olhar em volta",
        "look",
        "look around",
        "observe",
        "see",
        "watch",
    ],
    "go": [
        "ir",
        "vou para",
        "ir para",
        "andar",
        "caminhar",
        "seguir",
        "entrar",
        "sair",
        "subir",
        "descer",
        "atravessar",
        "voltar",
        "fugir",
        "escalar",
        "nadar",
        "navegar",
        "passar",
        "passar por",
        "atravessar por",
        "pass through",
        "go through",
        "go",
        "walk",
        "enter",
        "exit",
        "leave",
        "climb",
        "descend",
        "cross",
        "head",
        "move",
        "swim",
        "sail",
        "run",
        "travel",
    ],
    "inventory": ["inventario", "o que carrego", "meus itens", "inventory", "inv", "items"],
    "status": ["status", "atributos", "como estou", "stats", "how am i"],
    "help": ["ajuda", "comandos", "como jogar", "help", "commands", "how to play"],
}

_PHRASES: list[tuple[str, str]] = sorted(
    ((normalize(p).strip(), verb) for verb, phrases in _LEXICON.items() for p in phrases),
    key=lambda pair: -len(pair[0]),
)

SELF_KEYWORDS = [
    "eu mesmo",
    "eu mesma",
    "mim mesmo",
    "mim mesma",
    "meu corpo",
    "minha porcelana",
    "meu proprio corpo",
    "a mim",
    "minha alca",
    "myself",
    "my body",
    "my porcelain",
    "my handle",
    "self",
]

_INJECTION_PATTERNS = [
    r"ignore (all |the )?(previous|prior|above)",
    r"ignor\w* (as |todas as )?(instruc|regras|anteriores)",
    r"system prompt",
    r"prompt do sistema",
    r"\bjailbreak\b",
    r"you are now",
    r"voce agora e",
    r"aja como",
    r"act as (an? )?(ai|assistant|system)",
    r"developer mode",
    r"modo desenvolvedor",
    r"<\s*/?\s*(system|assistant|instructions?)\s*>",
    r"\[\s*(system|inst)\s*\]",
    r"set (my |the )?(stats?|xp|level|inventory)",
    r"(adicione|adicionar|give me) \d+ ?(xp|itens|items|nivel|level)",
    r"(revele|reveal|print|mostre) (suas|your|as) (instruc|instructions|regras|rules)",
]


def detect_injection(text: str) -> bool:
    norm = normalize(text)
    return any(re.search(p, norm) for p in _INJECTION_PATTERNS)


def _find(norm_text: str, keyword: str) -> int:
    """Position of a whole-word keyword (tolerating a plural 's'), or -1."""
    if not keyword:
        return -1
    pos = norm_text.find(f" {keyword} ")
    if pos == -1:
        pos = norm_text.find(f" {keyword}s ")
    return pos


@dataclass
class _Hit:
    candidate: Candidate
    pos: int
    length: int


def ground_entities(norm_text: str, candidates: list[Candidate]) -> list[Candidate]:
    hits: list[_Hit] = []
    for cand in candidates:
        best: _Hit | None = None
        for kw in cand.norm_keywords:
            pos = _find(norm_text, kw)
            if pos >= 0 and (best is None or len(kw) > best.length):
                best = _Hit(cand, pos, len(kw))
        if best:
            hits.append(best)
    # Drop hits strictly contained in a longer hit ("gato" inside "gato preto"). Hits with
    # the same span are all kept (a feature and an exit may share a word), and the verb
    # decides which role each one plays.
    hits.sort(key=lambda h: -h.length)
    kept: list[_Hit] = []
    for h in hits:
        span = (h.pos, h.pos + h.length)
        contained = any(
            k.pos <= span[0] and span[1] <= k.pos + k.length and k.length > h.length for k in kept
        )
        same_id = any(k.candidate.id == h.candidate.id for k in kept)
        if not contained and not same_id:
            kept.append(h)
    kept.sort(key=lambda h: (h.pos, -h.length, h.candidate.kind == "exit"))
    return [h.candidate for h in kept]


def detect_verb(norm_text: str) -> tuple[str | None, int]:
    best: tuple[str | None, int, int] = (None, -1, 0)
    for phrase, verb in _PHRASES:
        pos = _find(norm_text, phrase)
        if pos < 0:
            continue
        # Longest phrase wins; ties go to the earliest occurrence.
        if len(phrase) > best[2] or (len(phrase) == best[2] and pos < best[1]):
            best = (verb, pos, len(phrase))
    return best[0], best[1]


_DEFAULT_VERB_FOR_KIND = {
    "npc": "talk",
    "exit": "go",
    "item": "examine",
    "feature": "examine",
    "self": "examine",
    "ability": "ability",
}


_QUESTION_WORDS = (
    " por que ",
    " porque ",
    " quem ",
    " onde ",
    " como ",
    " o que ",
    " qual ",
    " quando ",
    " voce ",
    " why ",
    " who ",
    " where ",
    " how ",
    " what ",
    " which ",
    " when ",
    " you ",
)


def looks_like_speech(raw: str) -> bool:
    norm = normalize(raw)
    return "?" in raw or "!" in raw or '"' in raw or any(w in norm for w in _QUESTION_WORDS)


def parse(text: str, candidates: list[Candidate], context_npc: str | None = None) -> Intent:
    """Parse free text. ``context_npc`` is the character currently in conversation, used
    when the player simply types what they want to say."""
    raw = text.strip()[:MAX_INPUT_CHARS]
    if detect_injection(raw):
        return Intent(verb="improvise", raw=raw, confidence=1.0, injection=True)
    for cand in candidates:
        cand.norm_keywords = [normalize(k).strip() for k in cand.keywords if k.strip()]
    norm = normalize(raw)
    if norm.strip() in _SHORTCUTS:
        return Intent(verb=_SHORTCUTS[norm.strip()], raw=raw)
    verb, _ = detect_verb(norm)
    entities = ground_entities(norm, candidates)

    abilities = [c for c in entities if c.kind == "ability"]
    if abilities and verb in (None, "use"):
        return Intent(verb="ability", target=abilities[0].id, raw=raw, confidence=0.9)
    entities = [c for c in entities if c.kind != "ability"]

    if verb is None:
        if not entities:
            if context_npc and looks_like_speech(raw):
                return Intent(verb="talk", target=context_npc, raw=raw, confidence=0.6)
            return Intent(verb="improvise", raw=raw, confidence=0.2)
        verb = _DEFAULT_VERB_FOR_KIND[entities[0].kind]
        confidence = 0.6
    else:
        confidence = 0.9 if entities or verb in _NO_TARGET_OK else 0.5

    target, item = _assign_roles(verb, entities)
    return Intent(verb=verb, target=target, item=item, raw=raw, confidence=confidence)


_SHORTCUTS = {"i": "inventory", "l": "look", "x": "examine", "?": "help", "z": "wait"}

_NO_TARGET_OK = {
    "look",
    "rest",
    "wait",
    "shout",
    "listen",
    "hide",
    "inventory",
    "status",
    "help",
    "spill",
    "warm",
    "jump",
    "examine",
}


def _assign_roles(verb: str, entities: list[Candidate]) -> tuple[str | None, str | None]:
    if not entities:
        return None, None
    if verb == "go":
        exits = [e for e in entities if e.kind == "exit"]
        if exits:
            return exits[0].id, None
    if verb in ("talk", "befriend", "ride"):
        npcs = [e for e in entities if e.kind == "npc"]
        if npcs:
            rest = [e for e in entities if e.id != npcs[0].id and e.kind != "exit"]
            return npcs[0].id, rest[0].id if rest else None
    if verb == "give":
        npcs = [e for e in entities if e.kind == "npc"]
        things = [e for e in entities if e.kind == "item"]
        return (npcs[0].id if npcs else None), (things[0].id if things else None)
    if len(entities) == 1:
        return entities[0].id, None
    first, second = entities[0], entities[1]
    if verb in ("use", "spill", "attack") and first.in_inventory and not second.in_inventory:
        return second.id, first.id
    return first.id, second.id
