# Fluxos de uso

## 1. Primeira execução

1. Tela de boas-vindas: título, frase-tema, caneca animada, chuva de fundo.
2. Sem partidas: "Nova aventura" é o botão principal. Com partida ativa: "Continuar" mostra nome e local.
3. Linha de estado do narrador ("modo básico (sem IA)" ou provedor + modelo).
4. Backend inacessível: alerta com instrução e botão "Tentar novamente".

## 2. Criar a caneca (4 etapas)

1. **Identidade:** nome (obrigatório, até 40; "Sortear nome") e personalidade.
2. **Aparência:** cor (8 amostras), estampa, material.
3. **Alma:** bebida e até 2 traços.
4. **Aventura:** tom, dificuldade, tamanho da narração, idioma da história.

A prévia ao lado atualiza o retrato em tempo real. As etapas são navegáveis pelo indicador; tentar avançar sem nome foca o campo e mostra o erro. "Despertar" cria a partida e abre o jogo com o texto inicial em revelação progressiva.

## 3. Jogar um turno

1. A jogadora escreve (Enter envia, Shift+Enter quebra linha, ↑/↓ recuperam ações anteriores) ou toca numa sugestão (Alt+1…6), num caminho do painel de local, numa habilidade ou numa ação do inventário.
2. A ação aparece no feed; o compositor mostra "O mundo está reagindo…".
3. Evento `outcome`: medidores, painéis, mapa e sugestões atualizam na hora; toasts anunciam missões, objetivos, conquistas, níveis e habilidades.
4. Narração: modo básico mostra o texto do motor com revelação progressiva; com IA, o texto chega em streaming com cursor.
5. Rodapé do bloco: teste de dados (se ativado), consequências (temperatura, café, itens, deslocamento, relação, XP), selo de origem quando não é do motor, copiar trecho e salvar cartão PNG (gerado localmente, nada é enviado).
6. Leitores de tela recebem a narração completa uma vez (região `polite`), não token a token.

## 4. Streaming e cancelamento

- "Interromper" (ou Esc) aborta a geração. O bloco fica com o texto parcial ou o texto do motor e o selo "interrompida".
- Falha da IA: toast de aviso ("A IA não respondeu; usando a narrativa básica") e texto do motor; nada se perde.
- Conflito (partida alterada em outra janela): toast e recarga do estado e do histórico.

## 5. Salvar e restaurar

- Salvamento automático a cada turno (estado no banco).
- "Salvar ponto" (Ctrl+S, ícone no cabeçalho ou menu) cria um checkpoint nomeado com local e hora do jogo.
- Troca de capítulo cria checkpoint automático.
- Partidas salvas: lista com retrato, capítulo, local, nível e "atualizada há…"; abrir, renomear, exportar, excluir (com confirmação), checkpoints (restaurar com confirmação; o ponto atual é guardado como "Antes de restaurar"), cópia de segurança do banco.
- Fim de jogo (final ou derrota): cartão com "Voltar a um ponto salvo" e "Nova aventura"; o campo de ação é desativado.

## 6. Importar e exportar

- Exportar baixa `caneca-quest-<nome>.json` (formato v1).
- Importar aceita `.json` de até 8 MiB; o servidor valida tudo antes de criar uma nova partida. Erro → toast "Arquivo de partida inválido ou incompatível".

## 7. Configurações

- **Inteligência artificial:** escolher narrador; Ollama: URL, "Verificar e listar modelos", situação, seleção de modelo, Testar; nuvem: aviso, consentimento, chave (campo de senha; a chave nunca volta ao navegador); parâmetros (temperatura, contexto, tempo limite, turnos de memória, IA para ações ambíguas); uso registrado.
- **Visual e leitura:** tema, tamanho do texto, fonte de leitura, animações, velocidade do texto, mostrar testes, efeitos de clima.
- **Som e voz:** som ambiente procedural (desligado por padrão), volume, modo narrador (Web Speech) e voz.
- **Idioma:** muda interface e o idioma da história da partida aberta; o histórico do motor é re-renderizado no novo idioma.

## 8. Celular

- Narrativa ocupa a tela; faixa de medidores no topo (toque abre o estado completo).
- Sugestões numa linha rolável horizontalmente (só a linha rola, a página não).
- Barra inferior com Caneca, Inventário, Missões, Mapa, Diário; cada um abre um diálogo com as abas compactas.
- Campo com placeholder curto, `enterkeyhint="send"`, área de toque ≥ 44 px.
