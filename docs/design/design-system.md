# Design system

Fonte da verdade: `apps/web/src/styles/index.css` (tokens) e `apps/web/src/components/ui/` (componentes).

## Direção

- **Tema claro — livro ilustrado:** papel envelhecido, tinta marrom, café e cobre.
- **Tema escuro — café noturno cinematográfico:** azul noturno, luz de porcelana, cobre quente.
- **Tema automático:** segue `prefers-color-scheme`; o tema salvo é aplicado antes da primeira pintura por `public/theme-init.js` (arquivo externo por causa da CSP).

## Tokens de cor

Definidos como variáveis CSS (`--c-*`) em `:root` e `[data-theme="dark"]`, expostos ao Tailwind via `@theme inline` (`bg-bg`, `text-ink`, `border-rule`, `bg-accent` etc.).

| Token | Claro | Escuro | Uso |
|---|---|---|---|
| bg | `#f6efe3` | `#12161f` | fundo da página |
| bg-deep | `#ecdfca` | `#0c0f16` | fundos profundos |
| surface | `#fbf7f0` | `#1a2030` | cartões, campos |
| surface-2 | `#f1e7d7` | `#222a3d` | blocos secundários, trilhas de medidores |
| ink | `#2b1f17` | `#efe6d8` | texto principal |
| muted | `#65503f` | `#b9ab96` | texto secundário |
| rule | `#d9c6a8` | `#34405a` | bordas |
| accent / accent-ink | `#8a4b1c` / `#fff8ef` | `#e3a468` / `#1a1208` | ação primária, destaques |
| accent-soft | `#f0d9bf` | `#3a2c22` | selecionado |
| coffee, copper | `#6f4e37`, `#b8733a` | `#c9946a`, `#e0a066` | decoração, medidor de café |
| good, warn, bad | `#2f6b4c`, `#8a5a00`, `#a3352a` | `#7fc8a0`, `#f0c060`, `#f08a7a` | estados |
| cold, hot | `#2f5d8a`, `#b5432a` | `#8fb8e8`, `#f39a7f` | temperatura |
| dialogue | `#6a3a14` | `#f2c38f` | falas de personagens |
| player | `#3d5574` | `#a9c4e6` | ações da jogadora no feed |
| focus | `#2f5d8a` | `#9cc3ef` | anel de foco (3 px) |

### Contraste (WCAG 2.1, calculado a partir dos valores acima)

| Par | Claro | Escuro |
|---|---|---|
| ink / bg | 14,0 | 14,6 |
| muted / surface-2 (pior caso de texto secundário) | 6,2 | 6,4 |
| accent / bg | 5,9 | 8,4 |
| accent-ink / accent (botão primário) | 6,4 | 8,6 |
| dialogue / bg | 8,3 | 11,2 |
| player / surface-2 | 6,2 | 8,0 |
| hot / surface (pior caso de estado) | 5,2 | 7,5 |
| focus / bg | 6,0 | 9,9 |

Todos os pares de texto ficam acima de 4,5:1 (AA). Os números foram calculados com a fórmula de luminância relativa; o teste `apps/web/src/styles/contrast.test.ts` lê os tokens direto do CSS e falha se algum par cair abaixo de 4,5:1 (texto) ou 3:1 (anel de foco); o E2E (`apps/web/e2e/`) também roda o axe nos dois temas e no celular.

## Tipografia

| Papel | Família | Licença |
|---|---|---|
| Títulos (`font-display`) | Fraunces Variable | OFL |
| Leitura/narrativa (`font-read`) | Literata Variable (padrão) · Atkinson Hyperlegible · sem serifa do sistema | OFL |
| Interface (`font-ui`) | fonte do sistema; Atkinson quando escolhida como fonte de leitura | — |

Fontes empacotadas via Fontsource (sem CDN). A PWA pré-armazena só os subconjuntos latinos. Narrativa: 1,125 rem, entrelinha 1,75, coluna ≤ 44 rem, hifenização, capitular no texto de abertura. Tamanho global ajustável de 85% a 150% (`--font-scale`).

## Componentes (`components/ui`)

- `Button` (primary, secondary, ghost, danger; ≥ 44 px de altura, ícone opcional) e `IconButton` (rótulo acessível obrigatório).
- `Dialog`: `<dialog>` nativo com `showModal` (foco preso, Esc, fundo inerte), fecha clicando no fundo.
- `Tabs`/`TabPanel`: padrão WAI-ARIA com foco itinerante (setas, Home, End); modo compacto só com ícones.
- `Meter`: `role="meter"` com valor e texto (`aria-valuetext`); número e ícone visíveis, nunca só cor.
- `Toggle` (`role="switch"`), `Field` (rótulo, ajuda, erro com `role="alert"`), `ChoiceGroup` (rádios/checkboxes em cartões, amostras de cor), `Spinner` (`role="status"`), `Toasts` (região `polite` e região `assertive` para erros).
- `Icon`: conjunto próprio de ícones de traço 24×24, decorativos por padrão (`aria-hidden`).

Componentes de jogo (`components/game`): `MugAvatar` (SVG original: cor, estampa, bebida, vapor proporcional à temperatura, rachaduras pela integridade, expressão por cansaço/frio/camuflagem), `SceneBackdrop` (gradiente por região + canvas de chuva ou vaga-lumes), `NarrativeFeed`, `Composer`, `StatsPanel` (cartão da caneca, medidores, local, habilidades), `SidePanel` (8 abas).

## Movimento

- Entrada suave dos blocos (360 ms), vapor, tremor de frio, pulso do local atual no mapa, cursor de escrita.
- Texto progressivo configurável (instantâneo, 140, 70 ou 35 caracteres/s); clique, Esc ou "mostrar tudo" revelam o restante.
- Canvas de clima a ~30 fps, até 70 partículas, pausado com a aba oculta.
- `prefers-reduced-motion` ou a preferência "Reduzidas" zera animações e desliga o canvas; "Ativadas" força animações mesmo com a preferência do sistema.

## Layout responsivo

| Largura | Layout |
|---|---|
| ≥ 1024 px (`lg`) | 3 colunas: caneca/estado (17–19 rem) · narrativa · painéis (21–23 rem) |
| 768–1023 px (`md`) | narrativa · painéis; faixa compacta de medidores abre o estado completo |
| < 768 px | narrativa em tela cheia; faixa de medidores; sugestões numa linha rolável; barra inferior (Caneca, Inventário, Missões, Mapa, Diário) abre painéis em diálogo |

Colunas da grade usam `minmax(0, 1fr)` para que conteúdo largo não cause rolagem horizontal. O compositor respeita `env(safe-area-inset-bottom)` e o meta viewport usa `interactive-widget=resizes-content` para o teclado virtual não cobrir o campo.
