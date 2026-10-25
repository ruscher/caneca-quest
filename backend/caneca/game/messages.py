"""Engine-generated sentences (not authored content). Each entry is an ``LText`` template."""

from __future__ import annotations

from caneca.game.i18n import lt

M = {
    "not_here": lt(
        "Você procura por toda parte, mas não encontra isso por aqui.",
        "You look everywhere, but there is nothing like that here.",
    ),
    "unclear": lt(
        "Você hesita, sem saber bem como transformar essa ideia em movimento.",
        "You hesitate, unsure how to turn that idea into movement.",
    ),
    "which_exit": lt(
        "Para onde? Daqui você pode ir: {exits}.",
        "Where to? From here you can go: {exits}.",
    ),
    "no_exits": lt("Não há caminho visível daqui.", "There is no visible way out from here."),
    "exit_blocked": lt("Esse caminho está bloqueado por enquanto.", "That way is blocked for now."),
    "too_tired": lt(
        "Sua porcelana treme de cansaço. Você precisa descansar antes de algo tão exigente.",
        "Your porcelain trembles with fatigue. You need rest before something this demanding.",
    ),
    "travel": lt("Você segue para {place}.", "You make your way to {place}."),
    "travel_fail_default": lt(
        "Você tenta, mas escorrega no meio do caminho.",
        "You try, but slip halfway there.",
    ),
    "taken": lt("Você prende {item} com cuidado na sua alça.", "You carefully hook {item} on your handle."),
    "already_have": lt("{item} já está com você.", "{item} is already with you."),
    "not_portable": lt(
        "{item} é grande demais para uma caneca carregar.",
        "{item} is far too big for a mug to carry.",
    ),
    "too_heavy": lt(
        "Sua alça não aguenta mais peso. Talvez seja hora de largar algo.",
        "Your handle can't bear more weight. Maybe it's time to drop something.",
    ),
    "dropped": lt("Você deixa {item} no chão, com cuidado.", "You set {item} down gently."),
    "not_carrying": lt("Você não está carregando {item}.", "You are not carrying {item}."),
    "nothing_happens": lt(
        "Você tenta usar {thing}, mas nada de especial acontece.",
        "You try to use {thing}, but nothing special happens.",
    ),
    "use_nothing": lt(
        "Você olha ao redor procurando o que usar, mas nada responde.",
        "You look around for something to use, but nothing answers.",
    ),
    "cant_combine": lt(
        "Você tenta juntar {a} e {b}, mas eles simplesmente não combinam.",
        "You try to combine {a} and {b}, but they just don't fit together.",
    ),
    "combine_need_two": lt(
        "Para combinar, diga quais duas coisas você quer juntar.",
        "To combine, say which two things you want to join.",
    ),
    "talk_nobody": lt(
        "Você fala para o vazio. Só o eco da chuva responde.",
        "You speak into the empty room. Only the echo of the rain answers.",
    ),
    "talk_whom": lt(
        "Com quem? Por aqui estão: {npcs}.",
        "With whom? Around you are: {npcs}.",
    ),
    "talk_object": lt(
        "Você fala com {thing}, mas não ouve resposta — pelo menos, não ainda.",
        "You speak to {thing}, but hear no answer — at least, not yet.",
    ),
    "give_need_item": lt(
        "O que você quer entregar? Diga o item que está com você.",
        "What do you want to give? Name an item you're carrying.",
    ),
    "give_accept_like": lt(
        "{npc} recebe {item} com evidente alegria.",
        "{npc} accepts {item} with obvious delight.",
    ),
    "give_accept": lt(
        "{npc} aceita {item}, curioso com o gesto.",
        "{npc} takes {item}, curious about the gesture.",
    ),
    "give_reject": lt(
        "{npc} recua diante de {item}. Não parece ter sido uma boa ideia.",
        "{npc} recoils from {item}. That wasn't a good idea.",
    ),
    "give_remote": lt(
        "Há um vidro entre vocês. Não dá para entregar nada assim.",
        "There's glass between you. You can't hand anything over like this.",
    ),
    "befriend_ok": lt(
        "Você se aproxima com sinceridade. {npc} parece um pouco mais à vontade com você.",
        "You approach sincerely. {npc} seems a little more at ease with you.",
    ),
    "befriend_fail": lt(
        "Você tenta criar laços, mas {npc} ainda mantém distância.",
        "You try to make a connection, but {npc} keeps their distance.",
    ),
    "attack": lt(
        "Você investe com toda a força de uma caneca. O impacto ecoa em sua porcelana mais do que em qualquer outra coisa.",
        "You charge with all the might of a mug. The impact rings through your porcelain more than anything else.",
    ),
    "attack_npc": lt(
        "{npc} se assusta e se afasta, magoado com a sua investida.",
        "{npc} startles and backs away, hurt by your charge.",
    ),
    "jump_ok": lt(
        "Você toma impulso e salta! Por um instante, a porcelana voa — e aterrissa sem um arranhão.",
        "You gather momentum and leap! For a moment porcelain flies — and lands without a scratch.",
    ),
    "jump_fail": lt(
        "Você salta, mas aterrissa torta. Um estalo seco percorre sua porcelana.",
        "You leap, but land crooked. A dry crack runs through your porcelain.",
    ),
    "hide_ok": lt(
        "Você fica absolutamente imóvel. Para qualquer observador, é só uma caneca esquecida.",
        "You go perfectly still. To any observer, you're just a forgotten mug.",
    ),
    "hide_fail": lt(
        "Você tenta ficar imóvel, mas um fio de vapor denuncia que há algo vivo aqui.",
        "You try to stay still, but a wisp of steam betrays that something here is alive.",
    ),
    "rest": lt(
        "Você se aquieta e descansa. O tempo passa devagar, e a energia volta aos poucos.",
        "You settle down and rest. Time passes slowly as your energy returns.",
    ),
    "rest_cold": lt(
        "Enquanto descansa, você sente o café perder calor.",
        "As you rest, you feel your coffee losing its warmth.",
    ),
    "spill": lt(
        "Você se inclina e derrama um pouco de café. Um aroma quente se espalha ao redor.",
        "You tilt and spill some coffee. A warm aroma spreads around you.",
    ),
    "spill_empty": lt(
        "Você se inclina, mas não há mais café para derramar.",
        "You tilt, but there's no coffee left to spill.",
    ),
    "shout": lt(
        "Você grita com toda a força de uma caneca. O som ressoa pela sua borda como um sino.",
        "You shout with all the might of a mug. The sound rings around your rim like a bell.",
    ),
    "listen_default": lt(
        "Você fica em silêncio e escuta. Só ouve o próprio café borbulhando baixinho.",
        "You stay quiet and listen. You only hear your own coffee bubbling softly.",
    ),
    "wait": lt(
        "Você espera. O tempo escorre como gotas na janela.",
        "You wait. Time trickles like drops on the window.",
    ),
    "warm_ok": lt(
        "Você se aproxima do calor. O café volta a fumegar.",
        "You move close to the heat. Your coffee steams again.",
    ),
    "warm_overheat": lt(
        "Calor demais! A porcelana estala com o choque térmico.",
        "Too much heat! Your porcelain creaks from the thermal shock.",
    ),
    "warm_none": lt(
        "Não há fonte de calor aqui. Você se abraça com a própria alça, sem muito efeito.",
        "There's no heat source here. You hug yourself with your handle, to little effect.",
    ),
    "ride_no": lt(
        "Não há ninguém disposto a carregar uma caneca por aqui.",
        "There's no one here willing to carry a mug.",
    ),
    "improvise_ok": lt(
        "Você tenta algo inesperado — e, de algum jeito, dá certo. O mundo parece um pouco mais seu.",
        "You try something unexpected — and somehow it works. The world feels a bit more yours.",
    ),
    "improvise_partial": lt(
        "Você tenta algo inesperado. Não sai exatamente como imaginou, mas também não foi um desastre.",
        "You try something unexpected. It doesn't go quite as planned, but it's no disaster either.",
    ),
    "improvise_fail": lt(
        "Você tenta, mas o mundo das coisas grandes não colabora desta vez.",
        "You try, but the world of big things doesn't cooperate this time.",
    ),
    "self_examine": lt(
        "Você se observa: uma caneca {material} {color_name}, com estampa {style}. Dentro, {drink} a {temperature}°C. {condition}",
        "You look yourself over: a {color_name} {material} mug with a {style} pattern. Inside, {drink} at {temperature}°C. {condition}",
    ),
    "self_ok": lt("Sua porcelana está quase intacta.", "Your body is nearly intact."),
    "self_cracked": lt(
        "Uma rachadura fina corre pela lateral, e gotas de café escapam por ela.",
        "A thin crack runs down your side, and drops of coffee seep out.",
    ),
    "self_shattered": lt(
        "Você está por um fio — rachaduras cobrem quase todo o seu corpo.",
        "You're hanging by a thread — cracks cover almost all of you.",
    ),
    "inventory": lt("Você carrega: {items}.", "You're carrying: {items}."),
    "inventory_empty": lt("Sua alça está vazia.", "Your handle is empty."),
    "status": lt(
        "Temperatura {temperature}°C · café {coffee}% · integridade {integrity}% · energia {energy}%.",
        "Temperature {temperature}°C · coffee {coffee}% · integrity {integrity}% · energy {energy}%.",
    ),
    "help": lt(
        'Escreva o que quer fazer, com suas palavras: "examinar o jornal", "falar com o gato sobre a voz", "ir para a cozinha", "usar o fogão", "descansar". As sugestões são só ideias.',
        'Write what you want to do in your own words: "examine the newspaper", "talk to the cat about the voice", "go to the kitchen", "use the stove", "rest". Suggestions are only ideas.',
    ),
    "ability_unknown": lt(
        "Você ainda não sabe fazer isso.",
        "You don't know how to do that yet.",
    ),
    "ability_cooldown": lt(
        "Você ainda está se recuperando da última vez que usou {ability}.",
        "You're still recovering from the last time you used {ability}.",
    ),
    "ability_cost": lt(
        "Você não tem forças (ou café) suficientes para {ability} agora.",
        "You don't have enough strength (or coffee) for {ability} right now.",
    ),
    "ability_too_cold": lt(
        "Seu café está frio demais para {ability}.",
        "Your coffee is too cold for {ability}.",
    ),
    "ability_passive": lt(
        "{ability} já faz parte de você — funciona sozinha, sem esforço.",
        "{ability} is already part of you — it works on its own.",
    ),
    "level_up": lt(
        "Você se sente mais forte. Nível {level}!",
        "You feel stronger. Level {level}!",
    ),
    "learned": lt("Nova habilidade: {ability}.", "New ability: {ability}."),
    "quest_started": lt("Nova missão: {quest}.", "New quest: {quest}."),
    "objective_done": lt("Objetivo cumprido: {objective}.", "Objective complete: {objective}."),
    "quest_completed": lt("Missão concluída: {quest}.", "Quest complete: {quest}."),
    "quest_failed": lt("Missão perdida: {quest}.", "Quest failed: {quest}."),
    "achievement": lt("Conquista: {name}.", "Achievement: {name}."),
    "crack_leak": lt(
        "Uma gota de café escapa pela rachadura.",
        "A drop of coffee escapes through the crack.",
    ),
    "cooling_warn": lt(
        "Seu café está esfriando. Talvez seja bom procurar uma fonte de calor.",
        "Your coffee is cooling. It might be wise to find a heat source.",
    ),
    "defeat": lt(
        "Um último estalo, e tudo fica em silêncio. Sua jornada termina aqui — mas toda história pode ser recontada a partir de um ponto salvo.",
        "One last crack, and everything goes quiet. Your journey ends here — but every story can be retold from a saved point.",
    ),
    "story_protect": lt(
        "Você deveria ter se partido — mas algo quente dentro de você se recusa a desistir.",
        "You should have shattered — but something warm inside you refuses to give up.",
    ),
    "game_over": lt(
        "Esta história chegou ao fim. Você pode reler a jornada ou começar uma nova.",
        "This story has ended. You can reread the journey or begin a new one.",
    ),
    "injection": lt(
        "Por um instante, você ouve palavras estranhas ecoando em sua mente, como se alguém tentasse reescrever o mundo de fora dele. Mas o mundo continua exatamente como era.",
        "For a moment you hear strange words echoing in your mind, as if someone tried to rewrite the world from outside it. But the world remains exactly as it was.",
    ),
    "remote_note": lt("(através do vidro)", "(through the glass)"),
    "and": lt(" e ", " and "),
    "nothing": lt("nada", "nothing"),
}

STATUS_NAMES = {
    "hot": lt("quente", "hot"),
    "lukewarm": lt("morna", "lukewarm"),
    "cold": lt("fria", "cold"),
    "overheated": lt("superaquecida", "overheated"),
    "empty": lt("vazia", "empty"),
    "buoyant": lt("flutuante", "buoyant"),
    "tired": lt("exausta", "exhausted"),
    "cracked": lt("rachada", "cracked"),
    "shattered": lt("em pedaços", "shattered"),
    "hidden": lt("camuflada", "camouflaged"),
    "wet": lt("molhada", "wet"),
    "watered": lt("café aguado", "watered-down"),
}

MATERIAL_NAMES = {
    "porcelain": lt("de porcelana", "porcelain"),
    "stoneware": lt("de cerâmica grés", "stoneware"),
    "enamel": lt("esmaltada", "enamel"),
    "glass": lt("de vidro temperado", "tempered glass"),
}
STYLE_NAMES = {
    "classic": lt("clássica", "classic"),
    "striped": lt("listrada", "striped"),
    "dotted": lt("de bolinhas", "polka-dot"),
    "floral": lt("floral", "floral"),
    "minimal": lt("minimalista", "minimalist"),
    "rustic": lt("rústica", "rustic"),
}
DRINK_NAMES = {
    "black_coffee": lt("café preto", "black coffee"),
    "latte": lt("café com leite", "latte"),
    "cappuccino": lt("cappuccino", "cappuccino"),
    "hot_chocolate": lt("chocolate quente", "hot chocolate"),
    "tea": lt("chá", "tea"),
}
