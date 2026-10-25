# Capítulo 2 — A Cidade Gigantesca

Arquivo de conteúdo: `backend/caneca/game/content/20-cidade.yaml`. O capítulo começa na primeira entrada em `parapeito`, `calcada` ou `beco` (efeitos `on_enter`: conclui `q_despertar`, capítulo 2, inicia `q_cidade`).

## Locais

| id | Nome | Destaques |
|---|---|---|
| `parapeito` | Parapeito externo | Saída pela janela; salto até a calçada. |
| `calcada` | Calçada do Café Aurora | Zeca; acesso a beco, poça e cruzamento; porta do café (se aberta). |
| `beco` | Beco dos fundos | Ferrugem bloqueia a passagem para a calçada até ser resolvido (ou Noir estar junto). |
| `lixeira` | Montanha de lixo | Tampinha, palito, casca de pão; vista do bosque. |
| `poca_oceano` | Oceano da calçada (9 °C) | Travessia até o bueiro. |
| `bueiro` | Boca do bueiro | Túnel secreto até a floresta (`orla`). |
| `cruzamento` | Cruzamento | Semáforo; travessia perigosa até o jardim. |
| `jardim` | Jardim da praça | Fonte, casa amarela (Ilda na janela), cerca viva com buraco para a floresta. |

## Missões

- **`q_cidade` (principal)** — opcionais `orientar` (saber onde é a floresta) e `atravessar` (chegar à praça); obrigatório `encontrar_floresta` (cumprido ao entrar na `orla`).
- **`q_zeca`** — agradar Zeca (casca de pão → pena de amizade; ou algo brilhante). Ele passa a esperar no cruzamento.
- **`q_lata`** — passar pelo beco de Ferrugem: desfechos `respeito`, `pedagio`, `coragem`, `noir`.

## Quebra-cabeças e alternativas

**Saber onde fica a floresta** (`orientar` / flag `sabe_do_bosque`): mapa do bairro (porão), Zeca, Noir (rel ≥ 20), encontrar o buraco na cerca (criatividade CD 11) ou percepção de vibrações.

**Ferrugem:** pagar pedágio com tampinha/botão/moeda; encará-lo (coragem CD 13); dizer que ele não é lixo (exige a dica de Zeca ou coragem ≥ 55 — revela o túnel do bueiro); ou chegar com Noir.

**Poça gigante:** uma caneca cheia afunda. Atravessar exige barquinho (receita tampinha + palito), estar `buoyant` (café ≤ 40%, por exemplo derramando café) ou vazia. Teste de coragem CD 11 (+8 com barquinho); falha esfria e deixa o café aguado.

**Cruzamento:** atravessar correndo (coragem CD 14, dano se falhar); esperar o sinal fechar e atravessar com segurança; voar com Zeca (rel ≥ 30); montar em Noir (rel ≥ 50).

**Entradas da floresta:** buraco na cerca do jardim (precisa saber do bosque ou tê-lo encontrado) ou o túnel do bueiro (revelado por Ferrugem ou pela percepção de vibrações, inclusive no porão do café).

**Momento opcional:** examinar a casa amarela mostra Ilda na janela (fato `viu_ilda_janela`, conta para `segredo_ilda`).
