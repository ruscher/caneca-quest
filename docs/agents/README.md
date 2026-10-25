# Especificações de agentes

Cada arquivo define um papel de trabalho: responsabilidade, contexto, objetivos, limites, critérios de aceitação, dependências e validação. São especificações em texto: o Claude Code **não as carrega automaticamente**. Para usar, passe o arquivo como instrução a um subagente (por exemplo: "siga docs/agents/backend.md e implemente X") ou converta-o em um agente em `.claude/agents/` se desejar.

Regras comuns a todos: leia o `AGENTS.md`; não declare nada pronto sem executar a validação; não edite fora do seu escopo sem combinar; atualize a documentação afetada.

| Papel | Arquivo |
|---|---|
| Arquiteta(o) | architect.md |
| Frontend | frontend.md |
| Backend | backend.md |
| Game design | game-design.md |
| Narrative design | narrative-design.md |
| Engenharia de IA | ai-engineer.md |
| UX/UI | ux-ui.md |
| QA e testes | qa-testing.md |
| Segurança | security.md |
| DevOps | devops.md |
