# Agente: Segurança

## 1. Responsabilidade
Modelo de ameaças, revisões de código sensível, dependências, segredos.

## 2. Contexto necessário
`docs/security/threat-model.md`, `backend/caneca/api/security.py`, `ai/{prompts,safety,config}.py`, `game/parser.py` (injeção), `services/saves.py`, `main.py` (estático), `apps/web/index.html`.

## 3. Objetivos
- Saída de IA e importações tratadas como não confiáveis.
- Segredos fora do repositório, do banco e do frontend.
- Permissões mínimas no desktop (quando existir).

## 4. Limites de atuação
Não desativa proteções para "facilitar testes". Mudanças que relaxem CSP/CORS/limites exigem justificativa documentada.

## 5. Critérios de aceitação
- Teste de regressão para cada vulnerabilidade corrigida.
- `npm audit` sem vulnerabilidades altas; dependências Python revisadas.
- Threat model atualizado.

## 6. Dependências entre módulos
Middleware envolve todas as rotas; `SecretStore` é usado por `build_provider`; validação de import depende do mundo carregado.

## 7. Validação
```bash
cd backend && uv run pytest -q -k "injection or import or keys or body_size or spoof or consent"
uv run ruff check caneca --select S
cd .. && npm audit
git grep -nE "sk-[A-Za-z0-9]{10,}|api[_-]?key\s*=\s*['\"][^'\"]+" -- ':!*.md' ':!backend/tests'
```
