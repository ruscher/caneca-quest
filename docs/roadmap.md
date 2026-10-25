# Roadmap

Estado honesto do projeto. "Feito" significa implementado e coberto por testes ou verificado no navegador.

## Feito

- Motor determinístico: parser pt-BR/en, interações, condições/efeitos, testes de dados com semente, atributos (temperatura, café, integridade, energia, coragem, criatividade, XP/nível), habilidades, companheiros, eventos aleatórios, conquistas, finais e derrota.
- Conteúdo: 3 regiões conectadas (Cafeteria, Cidade, Floresta), 23 locais, 13 personagens, missões principais e secundárias com resoluções alternativas, 3 finais. Validação de referências na carga.
- Persistência: SQLite + Alembic, commit transacional por turno, histórico, diário, fatos/memórias de NPC, checkpoints (manuais, automáticos por capítulo, antes de restaurar), exportação/importação v1 validada, backups.
- IA: Ollama, OpenAI-compatível e Anthropic com streaming, refinamento de intenção validado, memória com orçamento, resumos incrementais, saneamento de saída, fallback, cancelamento, consentimento para nuvem, registro de uso de tokens.
- API REST + SSE com segurança (CSP, CORS, token opcional, rate limit, limites de corpo).
- Web/PWA: boas-vindas, criação em 4 etapas com prévia, tela de jogo responsiva (desktop/tablet/celular), feed com texto progressivo e falas destacadas, 8 painéis (inventário, missões, mapa, diário, relações, memórias, enciclopédia, conquistas), partidas salvas, configurações (IA, visual, som/voz, idioma), ajuda, créditos, temas claro/escuro/automático, i18n pt-BR/en, som ambiente procedural, modo narrador (Web Speech), cartão de compartilhamento local.
- Testes: backend (pytest, ~200), frontend (Vitest, 94), E2E com Playwright + axe (11 cenários, desktop e celular), medições de desempenho reais.
- Desktop Linux: Tauri 2 com o backend como sidecar (PyInstaller), sem permissões de IPC, token por execução, watchdog contra processos órfãos; pacote `.deb` gerado e o app executado.
- CI/CD configurado (`ci.yml` e `release.yml` com matriz Linux/Windows/macOS).

## Próximo

1. Executar o `release.yml` no GitHub e validar os instaladores de Windows e macOS (não testados — sem acesso a essas plataformas aqui).
2. Teste com Ollama real em hardware modesto (CPU) e ajuste dos prompts por tamanho de modelo (o adaptador só foi testado contra um servidor simulado fiel ao protocolo).
3. Controle de custos em moeda e limite de gasto para provedores em nuvem.
4. Auditoria de dependências automatizada no CI.

## Depois

- Geração procedural de locais/eventos dentro de regras geográficas (o schema já permite novos locais sem mudar o motor).
- TTS local servido pelo backend (a interface `SpeechNarrator` já isola o mecanismo).
- Ilustrações por local e retratos de NPCs.
- Embeddings para memória, se medições mostrarem ganho (ver `docs/ai/memory.md`).
- Versão Android reaproveitando a PWA.
- Novos idiomas (adicionar dicionário de UI + traduções no conteúdo).
