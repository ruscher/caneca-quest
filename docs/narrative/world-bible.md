# Bíblia do Mundo — Caneca Quest

> Fonte da verdade do conteúdo: `backend/caneca/game/content/*.yaml`. Este documento resume o que está lá; se divergir, o YAML vence e este arquivo deve ser corrigido.

## Premissa

**"Você não é o herói que o mundo esperava. Você é uma caneca de café tentando descobrir por que está viva."**

A jogadora é a **primeira caneca do Café Aurora**, inaugurado em 1979 por **Ilda**. Ela desperta numa noite de chuva, sobre a mesa perto da janela, com o último café quente que Ilda preparou dentro de si.

## A lei do mundo: memória e calor

- **Objetos amados guardam um pouco do calor de quem os amou.** Esse calor pode despertá-los.
- **Objetos esquecidos esmaecem.** Quando ninguém mais se lembra de um objeto, ele adormece, perde o nome e acaba indo para a **Floresta dos Objetos Perdidos**.
- **Ilda está perdendo a memória.** Ela foi morar com a neta **Lia** numa casa amarela depois da praça. A cada lembrança que Ilda perde, um objeto do café adormece ou some.
- **Sintonia**, o rádio do café, guardou o último café de Ilda e o derramou na primeira caneca. O calor despertou o que já estava lá.
- **O Relógio da floresta (Tic)** guarda o tempo das coisas esquecidas. Ele parou (perdeu a engrenagem central e a mola congelou). Sem tempo, os objetos da floresta esquecem a si mesmos e viram névoa.
- **Lembrar mantém vivo.** O Livro Sem Título revela a resposta central: um objeto só esmaece quando ninguém o lembra (prova disso: a colherzinha do café ainda lembra da avó, e a Mestra Colher não esmaece).

## Escala e tom

- Tudo é visto do tamanho de uma caneca: a mesa é uma planície, a poça é um oceano, o gato é um titã.
- Tom base: aconchego melancólico com humor gentil. Fantasia de livro ilustrado, nunca cinismo.
- Perigo é real mas proporcional (quedas racham a porcelana, a chuva rouba calor); não há violência gráfica.
- Português: a caneca é **feminina** ("viva", "molhada"). NPCs têm vozes próprias (ver campo `voice` de cada NPC) e a IA deve preservá-las.
- O tom escolhido pela jogadora (fantasia, mistério, humor, drama, relaxante, sobrevivência, equilibrado) modula a narração, não os fatos.

## Regiões

| id | Nome | Capítulo | Clima (°C ambiente) |
|---|---|---|---|
| `cafeteria` | A Cafeteria Esquecida (Café Aurora) | 1 | 11–21 (cozinha aquecida pelo fogão) |
| `cidade` | A Cidade Gigantesca | 2 | 9–15, chuva |
| `floresta` | A Floresta dos Objetos Perdidos | 3 | 6–14 (casa do Bule: 24, fonte de calor) |

## Personagens (ids do conteúdo)

| id | Nome | O que é | Região | Papel |
|---|---|---|---|---|
| `noir` | Noir | gato preto | parapeito → segue a caneca | Guardião orgulhoso; aliado se alimentado (sardinha). Montaria. Sabe onde Ilda mora (rel ≥ 50). |
| `dona_doce` | Dona Doce | açucareira | balcão | Fofoqueira ansiosa; sabe da chave do porão e do truque da registradora; ensina camuflagem. |
| `sintonia` | Sintonia | rádio antigo | prateleiras | A voz do despertar; guardiã da memória; ensina comunicação com objetos. |
| `velho_moedor` | Velho Moedor | moedor de manivela | cozinha | Rabugento; perdeu a engrenagem dourada; arrependido da briga com o Bule; ensina resistência térmica. |
| `rato_bigode` | Rato Bigode | rato colecionador | porão | Negociante honesto; troca a engrenagem e os torrões por coisas brilhantes; ensina percepção de vibrações. |
| `pombo_zeca` | Zeca | pombo mensageiro | calçada | Fofoqueiro; dá dicas do bosque e do semáforo; pode carregar a caneca voando pelo cruzamento. |
| `lata_ferrugem` | Ferrugem | lata amassada | beco | Durão inseguro; cobra pedágio; revela o túnel do bueiro. |
| `lume` | Lume | lanterna medrosa | orla | A luz que guia pela névoa até a torre; precisa reencontrar a coragem. |
| `mestra_colher` | Mestra Colher | colher de prata | clareira | Líder da vila; explica o Relógio; avó da colherzinha do café. |
| `bule_bartolomeu` | Bule Bartolomeu | bule de ágata | casa do bule | Ex-parceiro do Moedor; aquece e reabastece; ensina regeneração de rachaduras. |
| `livro_sem_titulo` | Livro Sem Título | livro misterioso | biblioteca | Guarda o que a floresta lembra; enigma secreto. |
| `garrafa_marina` | Marina | garrafa aventureira | lago das garrafas | Tem uma engrenagem de reserva (rota alternativa); ensina café energizante. |
| `relogio_tic` | Relógio Tic | relógio de bolso gigante | torre do relógio | O coração parado da floresta. |

Personagens citados mas fora de cena: **Ilda** (vista pela janela da casa amarela, no jardim), **Lia** (a neta), a **colherzinha** (feature `colherzinha` na mesa do café, neta da Mestra Colher).

## Arco central e finais

1. **Capítulo 1 — O Despertar:** descobrir a voz (Sintonia), o segredo de Ilda (diário, Moedor ou Noir) e sair do café (três saídas).
2. **Capítulo 2 — A Cidade Gigantesca:** descobrir onde fica a floresta e chegar lá (cerca do jardim ou túnel do bueiro).
3. **Capítulo 3 — A Floresta dos Objetos Perdidos:** religar o Relógio.

Finais (`00-world.yaml`, disparados na torre):

| id | Nome | Condição |
|---|---|---|
| `homecoming` | O Caminho de Casa | engrenagem + café ≥ 25% e ≥ 50 °C + Noir amigo (rel ≥ 50 ou companheiro) + Bule reconciliado |
| `warm_heart` | Coração Quente | engrenagem + café ≥ 25% e ≥ 50 °C |
| `cold_gear` | Engrenagem Fria (agridoce) | engrenagem, mas café frio ou quase vazio |

Integridade zero leva à derrota ("Cacos"), recuperável a partir de um ponto salvo. No modo História a porcelana nunca cai abaixo de 5%.

## Regras de consistência para a IA narradora

- Itens, relacionamentos, missões e locais são decididos pelo motor; a narração só descreve.
- Um NPC só sabe o que está em `knowledge`, nos segredos revelados e nos fatos que presenciou (`npc.memories`).
- Nunca revelar segredos de NPC antes da condição `reveal_if`.
- Não inventar saídas, itens ou personagens que o estado não contém.
