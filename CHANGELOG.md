# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/); versões seguem [SemVer](https://semver.org/lang/pt-BR/).

## [0.1.0] — ainda não publicado

Primeira versão jogável.

### Adicionado
- Motor de regras determinístico (Python): interpretador de texto livre pt-BR/en, intenções validadas contra a cena, interações com condições e efeitos declarativos, testes d20 com semente, atributos da caneca (temperatura com resfriamento de Newton, café, porcelana, energia, coragem, criatividade, XP/nível), habilidades, companheiros, eventos aleatórios, conquistas, finais e derrota.
- Conteúdo em YAML validado na carga: Cafeteria, Cidade e Floresta (23 locais, 13 personagens, 11 missões, 3 finais), em português e inglês.
- Persistência em SQLite (WAL) com SQLAlchemy e Alembic: salvamento transacional a cada turno com controle otimista de versão, histórico, diário automático, memória de fatos por personagem, pontos salvos, restauração, exportação/importação versionada e validada, backups.
- Narração por IA opcional: Ollama, APIs compatíveis com OpenAI e Anthropic, com streaming (SSE), cancelamento, refinamento de intenção validado, memória com orçamento de contexto, resumos incrementais, saneamento da saída e fallback para o texto do motor. Modo básico sem IA completo.
- API REST + SSE com CSP, CORS restrito, token opcional, rate limit, limites de corpo e tratamento centralizado de erros.
- Interface web/PWA (React 19, TypeScript, Tailwind 4, Zustand): boas-vindas, criação da caneca com prévia ilustrada, jogo responsivo (desktop/tablet/celular), oito painéis, configurações de IA/visual/som/idioma, ajuda, créditos, temas claro/escuro/automático, i18n pt-BR/en, som ambiente procedural, leitura em voz alta, cartões de compartilhamento locais, acessibilidade WCAG 2.2 AA verificada com axe.
- App desktop com Tauri 2: backend empacotado como sidecar, porta aleatória em loopback, token por execução, nenhuma permissão de IPC, watchdog contra processos órfãos. Pacote `.deb` gerado e testado no Linux.
- Testes: 201 (backend), 94 (frontend), 11 cenários E2E com Playwright; medições de desempenho em `docs/testing/performance.md`.
- CI (lint, tipos, testes, build, E2E) e workflow de release multiplataforma no GitHub Actions.
- Documentação: AGENTS.md, especificações por agente, arquitetura, modelo de dados, motor, IA, memória, design system, fluxos, ameaças, plano de testes, narrativa e roadmap.

### Limitações conhecidas
- Instaladores de Windows e macOS configurados no `release.yml`, mas não executados.
- O adaptador do Ollama foi testado contra um servidor simulado do protocolo, não contra um Ollama real.
- Sem controle de custo em moeda para provedores em nuvem (apenas contagem de tokens).
